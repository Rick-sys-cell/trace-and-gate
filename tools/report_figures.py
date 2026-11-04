"""Report figures with plain-English version names on the axes (Rui, 4 Nov: no short codes in the report).

    python tools/report_figures.py          (from the repo root)

Redraws Figs. 1-6 of 3_Sources/Final_Report.md in the report's one-column style, the same way as the
"col" figures of sandbox/src/analyse.py (same colours, 95% Wilson whiskers, heatmap ramp), from the
analysis files only: sandbox/results/analysis_{dev_v3,heldout,heldout_qwen25,heldout_camel}.json and the
AgentDojo summary (via agentdojo_analyse.as_analysis). Writes sandbox/results/figures/report_fig*.png.
analyse.py and its figures are not changed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "sandbox" / "results"
FIGS = RESULTS / "figures"

INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#ffffff"
S1, S2 = "#2a78d6", "#eb6834"  # analyse.py's validated categorical pair
NAME = {"b0": "No\ndefense", "b1": "Second-AI\nreader", "d1h": "Source\ncheck", "d2": "Tool\nallowlist",
        "d1hd2": "Both\nchecks"}
ROWS = {"attachment": "Attachment", "body": "Body", "subject": "Subject", "multiturn": "Multi-turn",
        "llmail": "LLMail-Inject"}
ORDER = ["b0", "b1", "d1h", "d2", "d1hd2"]
W, FS, SMALL, CELL = 3.45, 7, 6, 5.8  # analyse.py "col" spec


def _style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": FS, "axes.edgecolor": AXIS,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})


def bars(out, configs, path):
    """Fig. 1 style: attack success and normal-task success per version, with 95% intervals."""
    _style()
    fig, ax = plt.subplots(figsize=(W, 2.75), dpi=300)
    xs = range(len(configs))
    w = 0.36
    for off, key, color, name in ((-w / 2 - 0.01, "asr", S1, "Attack success"),
                                  (w / 2 + 0.01, "utility", S2, "Normal-task success")):
        vals = [out["configs"][c][key]["rate"] * 100 for c in configs]
        cis = [out["configs"][c][key]["ci95"] for c in configs]
        err = [[v - ci[0] * 100 for v, ci in zip(vals, cis)], [ci[1] * 100 - v for v, ci in zip(vals, cis)]]
        ax.bar([x + off for x in xs], vals, w, color=color, label=name, zorder=2)
        ax.errorbar([x + off for x in xs], vals, yerr=err, fmt="none", ecolor=INK2, elinewidth=0.8, capsize=1.5,
                    zorder=3)
        for x, v, ci in zip(xs, vals, cis):
            ax.text(x + off, ci[1] * 100 + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=SMALL, color=INK)
    ax.set_xticks(list(xs), [NAME[c] for c in configs], fontsize=SMALL)
    ax.set_ylim(0, 115)
    ax.set_ylabel("% of episodes")
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.legend(frameon=False, fontsize=SMALL, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.15),
              labelcolor=INK2, handlelength=1.2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)


def heatmap(out, configs, path):
    """Fig. 3 style: attack success by where the attack was hidden x version."""
    _style()
    chans = [ch for ch in ROWS if any(out["by_channel"][c].get(ch) for c in configs)]
    ramp = LinearSegmentedColormap.from_list("blue", ["#fcfcfb", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
    data = [[out["by_channel"][c].get(ch, {}).get("rate") or 0 for c in configs] for ch in chans]
    fig, ax = plt.subplots(figsize=(W, 2.2 * (0.4 + 0.6 * len(chans) / 5) + 0.15), dpi=300)
    ax.imshow(data, cmap=ramp, vmin=0, vmax=1, aspect="auto")
    for i, ch in enumerate(chans):
        for j, c in enumerate(configs):
            r = out["by_channel"][c].get(ch)
            v = data[i][j]
            ax.text(j, i, f"{v * 100:.0f}%\n({r['k']}/{r['n']})" if r else "-", ha="center", va="center",
                    fontsize=CELL, color="#ffffff" if v > 0.45 else INK)
    ax.set_xticks(range(len(configs)), [NAME[c] for c in configs], fontsize=SMALL)
    ax.set_yticks(range(len(chans)), [ROWS[ch] for ch in chans])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(1, len(configs))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(chans))], minor=True)
    ax.grid(which="minor", color=SURF, linewidth=2)
    ax.tick_params(which="both", length=0)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURF)
    plt.close(fig)


def main():
    FIGS.mkdir(exist_ok=True)
    made = []
    for tag in ("dev_v3", "heldout", "heldout_qwen25", "heldout_camel"):
        p = RESULTS / f"analysis_{tag}.json"
        if not p.exists():
            print(f"warning: {p.relative_to(ROOT)} missing; report_fig1_{tag}.png not drawn")
            continue
        out = json.loads(p.read_text(encoding="utf-8"))
        configs = [c for c in ORDER if c in out["configs"]]
        bars(out, configs, FIGS / f"report_fig1_{tag}.png")
        made.append(f"report_fig1_{tag}.png")
        if tag == "heldout":
            heatmap(out, configs, FIGS / "report_fig2_heldout.png")
            made.append("report_fig2_heldout.png")
    sys.path.insert(0, str(ROOT / "sandbox" / "src"))
    import agentdojo_analyse as ad
    runs = {t: s for t, s in ad.full_summaries().items() if not s.get("aborted")}
    if "" in runs:  # the main workspace run (Fig. 5); attack-trial runs have their own tags
        s = runs[""]
        bars(ad.as_analysis(s), [c for c in ORDER if c in s["configs"]], FIGS / "report_fig1_agentdojo.png")
        made.append("report_fig1_agentdojo.png")
    print("wrote " + ", ".join(made))


if __name__ == "__main__":
    main()
