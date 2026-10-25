"""Analysis + figure for the full AgentDojo run.

    python src/agentdojo_analyse.py            (host, from sandbox/)

Reads only numbers: results/agentdojo_summary_*.json and its progress file
results/progress/<run_id>.jsonl (one row per episode: ids, booleans, counts). Writes
results/analysis_agentdojo.json (timeouts per kind, utility without timed-out episodes,
paired McNemar tests on the same user task / pair) and
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


def analyse_rows(rows: list[dict], configs: list[str]) -> dict:
    by = {(r["config"], r["kind"], r["user_task"], r["injection_task"]): r for r in rows}
    out = {"configs": {}, "mcnemar": {}, "attack_successes": {}}
    for c in configs:
        out["configs"][c] = {}
        for kind in ("utility", "attack"):
            rs = [r for r in rows if r["config"] == c and r["kind"] == kind]
            ok = [r for r in rs if not r["llm_errors"]]
            k_ok = sum(r["utility"] for r in ok)
            out["configs"][c][kind] = {
                "n": len(rs), "utility": analyse.rate(rs, "utility"),
                "timed_out_episodes": len(rs) - len(ok),
                "utility_without_timeouts": {"k": k_ok, "n": len(ok), "rate": round(k_ok / len(ok), 4) if ok else None},
                "episodes_with_block": sum(r["blocked"] > 0 for r in rs)}
            if kind == "attack":
                out["configs"][c][kind]["asr"] = analyse.rate(rs, "attack_success")
        out["attack_successes"][c] = [[r["user_task"], r["injection_task"]] for r in rows
                                      if r["config"] == c and r["attack_success"]]
    for ref in ("b0", "b1"):  # D1h+D2 against each baseline, on the same user task (utility) or pair (under attack)
        if "d1hd2" not in configs or ref not in configs:
            continue
        res = {}
        for kind in ("utility", "attack"):
            keys = [k[1:] for k in by if k[0] == ref and k[1] == kind and ("d1hd2", *k[1:]) in by]
            b = sum(by[("d1hd2", *k)]["utility"] and not by[(ref, *k)]["utility"] for k in keys)
            c_ = sum(by[(ref, *k)]["utility"] and not by[("d1hd2", *k)]["utility"] for k in keys)
            res[kind] = {"d1hd2_only": b, f"{ref}_only": c_, "p": analyse.mcnemar_exact(b, c_)}
        out["mcnemar"][f"{ref}_vs_d1hd2"] = res
    return out


def main() -> int:
    s = full_summary()
    if s is None or s.get("aborted"):
        print("no finished full AgentDojo run yet; nothing written")
        return 1
    configs = [c for c in CONFIGS if c in s["configs"]]
    progress = analyse.RESULTS / "progress" / f"{s['run_id']}.jsonl"
    if progress.exists():
        rows = [json.loads(l) for l in progress.read_text(encoding="utf-8").splitlines() if l.strip()]
        out = {"run_id": s["run_id"], "code_version": s["code_version"], **analyse_rows(rows, configs)}
        (analyse.RESULTS / "analysis_agentdojo.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    analyse.figures(as_analysis(s), configs, "_agentdojo", heatmap=False)
    print(f"wrote AgentDojo analysis and figures for {configs} (run {s['run_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
