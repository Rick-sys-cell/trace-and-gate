"""Final report tables: collect every numbers-only result file into one place.

    python src/report_tables.py          (host, from sandbox/)

Writes results/final_tables.json and results/final_tables.md. Every number comes from an
analysis_*, block_reasons_* or agentdojo_summary_* file named in the output; a missing input
is shown as PENDING, never estimated.
"""
from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"
ORDER = ["b0", "b1", "d1h", "d2", "d1hd2", "d1hl", "d1hld2"]
LABEL = {"b0": "B0 none", "b1": "B1 Dual-LLM", "d1h": "D1h", "d2": "D2", "d1hd2": "D1h+D2",
         "d1hl": "D1h-L*", "d1hld2": "D1h-L+D2*"}
DATASETS = [  # (key, title, analysis file)
    ("dev", "Dev suite v3 (1 run)", "analysis_dev_v3.json"),
    ("heldout", "Held-out (3 runs)", "analysis_heldout.json"),
    ("qwen25", "Held-out, Qwen2.5-7B (1 run)", "analysis_heldout_qwen25.json"),
    ("d1hl_dev", "D1h-L on dev v3 (1 run)", "analysis_d1hl_dev.json"),
    ("d1hl_heldout", "D1h-L on held-out (1 run)", "analysis_d1hl_heldout.json"),
    ("links", "Benign links (3 runs)", "analysis_links.json"),
]
FLOWS = ["ask", "forward", "reply-own", "send-link", "send-noncontact"]


def load(name):
    p = RESULTS / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def pct(r):
    """'45.4% (44/97)' from an analyse.py rate dict."""
    if not r or not r.get("n"):
        return "–"
    return f"{100 * r['k'] / r['n']:.1f}% ({r['k']}/{r['n']})"


def ci(r):
    if not r or not r.get("ci95"):
        return "–"
    lo, hi = r["ci95"]
    return f"{100 * lo:.1f}–{100 * hi:.1f}%"


def frac(k, n):
    return f"{100 * k / n:.1f}% ({k}/{n})" if n else "–"


def main_table(a):
    rows = ["| Config | Attack success | 95% CI | Normal tasks done | Done under attack | s/episode | LLM calls | Tokens |",
            "|---|---|---|---|---|---|---|---|"]
    for cfg in [c for c in ORDER if c in a["configs"]]:
        c = a["configs"][cfg]
        calls = c["mean_llm_calls"] + c.get("mean_reader_calls", 0)
        rows.append(f"| {LABEL[cfg]} | {pct(c['asr'])} | {ci(c['asr'])} | {pct(c['utility'])} | "
                    f"{pct(c['utility_under_attack'])} | {c['mean_seconds']:.1f} | {calls:.1f} | {c['mean_tokens']:.0f} |")
    return rows


def mcnemar_rows(a):
    rows = []
    for name, m in a.get("mcnemar", {}).items():
        ref, other = name.split("_vs_")
        at, be = m["attack"], m["benign"]
        o, r = LABEL.get(other, other), LABEL.get(ref, ref)
        rows.append(f"- {r} vs {o} (paired episodes where only one succeeded): attacks succeeded only under {o} "
                    f"{at['other_only']}, only under {r} {at[ref + '_only']} (p = {at['p']}); normal tasks done only "
                    f"under {o} {be['other_only']}, only under {r} {be[ref + '_only']} (p = {be['p']})")
    return rows


SOURCE = {"team": "Team-written", "llmail": "LLMail-Inject", "template": "Template"}


def source_table(a, bucket="by_source", names=SOURCE):
    """Attack success (and the user's task under attack) per attack source or style, per config."""
    groups = sorted({g for c in a.get(bucket, {}).values() for g in c})
    cfgs = [c for c in ORDER if c in a.get(bucket, {})]
    rows = ["| Attacks | " + " | ".join(LABEL[c] for c in cfgs) + " |", "|---|" + "---|" * len(cfgs)]
    for g in groups:
        rows.append(f"| {names.get(g, g)} | " + " | ".join(
            f"{pct(a[bucket][c][g]['asr'])}; task done {pct(a[bucket][c][g]['utility_under_attack'])}"
            if g in a[bucket][c] else "–" for c in cfgs) + " |")
    return rows


def _p(v):
    return "–" if v is None else f"{100 * v:.1f}"


def per_run_line(a):
    pr = a.get("per_run", {})
    if not pr:
        return []
    return ["Per run (attack success / normal tasks done): " + "; ".join(
        f"{LABEL[c]} " + ", ".join(f"{_p(v['asr'])}/{_p(v['utility'])}" for v in pr[c].values())
        for c in ORDER if c in pr)]


def link_table(br):
    cfgs = [c for c in ORDER if c in br["configs"] and br["configs"][c].get("link_flows")]
    rows = ["| Flow | " + " | ".join(LABEL[c] for c in cfgs) + " |", "|---|" + "---|" * len(cfgs)]
    for f in FLOWS:
        cells = []
        for c in cfgs:
            v = br["configs"][c]["link_flows"].get(f)
            cells.append(f"{frac(v['utility'], v['n'])}, blocked {v['blocked']}" if v else "–")
        rows.append(f"| {f} | " + " | ".join(cells) + " |")
    return rows


