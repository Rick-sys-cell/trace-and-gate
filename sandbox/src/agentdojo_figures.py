"""Figure for the full AgentDojo run: attack success vs utility per config, as analyse.py's Fig 1.

    python src/agentdojo_figures.py            (host, from sandbox/)

Reads only results/agentdojo_summary_*.json (numbers) and writes
results/figures/fig1_asr_vs_utility{,_col,_slide}_agentdojo.png.
"""
from __future__ import annotations

import json
import sys

import analyse

CONFIGS = ["b0", "b1", "d1hd2"]


def full_summary():
    """The newest summary of a full run (40 user tasks, not the timing spike), or None."""
    for f in sorted(analyse.RESULTS.glob("agentdojo_summary_*.json"), reverse=True):
        s = json.loads(f.read_text(encoding="utf-8"))
        if s.get("user_tasks", 0) >= 40:
            return s
    return None


def as_analysis(summary: dict) -> dict:
    """Map AgentDojo summary fields onto the analysis.json shape that analyse.figures() reads."""
    return {"configs": {c: {"asr": {"rate": v["asr"], "ci95": v["asr_ci95"]},
                            "utility": {"rate": v["utility"], "ci95": v["utility_ci95"]}}
                        for c, v in summary["configs"].items()}}


def main() -> int:
    s = full_summary()
    if s is None or s.get("aborted"):
        print("no finished full AgentDojo run yet; no figure written")
        return 1
    configs = [c for c in CONFIGS if c in s["configs"]]
    analyse.figures(as_analysis(s), configs, "_agentdojo", heatmap=False)
    print(f"wrote AgentDojo figures for {configs} (run {s['run_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
