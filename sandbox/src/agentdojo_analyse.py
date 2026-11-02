"""Analysis + figure for the full AgentDojo runs (one per attack) and the attack-selection spike.

    python src/agentdojo_analyse.py            (host, from sandbox/)

Reads only numbers: results/agentdojo_summary_*.json and its progress file
results/progress/<run_id>.jsonl (one row per episode: ids, booleans, counts). Writes
results/analysis_agentdojo.json (timeouts per kind, utility without timed-out episodes,
paired McNemar tests on the same user task / pair, injection exposure where recorded) and
results/figures/fig1_asr_vs_utility{,_col,_slide}_agentdojo.png for the important_instructions run;
results/analysis_agentdojo_<attack>.json and figures *_agentdojo_<attack>.png for any other attack;
results/analysis_agentdojo_spike.json for the B0-only spike runs of the main model (fewer than 40 user tasks,
with no-attack rows reused from a full run, or attack episodes only), and
results/analysis_agentdojo_spike_models.json for every model x attack cell of the spike (2 Nov).
A full run of another model than MAIN_MODEL is written with the model in the name, e.g.
analysis_agentdojo_llama3.1-8b_test_framing.json.
"""
from __future__ import annotations

import json
import sys

import analyse

CONFIGS = ["b0", "b1", "d1hd2"]
FIRST_ATTACK = "important_instructions"
MAIN_MODEL = "qwen3:8b"


def model_of(s: dict) -> str:
    return s.get("model", MAIN_MODEL)


def run_tag(model: str, attack: str) -> str:
    """'' for the first run, '_<attack>' for other attacks on the main model, '_<model>_<attack>' otherwise."""
    if model == MAIN_MODEL:
        return "" if attack == FIRST_ATTACK else f"_{attack}"
    return f"_{model.replace(':', '-')}_{attack}"


def summaries() -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(analyse.RESULTS.glob("agentdojo_summary_*.json"))]


def full_summaries() -> dict[str, dict]:
    """Per run tag (model and attack), the newest summary of a full run (40 user tasks, not a spike);
    the main model's important_instructions run first."""
    out = {}
    for s in summaries():
        if s.get("user_tasks", 0) >= 40:
            out[run_tag(model_of(s), s.get("attack", FIRST_ATTACK))] = s
    return dict(sorted(out.items(), key=lambda kv: kv[0] != ""))


def spike_summaries() -> list[dict]:
    """The attack-selection spike: partial runs that reused a full run's no-attack rows or ran attacks only."""
    return [s for s in summaries() if s.get("user_tasks", 0) < 40 and (s.get("utility_from") or s.get("attacks_only"))]


def read_rows(run_id: str) -> list[dict] | None:
    p = analyse.RESULTS / "progress" / f"{run_id}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else None


def exposure(rs: list[dict]) -> dict | None:
    """Attack episodes where the injection reached the model, and attack success among those."""
    if not rs or any("exposed" not in r for r in rs):
        return None  # recorded only from commit 957dedb on
    exp = [r for r in rs if r["exposed"]]
    return {"exposed": {"k": len(exp), "n": len(rs)}, "asr_given_exposed": analyse.rate(exp, "attack_success")}


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
                if (e := exposure(rs)) is not None:
                    out["configs"][c][kind].update(e)
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


def spike() -> int:
    cells: dict[str, dict] = {}  # model -> attack -> cell; a newer run of the same cell replaces an older one
    for s in spike_summaries():
        rows = read_rows(s["run_id"])
        att = [r for r in rows or [] if r["kind"] == "attack" and r["config"] == "b0"]
        if not att or s.get("aborted"):
            continue
        cells.setdefault(model_of(s), {})[s.get("attack", FIRST_ATTACK)] = {
            "run_id": s["run_id"], "seed": s.get("seed"), "user_tasks": s["user_tasks"],
            "asr": analyse.rate(att, "attack_success"), "timed_out_episodes": sum(bool(r["llm_errors"]) for r in att),
            **(exposure(att) or {})}
    if MAIN_MODEL in cells:
        (analyse.RESULTS / "analysis_agentdojo_spike.json").write_text(json.dumps(cells[MAIN_MODEL], indent=2),
                                                                       encoding="utf-8")
        print(f"wrote the attack-selection spike for {sorted(cells[MAIN_MODEL])}")
    if set(cells) - {MAIN_MODEL}:
        (analyse.RESULTS / "analysis_agentdojo_spike_models.json").write_text(json.dumps(cells, indent=2),
                                                                              encoding="utf-8")
        print(f"wrote the model x attack spike for {sorted(cells)}")
    return sum(len(v) for v in cells.values())


def main() -> int:
    n_spike = spike()
    runs = {a: s for a, s in full_summaries().items() if not s.get("aborted")}
    if not runs:
        print("no finished full AgentDojo run yet; nothing written")
        return 0 if n_spike else 1
    for tag, s in runs.items():
        attack = s.get("attack", FIRST_ATTACK)
        configs = [c for c in CONFIGS if c in s["configs"]]
        rows = read_rows(s["run_id"])
        if rows is not None:
            out = {"run_id": s["run_id"], "attack": attack, "model": model_of(s), "code_version": s["code_version"],
                   "utility_from": s.get("utility_from"), **analyse_rows(rows, configs)}
            (analyse.RESULTS / f"analysis_agentdojo{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
        analyse.figures(as_analysis(s), configs, f"_agentdojo{tag}", heatmap=False)
        print(f"wrote AgentDojo analysis and figures for {model_of(s)} {attack}, {configs} (run {s['run_id']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
