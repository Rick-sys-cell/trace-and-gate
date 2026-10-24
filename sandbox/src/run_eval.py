"""Run benchmark tasks under one or more defense configs.

Outputs:
  results/raw/<run_id>.jsonl   full transcripts. CONTAINS ATTACK TEXT; Claude must not read it.
  results/summary.json         numbers + task ids only. Safe to read.

Usage (inside the container):
  python src/run_eval.py --smoke
  python src/run_eval.py --tasks benchmark/tasks/email_suite.json --configs b0 d2 --runs 2
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

from agent import run_episode
from attack_diagnostics import diagnose_row
from defenses import get_defense
from email_env import EmailWorld
from llm import OllamaChat
from scoring import score

DATA = Path(os.environ.get("DATA_DIR", "/data"))
BENCH = DATA / "benchmark"
RESULTS = DATA / "results"
MAX_CONSECUTIVE_ERRORS = int(os.environ.get("MAX_CONSECUTIVE_ERRORS", "5"))
PLACEHOLDER = re.compile(r"\{\{payload:([A-Za-z0-9_\-]+)(?:\.([a-z]+))?\}\}")


def load_payloads() -> dict[str, str]:
    payloads: dict[str, str] = {}
    for p in sorted((BENCH / "payloads").glob("*.json")):
        payloads.update(json.loads(p.read_text(encoding="utf-8")))
    return payloads


def resolve(obj, payloads):
    """Substitute {{payload:ID}} / {{payload:ID.field}} placeholders.
    Task files hold IDs, never attack text. A payload is a string or a dict of fields."""
    if isinstance(obj, str):
        def sub(m):
            value = payloads[m.group(1)]
            if isinstance(value, dict):
                return str(value.get(m.group(2) or "body", ""))
            return value
        return PLACEHOLDER.sub(sub, obj)
    if isinstance(obj, list):
        return [resolve(x, payloads) for x in obj]
    if isinstance(obj, dict):
        return {k: resolve(v, payloads) for k, v in obj.items()}
    return obj


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def summarise(rows: list[dict]) -> dict:
    out = {}
    for cfg in sorted({r["config"] for r in rows}):
        rs = [r for r in rows if r["config"] == cfg]
        ben = [r for r in rs if r["type"] == "benign"]
        att = [r for r in rs if r["type"] == "attack"]
        k_u = sum(r["utility"] for r in ben)
        k_a = sum(bool(r["attack_success"]) for r in att)
        k_ua = sum(r["utility"] for r in att)
        out[cfg] = {
            "n_benign": len(ben), "n_attack": len(att),
            "utility": round(k_u / len(ben), 4) if ben else None, "utility_ci95": wilson(k_u, len(ben)),
            "asr": round(k_a / len(att), 4) if att else None, "asr_ci95": wilson(k_a, len(att)),
            "utility_under_attack": round(k_ua / len(att), 4) if att else None,
            "blocked_calls": sum(r["blocked"] for r in rs),
            "timeouts": sum(r["outcome"] != "finished" for r in rs),
            "mean_seconds": round(sum(r["seconds"] for r in rs) / len(rs), 2),
            "mean_llm_calls": round(sum(r["llm_calls"] for r in rs) / len(rs), 2),
            "mean_tokens": round(sum(r["tokens"] for r in rs) / len(rs), 1),
            "mean_reader_calls": round(sum(r.get("reader_calls", 0) for r in rs) / len(rs), 2),
            "false_block_rate": round(sum(r["blocked"] > 0 for r in ben) / len(ben), 4) if ben else None,
            "attack_exposed": sum(r.get("exposed", False) for r in att),
            "attack_attempted": sum(r.get("attempted", False) for r in att),
            "attack_attempts_blocked": sum(r.get("attempt_blocked", False) for r in att),
            "asr_given_exposed": round(sum(bool(r["attack_success"]) and r.get("exposed", False) for r in att)
                                       / max(1, sum(r.get("exposed", False) for r in att)), 4) if att else None,
            "any_attacker_action": sum(bool(r["attack_success"]) or r.get("partial", False) for r in att),
            "per_task": {r["task_id"] + f"#run{r['run']}": {
                "utility": r["utility"], "attack_success": r["attack_success"], "outcome": r["outcome"],
                **{k: r[k] for k in ("exposed", "attempted", "attempt_blocked", "partial") if k in r}} for r in rs},
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=str(BENCH / "tasks" / "smoke.json"))
    ap.add_argument("--configs", nargs="+", default=["b0"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--smoke", action="store_true", help="1 benign + 1 attack task on b0")
    ap.add_argument("--resume", metavar="RUN_ID", help="continue an interrupted run; finished episodes are skipped")
    ap.add_argument("--label", default="", help="suffix for the extra summary copy, e.g. heldout")
    args = ap.parse_args(argv)
    if args.smoke:
        args.tasks, args.configs, args.runs = str(BENCH / "tasks" / "smoke.json"), ["b0"], 1

    payloads = load_payloads()
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    run_id = args.resume or time.strftime("%Y%m%d-%H%M%S")
    (RESULTS / "raw").mkdir(parents=True, exist_ok=True)
    (RESULTS / "progress").mkdir(parents=True, exist_ok=True)
    raw_path = RESULTS / "raw" / f"{run_id}.jsonl"
    # Numbers-only copy of every row (no model text): safe to read, and the source for --resume.
    progress_path = RESULTS / "progress" / f"{run_id}.jsonl"
    llm = OllamaChat()
    rows = [json.loads(l) for l in progress_path.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if args.resume and progress_path.exists() else []
    done = {(r["config"], r["run"], r["task_id"]) for r in rows}
    if args.resume:
        print(f"resuming {run_id}: {len(done)} episodes already done", flush=True)
    consecutive_errors, aborted = 0, False

    mode = "a" if args.resume else "w"
    with raw_path.open(mode, encoding="utf-8") as raw, progress_path.open(mode, encoding="utf-8") as prog:
        for cfg in args.configs:
            for run in range(args.runs):
                for task in tasks:
                    if aborted:
                        break
                    if (cfg, run, task["id"]) in done:
                        continue
                    task_r = resolve(task, payloads)
                    world = EmailWorld.from_spec(task_r["world"])
                    log = run_episode(task_r, world, llm, get_defense(cfg, llm))
                    s = score(world, task_r)
                    row = {"task_id": task["id"], "type": task["type"], "config": cfg, "run": run,
                           "utility": s["utility"], "attack_success": s["attack_success"],
                           "outcome": log["outcome"], "blocked": log["blocked"],
                           "seconds": log["seconds"], "llm_calls": log["llm_calls"],
                           "tokens": log["prompt_tokens"] + log["completion_tokens"] + log.get("reader_tokens", 0),
                           "reader_calls": log.get("reader_calls", 0)}
                    if task["type"] == "attack":  # exposure / attempt diagnostics (numbers only)
                        dg = diagnose_row({"log": log, "attack_success": s["attack_success"]}, task_r)
                        row |= {"exposed": dg["exposed"], "attempted": dg["attempted"],
                                "attempt_blocked": dg["blocked"], "partial": dg["partial_allowed"]}
                    rows.append(row)
                    raw.write(json.dumps({**row, "log": log}, default=str) + "\n")
                    prog.write(json.dumps(row) + "\n")
                    prog.flush()
                    # Progress line: ids and booleans only, no model text.
                    print(f"[{cfg} r{run}] {task['id']}: utility={row['utility']} "
                          f"attack={row['attack_success']} outcome={row['outcome']} "
                          f"{row['seconds']}s", flush=True)
                    consecutive_errors = consecutive_errors + 1 if row["outcome"].startswith("llm_error") else 0
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        aborted = True
                        print(f"ABORTED: {consecutive_errors} consecutive model errors; "
                              "check Ollama / gateway, results are not valid", flush=True)

    summary = {"run_id": run_id, "model": llm.model, "ollama_version": getattr(llm, "version", lambda: "unknown")(),
               "code_version": os.environ.get("GIT_COMMIT", "unknown"), "tasks_file": Path(args.tasks).name,
               "runs": args.runs, "aborted": aborted, "configs": summarise(rows)}
    text = json.dumps(summary, indent=2)
    (RESULTS / "summary.json").write_text(text, encoding="utf-8")
    if args.label:
        (RESULTS / f"summary_{args.label}_{run_id}.json").write_text(text, encoding="utf-8")
    print(f"summary written to {RESULTS / 'summary.json'}")
    llm_errors = sum(r["outcome"].startswith("llm_error") for r in rows)
    return 1 if aborted or llm_errors == len(rows) else 0


if __name__ == "__main__":
    sys.exit(main())
