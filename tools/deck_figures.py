"""Slide charts for the final deck, with plain-English configuration names on the axis.

    python tools/deck_figures.py          (from the repo root; build_deck.py runs it too)

Reads only sandbox/results/final_tables.json (the numbers the deck and report already use) and writes
sandbox/results/figures/deck_*.png. No result file is changed. Colours and chart style follow
sandbox/src/analyse.py: attack success in blue, normal-task success in orange (its validated pair),
95% Wilson intervals as whiskers.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "sandbox" / "results"
FIGS = RESULTS / "figures"

INK, INK2, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#ffffff"
ATTACK, NORMAL = "#2a78d6", "#eb6834"   # analyse.py slots 1-2
GUARDED = INK2                          # "with the gate" bars on the generalisation chart (direct-labelled)
NAME = {"b0": "B0\nno defense", "b1": "B1\nDual-LLM", "d1h": "D1h\nprovenance", "d2": "D2\npolicy",
        "d1hd2": "D1h+D2\nboth", "d1hl": "D1h-L\ntrusts contacts"}


def _style(fs=13):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": fs, "axes.edgecolor": AXIS,
                         "axes.labelcolor": INK2, "xtick.color": INK, "ytick.color": INK2,
                         "figure.facecolor": SURF, "axes.facecolor": SURF})


def _axes(ax, top=115):
    ax.set_ylim(0, top)
    ax.set_ylabel("% of episodes")
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0, pad=6)


def _legend(fig, items):
    """Legend in one row above the plot (proxy patches, so each swatch has its series colour)."""
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c, label=lab) for c, lab in items], frameon=False, fontsize=10.5, columnspacing=1.2,
               loc="upper center", ncol=len(items), labelcolor=INK2, handlelength=1.2, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.92))


def _bar(ax, x, r, w, color, fs):
    """One bar with its 95% interval and a value label above the whisker."""
    v = 100 * r["k"] / r["n"]
    lo, hi = (100 * c for c in r["ci95"])
    ax.bar(x, v, w, color=color, zorder=2)
    ax.errorbar(x, v, yerr=[[v - lo], [hi - v]], fmt="none", ecolor=INK2, elinewidth=1.2, capsize=3, zorder=3)
    ax.text(x, hi + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=fs, color=INK)


def attack_vs_normal(t, key, out, cfgs=("b0", "b1", "d1h", "d2", "d1hd2")):
    """Slides 9-10: attack success and normal-task success per configuration."""
    d = t[key]["configs"]
    _style()
    fig, ax = plt.subplots(figsize=(6.1, 3.95), dpi=300)
    w = 0.36
    for i, c in enumerate(cfgs):
        _bar(ax, i - w / 2 - 0.01, d[c]["asr"], w, ATTACK, 12)
        _bar(ax, i + w / 2 + 0.01, d[c]["utility"], w, NORMAL, 12)
    ax.set_xticks(range(len(cfgs)), [NAME[c] for c in cfgs], fontsize=11)
    _axes(ax)
    _legend(fig, [(ATTACK, "Attack success (lower is better)"), (NORMAL, "Normal tasks done (higher is better)")])
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def generalise(t, out):
    """Slide 11: attack success with no defense vs with both checks, on three settings."""
    ad = t["agentdojo"]["configs"]

    def ad_rate(c):
        k = round(ad[c]["asr"] * ad[c]["n_attack"])
        n = ad[c]["n_attack"]
        from math import sqrt
        z, p = 1.96, k / n  # Wilson interval, as in analyse.py
        den = 1 + z * z / n
        mid = (p + z * z / (2 * n)) / den
        h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return {"k": k, "n": n, "ci95": [max(0, mid - h), min(1, mid + h)]}

    groups = [("Qwen3-8B\nour held-out set", t["heldout"]["configs"]["b0"]["asr"], t["heldout"]["configs"]["d1hd2"]["asr"]),
              ("Qwen2.5-7B\nsecond model", t["qwen25"]["configs"]["b0"]["asr"], t["qwen25"]["configs"]["d1hd2"]["asr"]),
              ("AgentDojo\npublic benchmark", ad_rate("b0"), ad_rate("d1hd2"))]
    _style()
    fig, ax = plt.subplots(figsize=(6.1, 3.95), dpi=300)
    w = 0.36
    for i, (_, b0, both) in enumerate(groups):
        _bar(ax, i - w / 2 - 0.01, b0, w, ATTACK, 12)
        _bar(ax, i + w / 2 + 0.01, both, w, GUARDED, 12)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups], fontsize=11)
    _axes(ax, top=50)
    ax.set_ylabel("% of attacks that worked")
    _legend(fig, [(ATTACK, "B0 · no defense"), (GUARDED, "D1h+D2 · both checks")])
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def links(t, out, cfgs=("b0", "d1h", "d1hd2", "d1hl")):
    """Slide 13: normal tasks with links done, per configuration (one series)."""
    d = t["links"]["configs"]
    _style()
    fig, ax = plt.subplots(figsize=(6.1, 3.95), dpi=300)
    for i, c in enumerate(cfgs):
        _bar(ax, i, d[c]["utility"], 0.55, NORMAL, 13)
    ax.set_xticks(range(len(cfgs)), [NAME[c] for c in cfgs], fontsize=11)
    _axes(ax)
    ax.set_ylabel("% of normal link tasks done")
    fig.tight_layout()
    fig.savefig(out, facecolor=SURF)
    plt.close(fig)


def main():
    t = json.loads((RESULTS / "final_tables.json").read_text(encoding="utf-8"))
    FIGS.mkdir(exist_ok=True)
    made = []
    for key, name in (("dev", "deck_dev.png"), ("heldout", "deck_heldout.png")):
        if t.get(key):
            attack_vs_normal(t, key, FIGS / name)
            made.append(name)
    if all(t.get(k) for k in ("heldout", "qwen25", "agentdojo")):
        generalise(t, FIGS / "deck_generalise.png")
        made.append("deck_generalise.png")
    if t.get("links"):
        links(t, FIGS / "deck_links.png")
        made.append("deck_links.png")
    print("wrote " + ", ".join(made))


if __name__ == "__main__":
    main()
