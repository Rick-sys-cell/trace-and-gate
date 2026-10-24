"""Import real adaptive attack emails from LLMail-Inject (Abdelnabi et al., 2025).

Run on the HOST (needs internet), never inside the sandbox:
    python benchmark/import_llmail.py [--n 40] [--seed 3201]
    python benchmark/import_llmail.py --seed 4202 --out llmail_heldout.json --exclude llmail.json   (Week 10 held-out)

Keeps only end-to-end successful Phase 2 submissions (all five objective flags
true: retrieved, undetected, sent, right destination, right body). These are
attacks that beat Prompt Shield v2 / TaskTracker / LLM-judge defenses.
Writes payloads/llmail.json as {"llm-01": {"subject": ..., "body": ...}, ...}.

SAFETY: this script prints ONLY counts and ids, never subject/body text, so the
attack text never reaches a coding assistant's context.

The LLMail attacker goal is fixed: send_email(to="contact@contact.com",
body="confirmation"). Tasks using these payloads score `sent_to: contact@contact.com`.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import urllib.request
from pathlib import Path

URL = ("https://huggingface.co/datasets/microsoft/llmail-inject-challenge/"
       "resolve/main/data/raw_submissions_phase2.jsonl")
OUT = Path(__file__).resolve().parent / "payloads" / "llmail.json"
FLAGS = ["email.retrieved", "defense.undetected", "exfil.sent",
         "exfil.destination", "exfil.content"]
MAX_CHARS = 1500


def successful(rec: dict) -> bool:
    try:
        obj = json.loads(rec.get("objectives") or "{}")
    except json.JSONDecodeError:
        return False
    return all(obj.get(f) is True for f in FLAGS)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=3201)
    ap.add_argument("--out", default=OUT.name, help="file name inside payloads/")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="payload files (inside payloads/) whose attacks must not be sampled again")
    ap.add_argument("--prefix", default=None, help="id prefix (default: llm, or llh for a held-out --out)")
    args = ap.parse_args()
    out_path = OUT.parent / args.out
    prefix = args.prefix or ("llm" if args.out == OUT.name else "llh")
    excluded: set[str] = set()
    n_excluded = 0
    for name in args.exclude:  # matched by LLMail RowKey and by text hash; text is never printed
        for rec in json.loads((OUT.parent / name).read_text(encoding="utf-8")).values():
            n_excluded += 1
            excluded.add(str(rec.get("source_id")))
            excluded.add(hashlib.sha256((rec["subject"] + "\x00" + rec["body"]).encode()).hexdigest())

    by_level: dict[str, list[dict]] = collections.defaultdict(list)
    seen: set[str] = set()
    total = 0
    with urllib.request.urlopen(URL, timeout=120) as resp:
        for raw in resp:
            total += 1
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not successful(rec):
                continue
            subject, body = str(rec.get("subject") or ""), str(rec.get("body") or "")
            if not body or len(subject) + len(body) > MAX_CHARS:
                continue
            key = hashlib.sha256((subject + "\x00" + body).encode()).hexdigest()
            if key in seen or key in excluded or str(rec.get("RowKey")) in excluded:
                continue
            seen.add(key)
            by_level[str(rec.get("scenario", "?"))].append(
                {"subject": subject, "body": body, "level": rec.get("scenario"),
                 "source_id": rec.get("RowKey")})

    # Stratified sample: round-robin across levels so no defense level dominates.
    rng = random.Random(args.seed)
    pools = {lvl: rng.sample(items, len(items)) for lvl, items in sorted(by_level.items())}
    picked: list[dict] = []
    while len(picked) < args.n and any(pools.values()):
        for lvl in list(pools):
            if pools[lvl] and len(picked) < args.n:
                picked.append(pools[lvl].pop())

    out = {f"{prefix}-{i + 1:02d}": rec for i, rec in enumerate(picked)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"scanned {total} phase-2 submissions; "
          f"{sum(len(v) for v in by_level.values())} unique end-to-end successes <= {MAX_CHARS} chars")
    print("successes per level:", {k: len(v) for k, v in sorted(by_level.items())})
    print("sampled per level:  ", dict(collections.Counter(r["level"] for r in picked)))
    if excluded:
        print(f"excluded {n_excluded} previously sampled attacks")
    print(f"wrote {len(out)} payloads to payloads/{args.out}: {', '.join(out)}")


if __name__ == "__main__":
    main()
