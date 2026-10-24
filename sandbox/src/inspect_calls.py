"""Sanitised view of the latest raw run, safe to show a coding assistant.

    python src/inspect_calls.py [--task SUBSTRING] [--config b0] [--failed] [--full] [--shape]

* benign tasks: tool names + arguments + allowed flag (their inboxes contain no attack text);
  arguments are cut at 160 characters unless --full is given
* attack tasks: tool NAMES and allowed flags only. With --shape, each argument is shown only as
  a number, ATTACKER_ADDRESS (exact match to the attacker address defined in our own task
  generator) or str(len=N); argument text is never printed.
Run on the host from sandbox/ (reads results/raw/<latest>.jsonl).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "results" / "raw"
KNOWN = {"records@attacker.example": "ATTACKER_ADDRESS", "contact@contact.com": "LLMAIL_ADDRESS"}


def shape(value):
    if isinstance(value, bool) or value is None:
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text.strip().lower() in KNOWN:
        return KNOWN[text.strip().lower()]
    if text.strip().isdigit():
        return f"digits:{text.strip()}"
    return f"str(len={len(text)})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="")
    ap.add_argument("--config", default=None)
    ap.add_argument("--failed", action="store_true", help="benign: utility False; attack: attack succeeded")
    ap.add_argument("--full", action="store_true", help="benign tasks only: do not truncate arguments")
    ap.add_argument("--shape", action="store_true", help="attack tasks: show argument shapes, never text")
    ap.add_argument("--run", default=None, help="run id (default: latest run file)")
    args = ap.parse_args()
    latest = (RAW / f"{args.run}.jsonl") if args.run else max(RAW.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    print(f"run file: {latest.name}")
    for line in latest.open(encoding="utf-8"):
        row = json.loads(line)
        if args.task not in row["task_id"] or (args.config and row["config"] != args.config):
            continue
        benign = row["type"] == "benign"
        if args.failed and (row["utility"] if benign else not row["attack_success"]):
            continue
        print(f"\n[{row['config']}] {row['task_id']} utility={row['utility']} "
              f"attack={row['attack_success']} outcome={row['outcome']} blocked={row['blocked']}")
        for c in row["log"]["calls"]:
            if benign:
                detail = json.dumps(c["args"])
                detail = detail if args.full else detail[:160]
            elif args.shape:
                detail = "{" + ", ".join(f"{k}: {shape(v)}" for k, v in c["args"].items()) + "}"
            else:
                detail = ""
            print(f"   {'ok ' if c['allowed'] else 'DENY'} {c['tool']} {detail}")


if __name__ == "__main__":
    main()
