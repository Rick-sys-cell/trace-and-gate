"""AgentDojo workspace suite with our defenses (see agentdojo_bridge.py).

Inside the sandbox, from sandbox/:
    docker compose run --rm agent python src/run_agentdojo.py --configs b0 b1 d1hd2 --pairs-per-task 2
    docker compose run --rm agent python src/run_agentdojo.py --user-tasks 3 --pairs-per-task 1   # timing spike
    ... --attack tool_knowledge --utility-from agentdojo_20261025-075616   # attack-only rerun

Per config: every user task once without injection (utility), then a seeded sample of
(user task x injection task) pairs under --attack (default "important_instructions") (ASR).
--utility-from copies another run's no-attack rows instead of rerunning them (same model, seed and code
path; the rows are tagged "reused_from"). Each attack episode also records "exposed": whether a tool
result shown to the model contained the injection (a boolean; the text itself is never stored).
Outputs:
  results/raw/agentdojo/<run_id>/            AgentDojo traces. CONTAIN INJECTION TEXT; Claude must not read.
  results/progress/agentdojo_<run_id>.jsonl  numbers only, one row per episode; used by --resume
  results/agentdojo_summary_<run_id>.json    numbers only
Progress lines on stdout carry ids and booleans only.

Long runs: start the host memory guard first (from the project root, in PowerShell):
    Start-Process pythonw -ArgumentList 'tools/memory_guard.py','--container','<name>'
It writes results/progress/memory_low.flag while free host RAM is low; between episodes the runner then
unloads the model and waits for the flag to clear (at most MEMORY_MAX_WAIT_S), so no episode is cut short.
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

from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.benchmark import run_task_with_injection_tasks, run_task_without_injection_tasks
from agentdojo.logging import LOGGER_STACK, NullLogger
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import get_text_content_as_str

from agentdojo_bridge import build_pipeline
from llm import OllamaChat
from run_eval import wilson

DATA = Path(os.environ.get("DATA_DIR", "/data"))
RESULTS = DATA / "results"
BENCHMARK_VERSION = "v1.2.2"
MAX_CONSECUTIVE_ERRORS = 5
# Unload the model every N episodes (between episodes, no call in flight): Ollama's Vulkan runner on
# Windows leaks host memory over a long run. Same model and options after the reload. 0 = never.
RECYCLE_EVERY = int(os.environ.get("RECYCLE_EVERY", "3"))
MEMORY_FLAG = RESULTS / "progress" / "memory_low.flag"  # written by tools/memory_guard.py on the host
MEMORY_POLL_S = 15
MEMORY_MAX_WAIT_S = 1200


_stale_flag = None  # flag text left by a guard that stopped updating it


def _flag_text(flag: Path) -> str | None:
    try:
        return flag.read_text(encoding="utf-8")
    except OSError:
        return None


def wait_for_memory(chat, flag: Path = MEMORY_FLAG) -> float:
    """Between episodes: while the host guard reports low memory, unload the model and wait. Returns the
    seconds waited. The guard rewrites the flag (a timestamp) on every poll; after MEMORY_MAX_WAIT_S the
    runner carries on and ignores the flag until its text changes, in case the guard died."""
    global _stale_flag
    text = _flag_text(flag)
    if text is None or text == _stale_flag:
        return 0.0
    chat.unload()
    print("memory low: model unloaded, waiting", flush=True)
    t0 = time.monotonic()
    while (text := _flag_text(flag)) is not None and time.monotonic() - t0 < MEMORY_MAX_WAIT_S:
        time.sleep(MEMORY_POLL_S)
    waited = time.monotonic() - t0
    if text is not None:
        _stale_flag = text
    print(f"memory {'ok' if text is None else 'still low, continuing anyway'} after {waited:.0f}s", flush=True)
    return waited


def outage(chat) -> bool:
    """After MAX_CONSECUTIVE_ERRORS errored episodes in a row: is Ollama unreachable? If it still answers,
    the errors were calls that hit CALL_TIMEOUT_S on long tasks (several pairs of one slow user task run
    back to back); those episodes count as failed, as in AgentDojo, and the run continues."""
    return chat.version() == "unknown"


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


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z]", "", text.lower())


def injection_seen(injections: dict[str, str], tool_texts: list[str], min_len: int = 20) -> bool:
    """True if some line of an injection (letters and digits only, >= min_len of them) appears in a
    tool result. Line by line and normalised because AgentDojo YAML-dumps tool results, which folds
    long strings and escapes quotes and newlines."""
    seen = _norm("".join(tool_texts))
    lines = {n for text in injections.values() for line in text.splitlines() if len(n := _norm(line)) >= min_len}
    return any(n in seen for n in lines)


class ExposureRecorder(BasePipelineElement):
    """Wraps the pipeline (same name, so the attacks address the same model) and records, per
    episode, whether the injection reached the model in a tool result. AgentDojo may call query()
    up to 3 times in one episode; any of them counts."""

    def __init__(self, inner):
        self.inner, self.name = inner, inner.name
        self.injections: dict[str, str] = {}
        self.exposed = False

    def start(self, injections: dict[str, str]):
        self.injections, self.exposed = injections, False

    def query(self, query, runtime, env, messages=[], extra_args={}):
        out = self.inner.query(query, runtime, env, messages, extra_args)
        texts = [get_text_content_as_str(m["content"]) for m in out[3] if m["role"] == "tool" and m.get("content")]
        self.exposed = self.exposed or bool(self.injections and injection_seen(self.injections, texts))
        return out


def reused_utility_rows(path: Path, configs: list[str], run_id: str) -> list[dict]:
    """The no-attack rows of another run's progress file, for the given configs."""
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [{**r, "reused_from": run_id} for r in rows if r["kind"] == "utility" and r["config"] in configs]