def block_table(br):
    rows = ["| Config | Normal episodes with a block | Rules that fired on normal tasks (distinct tasks) | "
            "Secret read, then external send (not scored as attack) |", "|---|---|---|---|"]
    for cfg in [c for c in ORDER if c in br["configs"]]:
        c = br["configs"][cfg]
        rules = ", ".join(f"{r} ({len(ids)})" for r, ids in c["false_blocks"].items()) or "none"
        iso = c["isolation"]
        rows.append(f"| {LABEL[cfg]} | {frac(c['benign_episodes_with_block'], c['benign_episodes'])} | {rules} | "
                    f"{iso.get('read_secret_then_external_send', 0)} ({iso.get('of_which_not_scored_as_attack', 0)}) |")
    return rows


def agentdojo_table(s):
    rows = ["| Config | Attack success | 95% CI | Utility (no attack) | Utility under attack | Normal tasks with a block | s/episode |",
            "|---|---|---|---|---|---|---|"]
    for cfg in [c for c in ORDER if c in s["configs"]]:
        c = s["configs"][cfg]
        k_a = round(c["asr"] * c["n_attack"]) if c["asr"] is not None else 0
        k_u = round(c["utility"] * c["n_utility"]) if c["utility"] is not None else 0
        lo, hi = c["asr_ci95"] or (0, 0)
        rows.append(f"| {LABEL[cfg]} | {frac(k_a, c['n_attack'])} | {100 * lo:.1f}–{100 * hi:.1f}% | "
                    f"{frac(k_u, c['n_utility'])} | {100 * (c['utility_under_attack'] or 0):.1f}% | "
                    f"{c['false_block_episodes']}/{c['n_utility']} | {c['mean_seconds']} |")
    return rows


def newest_agentdojo():
    files = sorted(RESULTS.glob("agentdojo_summary_*.json"))
    full = [f for f in files if json.loads(f.read_text(encoding="utf-8")).get("user_tasks", 0) >= 40]
    pick = (full or files or [None])[-1]
    return (pick.name, json.loads(pick.read_text(encoding="utf-8"))) if pick else (None, None)


def build():
    out, md = {"sources": {}}, ["# Final tables (generated by src/report_tables.py; do not edit by hand)", "",
                                "\\* exploratory, added after the defenses were frozen.", ""]
    for key, title, name in DATASETS:
        a = load(name)
        md += [f"## {title}", f"Source: `results/{name}`", ""]
        if a is None:
            md += ["PENDING", ""]
            continue
        out["sources"][key] = name
        out[key] = {"run_id": a["run_id"], "model": a["model"], "runs": a.get("runs", 1), "aborted": a.get("aborted"),
                    "ollama_version": a.get("ollama_version"), "code_version": a.get("code_version"),
                    "configs": a["configs"], "mcnemar": a.get("mcnemar", {}), "per_run": a.get("per_run", {})}
        md += [f"Run `{a['run_id']}`, {a['model']}, Ollama {a.get('ollama_version')}, code {a.get('code_version')}, "
               f"{a.get('runs', 1)} run(s), aborted: {a.get('aborted')}", ""] + main_table(a) + [""]
        md += per_run_line(a) + [""] + mcnemar_rows(a) + [""]
        if len({g for c in a.get("by_source", {}).values() for g in c}) > 1:
            out[key]["by_source"] = a["by_source"]
            md += ["Attack success by source (pooled over runs):", ""] + source_table(a) + [""]
            if any(a.get("by_style", {}).values()):
                out[key]["by_style"] = a["by_style"]
                md += ["Team-written attacks by style:", ""] + source_table(a, "by_style", {}) + [""]
    for tag, title in (("links", "Benign links: utility by flow"), ("heldout", "Failure analysis: held-out"),
                       ("dev_v3", "Failure analysis: dev v3")):
        name = f"block_reasons_{tag}.json"
        br = load(name)
        md += [f"## {title}", f"Source: `results/{name}`", ""]
        if br is None:
            md += ["PENDING", ""]
            continue
        out["sources"][f"block_reasons_{tag}"] = name
        out[f"block_reasons_{tag}"] = br["configs"]
        md += (link_table(br) if tag == "links" else []) + [""] + block_table(br) + [""]
    name, s = newest_agentdojo()
    md += ["## AgentDojo workspace", f"Source: `results/{name}`" if name else "", ""]
    if s is None:
        md += ["PENDING", ""]
    else:
        out["sources"]["agentdojo"] = name
        out["agentdojo"] = s
        md += [f"Run `{s['run_id']}`, suite {s['suite']}, attack `{s['attack']}`, {s['user_tasks']} user tasks x "
               f"{s['pairs_per_task']} injection tasks, {s['model']}, agentdojo {s['agentdojo_version']}, "
               f"aborted: {s['aborted']}" + ("" if s["user_tasks"] >= 40 else " **(timing spike, not the full run)**"),
               ""] + agentdojo_table(s) + [""]
    (RESULTS / "final_tables.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (RESULTS / "final_tables.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote results/final_tables.json and .md from {len(out['sources'])} sources: {sorted(out['sources'])}")


if __name__ == "__main__":
    build()
