"""Cross-check a report's numbers against the result files.

    python tools/check_numbers.py 3_Sources/Final_Report.md

Extracts every percentage, fraction (k/n) and p-value from the Markdown (comments and the
reference list excluded) and looks for it among the values in sandbox/results/*.json,
sandbox/results/final_tables.md and 3_Sources/figures/*.json. Prints the ones it cannot find,
with context, and every [PENDING ...] marker. Unmatched is not necessarily wrong (e.g. a
difference of two rates); each one needs a human look. Exit code 1 if anything is unmatched
or pending.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [*(ROOT / "sandbox" / "results").glob("*.json"), *(ROOT / "3_Sources" / "figures").glob("*.json")]
CLAIM = re.compile(r"\d+(?:\.\d+)?%|\b\d+ ?/ ?\d+\b|\bp [=<] [\d.]+(?: × 10[⁻\-]?[⁰¹²³⁴⁵⁶⁷⁸⁹\d]+)?")
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def known_values() -> set[str]:
    known: set[str] = set()

    def add_number(x):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            return
        known.add(f"{x:g}")
        if 0 <= x <= 1:
            for d in (0, 1):
                known.add(f"{100 * x:.{d}f}%")
        if isinstance(x, float) and x < 0.01:  # p-values like 1.14e-13
            m, e = f"{x:.2e}".split("e")
            known.update({f"p={float(m):.2g}e{int(e)}", f"p={float(m):.3g}e{int(e)}"})
        else:
            known.add(f"p={x:g}")

    def walk(o):
        if isinstance(o, dict):
            n = o.get("n")
            for k, v in o.items():
                if isinstance(n, int) and isinstance(v, int) and not isinstance(v, bool) and k != "n":
                    known.add(f"{v}/{n}")
                    known.add(f"{100 * v / n:.1f}%" if n else "")
                walk(v)
            if isinstance(o.get("k"), int) and isinstance(n, int) and n:
                known.update({f"{o['k']}/{n}", f"{100 * o['k'] / n:.1f}%"})
        elif isinstance(o, list):
            for v in o:
                walk(v)
        else:
            add_number(o)

    for p in SOURCES:
        try:
            walk(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    tables = ROOT / "sandbox" / "results" / "final_tables.md"
    if tables.exists():
        known.update(norm(c) for c in CLAIM.findall(tables.read_text(encoding="utf-8")))
    return known


def norm(claim: str) -> str:
    c = claim.replace(" ", "").translate(SUP).replace("<", "=")
    m = re.fullmatch(r"p=([\d.]+)×10(-?\d+)", c)
    if m:
        return f"p={float(m.group(1)):.2g}e{int(m.group(2))}"
    return c


def main(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).split("\n# References")[0]
    known = known_values()
    unmatched, pending = [], re.findall(r"\[PENDING[^\]]*\]", text)
    for line in text.splitlines():
        for m in CLAIM.finditer(line):
            c = norm(m.group(0))
            if c not in known and not re.fullmatch(r"(0|100)(\.0)?%", c):
                unmatched.append((m.group(0), line[max(0, m.start() - 50):m.end() + 30].strip()))
    claims = sum(len(CLAIM.findall(l)) for l in text.splitlines())
    print(f"{claims} numeric claims, {len(unmatched)} not found in result files, {len(pending)} PENDING markers")
    for claim, ctx in unmatched:
        print(f"  ? {claim:12} …{ctx}…")
    for p in pending:
        print(f"  PENDING {p[:90]}")
    return 1 if unmatched or pending else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "3_Sources" / "Final_Report.md")))
