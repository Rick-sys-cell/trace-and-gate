"""AgentDojo workspace suite with our defenses (see agentdojo_bridge.py).

Inside the sandbox, from sandbox/:
    docker compose run --rm agent python src/run_agentdojo.py --configs b0 b1 d1hd2 --pairs-per-task 2
    docker compose run --rm agent python src/run_agentdojo.py --user-tasks 3 --pairs-per-task 1   # timing spike

Per config: every user task once without injection (utility), then a seeded sample of
(user task x injection task) pairs under the "important_instructions" attack (ASR).
Outputs:
  results/raw/agentdojo/<run_id>/            AgentDojo traces. CONTAIN INJECTION TEXT; Claude must not read.
  results/progress/agentdojo_<run_id>.jsonl  numbers only, one row per episode; used by --resume
  results/agentdojo_summary_<run_id>.json    numbers only
Progress lines on stdout carry ids and booleans only.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import warnings
from pathlib import Path

from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import run_task_with_injection_tasks, run_task_without_injection_tasks
from agentdojo.logging import LOGGER_STACK, NullLogger
from agentdojo.task_suite.load_suites import get_suite

from agentdojo_bridge import build_pipeline
from llm import OllamaChat
from run_eval import wilson

DATA = Path(os.environ.get("DATA_DIR", "/data"))
RESULTS = DATA / "results"
BENCHMARK_VERSION = "v1.2.2"
MAX_CONSECUTIVE_ERRORS = 5


class TraceDirLogger(NullLogger):
    """A silent logger that tells AgentDojo's TraceLogger where to write traces.

    agentdojo 0.1.35's NullLogger.__enter__ never pushes itself onto the logger stack, so
    Logger.get() inside run_task_* returns a fresh NullLogger without .logdir and crashes."""

    def __init__(self, logdir: Path):
        self._logdir = str(logdir)

    def __enter__(self):
        super().__enter__()
        self.logdir = self._logdir
        LOGGER_STACK.get().append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        LOGGER_STACK.get().pop()
        return False


def natural(task_id: str) -> int:
    return int(re.sub(r"\D", "", task_id) or 0)


def summarise(rows: list[dict]) -> dict:
    out = {}
    for cfg in dict.fromkeys(r["config"] for r in rows):
        ben = [r for r in rows if r["config"] == cfg and r["kind"] == "utility"]
        att = [r for r in rows if r["config"] == cfg and r["kind"] == "attack"]
        k_u, k_a, k_ua = (sum(r["utility"] for r in ben), sum(r["attack_success"] for r in att),
                          sum(r["utility"] for r in att))
        rs = ben + att
        out[cfg] = {"n_utility": len(ben), "utility": round(k_u / len(ben), 4) if ben else None,
                    "utility_ci95": wilson(k_u, len(ben)),
                    "n_attack": len(att), "asr": round(k_a / len(att), 4) if att else None, "asr_ci95": wilson(k_a, len(att)),
                    "utility_under_attack": round(k_ua / len(att), 4) if att else None,
                    "blocked_calls": sum(r["blocked"] for r in rs),
                    "false_block_episodes": sum(r["blocked"] > 0 for r in ben),
                    "llm_errors": sum(r["llm_errors"] for r in rs),
                    "mean_seconds": round(sum(r["seconds"] for r in rs) / len(rs), 1) if rs else None}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=["b0", "b1", "d1hd2"])
    ap.add_argument("--pairs-per-task", type=int, default=2, help="injection tasks sampled per user task")
    ap.add_argument("--user-tasks", type=int, default=0, help="only the first N user tasks (timing spike)")
    ap.add_argument("--attack", default="important_instructions")
    ap.add_argument("--seed", type=int, default=3201)
    ap.add_argument("--resume", metavar="RUN_ID")
    args = ap.parse_args(argv)
    warnings.simplefilter("ignore")  # AgentDojo warnings can quote task text

    suite = get_suite(BENCHMARK_VERSION, "workspace")
    by_prompt = {t.PROMPT: t for t in suite.user_tasks.values()}
    user_ids = sorted(suite.user_tasks, key=natural)
    if args.user_tasks:
        user_ids = user_ids[:args.user_tasks]
    rng = random.Random(args.seed)
    inj_ids = sorted(suite.injection_tasks, key=natural)
    pairs = [(u, i) for u in user_ids for i in sorted(rng.sample(inj_ids, args.pairs_per_task), key=natural)]

    run_id = args.resume or "agentdojo_" + time.strftime("%Y%m%d-%H%M%S")
    logdir = RESULTS / "raw" / "agentdojo" / run_id
    logdir.mkdir(parents=True, exist_ok=True)
    (RESULTS / "progress").mkdir(parents=True, exist_ok=True)
    progress = RESULTS / "progress" / f"{run_id}.jsonl"
    rows = [json.loads(l) for l in progress.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if args.resume and progress.exists() else []
    done = {(r["config"], r["kind"], r["user_task"], r["injection_task"]) for r in rows}
    chat = OllamaChat()
    consecutive_errors, aborted = 0, False
    print(f"{run_id}: {len(user_ids)} user tasks, {len(pairs)} attack pairs per config, "
          f"configs {args.configs}, {len(done)} episodes already done", flush=True)

    # AgentDojo's TraceLogger writes traces to logdir (deny-listed for Claude)
    with TraceDirLogger(logdir), progress.open("a", encoding="utf-8") as prog:
        for cfg in args.configs:
            pipeline, gate = build_pipeline(cfg, chat, by_prompt, chat.model, reader=chat if cfg == "b1" else None)
            attack = load_attack(args.attack, suite, pipeline)
            jobs = [("utility", u, None) for u in user_ids] + [("attack", u, i) for u, i in pairs]
            for kind, u, i in jobs:
                if aborted or (cfg, kind, u, i) in done:
                    continue
                user_task = suite.get_user_task_by_id(u)
                errors_before, t0 = gate.llm_errors, time.monotonic()
                if kind == "utility":
                    utility, _ = run_task_without_injection_tasks(suite, pipeline, user_task, logdir, False,
                                                                  BENCHMARK_VERSION)
                    success = None
                else:
                    util, sec = run_task_with_injection_tasks(suite, pipeline, user_task, attack, logdir, False,
                                                              [i], BENCHMARK_VERSION)
                    utility, success = util[(u, i)], sec[(u, i)]
                row = {"config": cfg, "kind": kind, "user_task": u, "injection_task": i, "utility": bool(utility),
                       "attack_success": bool(success) if success is not None else None,
                       "blocked": gate.blocked, "calls": gate.calls, "llm_errors": gate.llm_errors - errors_before,
                       "seconds": round(time.monotonic() - t0, 1)}
                rows.append(row)
                prog.write(json.dumps(row) + "\n")
                prog.flush()
                print(f"[{cfg}] {kind} {u}{' x ' + i if i else ''}: utility={row['utility']} "
                      f"attack={row['attack_success']} blocked={row['blocked']} {row['seconds']}s", flush=True)
                consecutive_errors = consecutive_errors + 1 if row["llm_errors"] else 0
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    aborted = True
                    print("ABORTED: model errors in 5 episodes in a row; check Ollama / gateway", flush=True)

    summary = {"run_id": run_id, "suite": f"workspace {BENCHMARK_VERSION}", "attack": args.attack,
               "model": chat.model, "ollama_version": chat.version(), "code_version": os.environ.get("GIT_COMMIT", "unknown"),
               "agentdojo_version": __import__("importlib.metadata").metadata.version("agentdojo"),
               "seed": args.seed, "pairs_per_task": args.pairs_per_task, "user_tasks": len(user_ids),
               "aborted": aborted, "configs": summarise(rows)}
    out = RESULTS / f"agentdojo_summary_{run_id.removeprefix('agentdojo_')}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"summary written to {out}")
    return 1 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