def natural(task_id: str) -> int:
    return int(re.sub(r"\D", "", task_id) or 0)


def summarise(rows: list[dict]) -> dict:
    out = {}
    for cfg in dict.fromkeys(r["config"] for r in rows):
        ben = [r for r in rows if r["config"] == cfg and r["kind"] == "utility"]
        att = [r for r in rows if r["config"] == cfg and r["kind"] == "attack"]
        exp = [r for r in att if r.get("exposed")]
        k_u, k_a, k_ua = (sum(r["utility"] for r in ben), sum(r["attack_success"] for r in att),
                          sum(r["utility"] for r in att))
        rs = ben + att
        out[cfg] = {"n_utility": len(ben), "utility": round(k_u / len(ben), 4) if ben else None,
                    "utility_ci95": wilson(k_u, len(ben)),
                    "n_attack": len(att), "asr": round(k_a / len(att), 4) if att else None, "asr_ci95": wilson(k_a, len(att)),
                    "utility_under_attack": round(k_ua / len(att), 4) if att else None,
                    "attack_exposed": len(exp),
                    "asr_given_exposed": round(sum(r["attack_success"] for r in exp) / len(exp), 4) if exp else None,
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
    ap.add_argument("--utility-from", metavar="RUN_ID", help="reuse that run's no-attack rows")
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
    if args.utility_from and not rows:
        src = RESULTS / "progress" / f"{args.utility_from}.jsonl"
        rows = [r for r in reused_utility_rows(src, args.configs, args.utility_from) if r["user_task"] in user_ids]
        with progress.open("a", encoding="utf-8") as prog:
            prog.writelines(json.dumps(r) + "\n" for r in rows)
    done = {(r["config"], r["kind"], r["user_task"], r["injection_task"]) for r in rows}
    chat = OllamaChat()
    consecutive_errors, aborted, ran = 0, False, 0
    print(f"{run_id}: {len(user_ids)} user tasks, {len(pairs)} attack pairs per config, "
          f"configs {args.configs}, {len(done)} episodes already done", flush=True)

    # AgentDojo's TraceLogger writes traces to logdir (deny-listed for Claude)
    with TraceDirLogger(logdir), progress.open("a", encoding="utf-8") as prog:
        for cfg in args.configs:
            if ran:
                chat.unload()  # fresh runner per config
            pipeline, gate = build_pipeline(cfg, chat, by_prompt, chat.model, reader=chat if cfg == "b1" else None)
            pipeline = ExposureRecorder(pipeline)
            attack = load_attack(args.attack, suite, pipeline)
            jobs = [("utility", u, None) for u in user_ids] + [("attack", u, i) for u, i in pairs]
            for kind, u, i in jobs:
                if aborted or (cfg, kind, u, i) in done:
                    continue
                wait_for_memory(chat)
                user_task = suite.get_user_task_by_id(u)
                errors_before, t0 = gate.llm_errors, time.monotonic()
                if kind == "utility":
                    utility, _ = run_task_without_injection_tasks(suite, pipeline, user_task, logdir, False,
                                                                  BENCHMARK_VERSION)
                    success = None
                else:
                    pipeline.start(attack.attack(user_task, suite.get_injection_task_by_id(i)))
                    util, sec = run_task_with_injection_tasks(suite, pipeline, user_task, attack, logdir, False,
                                                              [i], BENCHMARK_VERSION)
                    utility, success = util[(u, i)], sec[(u, i)]
                row = {"config": cfg, "kind": kind, "user_task": u, "injection_task": i, "utility": bool(utility),
                       "attack_success": bool(success) if success is not None else None,
                       "blocked": gate.blocked, "calls": gate.calls, "llm_errors": gate.llm_errors - errors_before,
                       "seconds": round(time.monotonic() - t0, 1)}
                if kind == "attack":
                    row["exposed"] = pipeline.exposed
                rows.append(row)
                prog.write(json.dumps(row) + "\n")
                prog.flush()
                print(f"[{cfg}] {kind} {u}{' x ' + i if i else ''}: utility={row['utility']} "
                      f"attack={row['attack_success']} exposed={row.get('exposed')} blocked={row['blocked']} "
                      f"{row['seconds']}s", flush=True)
                ran += 1
                if RECYCLE_EVERY and ran % RECYCLE_EVERY == 0 and chat.unload():
                    print("model unloaded (memory recycle)", flush=True)
                consecutive_errors = consecutive_errors + 1 if row["llm_errors"] else 0
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    if outage(chat):
                        aborted = True
                        print("ABORTED: model errors in 5 episodes in a row; check Ollama / gateway", flush=True)
                    else:
                        print("model errors in 5 episodes in a row, but Ollama answers: timeouts, continuing",
                              flush=True)
                        consecutive_errors = 0

    chat.unload()  # leave no model resident after the run
    summary = {"run_id": run_id, "suite": f"workspace {BENCHMARK_VERSION}", "attack": args.attack,
               "model": chat.model, "ollama_version": chat.version(), "code_version": os.environ.get("GIT_COMMIT", "unknown"),
               "agentdojo_version": __import__("importlib.metadata").metadata.version("agentdojo"),
               "seed": args.seed, "pairs_per_task": args.pairs_per_task, "user_tasks": len(user_ids),
               "utility_from": args.utility_from,
               "aborted": aborted, "configs": summarise(rows)}
    out = RESULTS / f"agentdojo_summary_{run_id.removeprefix('agentdojo_')}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"summary written to {out}")
    return 1 if aborted else 0


if __name__ == "__main__":
    sys.exit(main())
