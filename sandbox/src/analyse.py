"""Analyse results/summary.json -> results/analysis.json + results/figures/*.png.

    python src/analyse.py            (host, from sandbox/)

Numbers and task ids only: reads summary.json and the task metadata (ids, type,
goal, channel), never payload text or raw transcripts.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
ORDER = ["b0", "b1", "d1", "d1h", "d2", "d1d2", "d1hd2"]
LABEL = {"b0": "B0 none", "b1": "B1 Dual-LLM", "d1": "D1 provenance", "d1h": "D1h", "d2": "D2 policy", "d1d2": "D1+D2", "d1hd2": "D1h+D2"}


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value for discordant counts b, c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return float(f"{min(1.0, 2 * tail):.3g}")


def rate(rows, key):
    k = sum(bool(r[key]) for r in rows)
    return {"k": k, "n": len(rows), "rate": round(k / len(rows), 4) if rows else None, "ci95": wilson(k, len(rows))}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=str(RESULTS / "summary.json"))
    ap.add_argument("--tag", default="", help="suffix for analysis_<tag>.json and figure names")
    args = ap.parse_args()
    tag = f"_{args.tag}" if args.tag else ""
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    suite_file = ROOT / "benchmark" / "tasks" / summary.get("tasks_file", "email_suite.json")
    meta = {t["id"]: t for t in json.loads(suite_file.read_text(encoding="utf-8"))}
    configs = [c for c in ORDER if c in summary["configs"]]
    rows = {}
    for cfg in configs:
        rows[cfg] = []
        for key, v in summary["configs"][cfg]["per_task"].items():
            t = meta[key.split("#")[0]]
            rows[cfg].append({**v, "id": t["id"], "key": key, "run": int(key.split("#run")[1]) if "#run" in key else 0,
                              "type": t["type"], "goal": t.get("goal"),
                              "channel": t.get("channel"), "control_for": t.get("control_for")})

    out = {"run_id": summary["run_id"], "model": summary["model"], "aborted": summary.get("aborted"),
           "runs": summary.get("runs", 1), "ollama_version": summary.get("ollama_version"),
           "code_version": summary.get("code_version"),
           "configs": {}, "by_channel": {}, "by_goal": {}, "controls": {}, "mcnemar": {}, "per_run": {}}
    for cfg in configs:
        c = summary["configs"][cfg]
        att = [r for r in rows[cfg] if r["type"] == "attack"]
        ben = [r for r in rows[cfg] if r["type"] == "benign"]
        out["configs"][cfg] = {
            "label": LABEL[cfg], "asr": rate(att, "attack_success"), "utility": rate(ben, "utility"),
            "utility_under_attack": rate(att, "utility"),
            "false_block_rate": c.get("false_block_rate"), "blocked_calls": c["blocked_calls"],
            "errors_or_caps": c["timeouts"], "mean_seconds": c["mean_seconds"],
            "mean_llm_calls": c["mean_llm_calls"], "mean_reader_calls": c.get("mean_reader_calls", 0),
            "mean_tokens": c["mean_tokens"]}
        runs = sorted({r["run"] for r in rows[cfg]})
        if len(runs) > 1:  # spread across repeated runs (pooled numbers above)
            out["per_run"][cfg] = {
                f"run{n}": {"asr": rate([r for r in att if r["run"] == n], "attack_success")["rate"],
                            "utility": rate([r for r in ben if r["run"] == n], "utility")["rate"]} for n in runs}
        for field, bucket in (("channel", "by_channel"), ("goal", "by_goal")):
            groups = defaultdict(list)
            for r in att:
                groups["llmail" if r["goal"] == "llmail" and field == "channel" else r[field]].append(r)
            out[bucket][cfg] = {g: rate(rs, "attack_success") for g, rs in sorted(groups.items())}
        # controls vs matching LLMail attack tasks: distraction effect on the user's task
        for mode in ("ask", "send"):
            ctrl = [r for r in ben if r["control_for"] == f"llmail-{mode}"]
            lm = [r for r in att if r["goal"] == "llmail"
                  and ("sent_to" in meta[r["id"]]["utility"]) == (mode == "send")]
            out["controls"].setdefault(cfg, {})[mode] = {"no_attack_utility": rate(ctrl, "utility"),
                                                         "under_llmail_attack_utility": rate(lm, "utility")}
    # paired tests (same task and run): the combined defense against every other config
    # (attacks: ASR; benign: utility). D1h+D2 is the reference from Week 10 on.
    refcfg = next((c for c in ("d1hd2", "d1d2") if c in configs), None)
    if refcfg:
        ref = {r["key"]: r for r in rows[refcfg]}
        for cfg in configs:
            if cfg == refcfg:
                continue
            other = {r["key"]: r for r in rows[cfg]}
            res = {}
            for kind, key in (("attack", "attack_success"), ("benign", "utility")):
                ids = [i for i in ref if ref[i]["type"] == kind and i in other]
                b = sum(bool(other[i][key]) and not ref[i][key] for i in ids)
                c = sum(bool(ref[i][key]) and not other[i][key] for i in ids)
                res[kind] = {"other_only": b, f"{refcfg}_only": c, "p": mcnemar_exact(b, c)}
            out["mcnemar"][f"{refcfg}_vs_{cfg}"] = res
    out["tasks_file"] = suite_file.name
    (RESULTS / f"analysis{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    figures(out, configs, tag)
    print(f"wrote analysis{tag}.json and figures for {configs}")


def figures(out, configs, tag=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
    S1, S2 = "#2a78d6", "#eb6834"  # reference categorical slots 1-2 (validated adjacent pair)
    figdir = RESULTS / "figures"
    figdir.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})

    SHORT = {"b0": "B0", "b1": "B1", "d1": "D1", "d1h": "D1h", "d2": "D2", "d1d2": "D1+D2", "d1hd2": "D1h+D2"}
    # "wide" = slides (7.2 in); "col" = one IEEE column of the report (3.45 in, white paper)
    specs = {"wide": dict(w=7.2, h1=3.6, h2=3.2, fs=10, small=8, cell=7.5, labels=LABEL, surf=SURF, suffix="",
                          names={"attachment": "Attachment", "body": "Email body", "subject": "Subject line",
                                 "multiturn": "Multi-turn", "llmail": "LLMail-Inject (real)"}),
             "slide": dict(w=6.1, h1=3.85, h2=3.85, fs=13, small=12, cell=11, labels=SHORT, surf="#ffffff",
                           suffix="_slide",
                           names={"attachment": "Attachment", "body": "Email body", "subject": "Subject line",
                                  "multiturn": "Multi-turn", "llmail": "LLMail-Inject"}),
             "col": dict(w=3.45, h1=2.55, h2=2.2, fs=7, small=6, cell=5.8, labels=SHORT, surf="#ffffff", suffix="_col",
                         names={"attachment": "Attachment", "body": "Body", "subject": "Subject",
                                "multiturn": "Multi-turn", "llmail": "LLMail-Inject"})}
    names1 = {"wide": ("Attack success (lower is better)", "Normal-task success (higher is better)"),
              "col": ("Attack success", "Normal-task success"), "slide": ("Attack success", "Normal-task success")}
    for mode, sp in specs.items():
        plt.rcParams.update({"font.size": sp["fs"], "figure.facecolor": sp["surf"], "axes.facecolor": sp["surf"]})

        # Fig 1: attack success vs normal-task success per config (one % axis, grouped bars)
        fig, ax = plt.subplots(figsize=(sp["w"], sp["h1"]), dpi=200 if mode == "wide" else 300)
        xs = range(len(configs))
        w = 0.36
        for (off, key, color), name in zip(((-w / 2 - 0.01, "asr", S1), (w / 2 + 0.01, "utility", S2)), names1[mode]):
            vals = [out["configs"][c][key]["rate"] * 100 for c in configs]
            cis = [out["configs"][c][key]["ci95"] for c in configs]
            err = [[v - ci[0] * 100 for v, ci in zip(vals, cis)], [ci[1] * 100 - v for v, ci in zip(vals, cis)]]
            ax.bar([x + off for x in xs], vals, w, color=color, label=name, zorder=2)
            ax.errorbar([x + off for x in xs], vals, yerr=err, fmt="none", ecolor=INK2,
                        elinewidth=0.8 if mode == "col" else 1.2, capsize=1.5 if mode == "col" else 3, zorder=3)
            for x, v, ci in zip(xs, vals, cis):  # label sits above the CI whisker
                ax.text(x + off, ci[1] * 100 + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=sp["small"], color=INK)
        ax.set_xticks(list(xs), [sp["labels"][c] for c in configs])
        ax.set_ylim(0, 115)
        ax.set_ylabel("% of episodes")
        ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        ax.legend(frameon=False, fontsize=sp["small"], loc="upper center", ncol=2,
                  bbox_to_anchor=(0.5, 1.13 if mode == "wide" else 1.15), labelcolor=INK2, handlelength=1.2)
        fig.tight_layout()
        fig.savefig(figdir / f"fig1_asr_vs_utility{sp['suffix']}{tag}.png", facecolor=sp["surf"])
        plt.close(fig)

        # Fig 2: heatmap, attack success by hiding place x config (sequential blue ramp)
        chans = ["attachment", "body", "subject", "multiturn", "llmail"]
        ramp = LinearSegmentedColormap.from_list("blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
        data = [[out["by_channel"][c].get(ch, {}).get("rate") or 0 for c in configs] for ch in chans]
        fig, ax = plt.subplots(figsize=(sp["w"], sp["h2"]), dpi=200 if mode == "wide" else 300)
        ax.imshow(data, cmap=ramp, vmin=0, vmax=1, aspect="auto")
        for i, ch in enumerate(chans):
            for j, c in enumerate(configs):
                r = out["by_channel"][c].get(ch)
                v = data[i][j]
                ax.text(j, i, f"{v * 100:.0f}%\n({r['k']}/{r['n']})" if r else "-", ha="center", va="center",
                        fontsize=sp["cell"], color="#ffffff" if v > 0.45 else INK)
        ax.set_xticks(range(len(configs)), [sp["labels"][c] for c in configs])
        ax.set_yticks(range(len(chans)), [sp["names"][ch] for ch in chans])
        for sp_ in ax.spines.values():
            sp_.set_visible(False)
        ax.set_xticks([x - 0.5 for x in range(1, len(configs))], minor=True)
        ax.set_yticks([y - 0.5 for y in range(1, len(chans))], minor=True)
        ax.grid(which="minor", color=sp["surf"], linewidth=2)
        ax.tick_params(which="both", length=0)
        fig.tight_layout()
        fig.savefig(figdir / f"fig2_asr_by_channel{sp['suffix']}{tag}.png", facecolor=sp["surf"])
        plt.close(fig)


if __name__ == "__main__":
    main()
