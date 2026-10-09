"""plots.py - figures for the README from results/scores_test.csv.

  results/f1_vs_size.png      F1 vs graph size per condition, one panel per level
  results/ci_differences.png  paired F1 differences (C - A, C - B, C - B+) with 95% bootstrap CIs
Run: python plots.py
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from score import RESULTS, THESIS_LEVELS, paired_bootstrap

NODES = {20: 24, 100: 117, 500: 553}  # size label -> actual node count (replicas included)
CONDS = ["A", "B", "Bplus", "C"]
NAMES = {"A": "A  LLM only", "B": "B  Python", "Bplus": "B+ Python + schema", "C": "C  SPARQL + ontology"}
COLOR = {"A": "#2a78d6", "B": "#eb6834", "Bplus": "#1baf7a", "C": "#eda100"}  # validated categorical slots 1-4
MARKER = {"A": "o", "B": "s", "Bplus": "^", "C": "D"}  # secondary encoding: identity is never color alone
SIZE = {"A": 11, "B": 9, "Bplus": 7.5, "C": 6}  # decreasing, so markers that coincide stay visible as rings
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
LEVELS = {"L1": "L1 lookup", "L2": "L2 multi-hop", "L3": "L3 aggregation", "L4": "L4 failure / constraint",
          "L5": "L5 out-of-schema"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
})


def f1_vs_size(df):
    sizes = sorted(df["size"].unique())
    fig, axes = plt.subplots(1, len(LEVELS), figsize=(15, 3.8), sharey=True)
    for ax, (lvl, title) in zip(axes, LEVELS.items()):
        sub = df[df["level"] == lvl]
        means = sub.pivot_table(index="size", columns="condition", values="f1")
        for c in CONDS:
            ax.plot([NODES[s] for s in sizes], means.loc[sizes, c], color=COLOR[c], marker=MARKER[c],
                    lw=2, ms=SIZE[c], mec=SURFACE, mew=1.2, label=NAMES[c], zorder=3)
        n = sub[sub["condition"] == "A"].groupby("size").size()
        ax.set_title(f"{title}\nn = {'/'.join(str(n[s]) for s in sizes)} questions", fontsize=10, color=INK)
        ax.set_xscale("log")
        ax.set_xticks([NODES[s] for s in sizes], [str(NODES[s]) for s in sizes])
        ax.minorticks_off()
        ax.set_ylim(-0.03, 1.05)
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_xlabel("graph size (nodes)")
    axes[0].set_ylabel("mean F1")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 1.13))
    fig.suptitle("TEST: mean F1 vs graph size, by question level", y=1.2, fontsize=12)
    fig.savefig(RESULTS / "f1_vs_size.png", dpi=160, bbox_inches="tight")


def ci_differences(df):
    core = df[df["level"].isin(THESIS_LEVELS)]
    groups = [("L2-L4 pooled (pre-registered)", core)] + \
             [(f"L2-L4, {NODES[s]} nodes (exploratory)", core[core["size"] == s]) for s in sorted(core["size"].unique())]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    y, ticks = 0, []
    for label, sub in groups:
        for other in ("A", "B", "Bplus"):
            r = paired_bootstrap(sub, "C", other)
            ax.errorbar(r["diff"], y, xerr=[[r["diff"] - r["lo"]], [r["hi"] - r["diff"]]], fmt=MARKER[other],
                        color=COLOR[other], ms=7, mec=SURFACE, lw=2, capsize=0, zorder=3)
            ax.text(r["hi"] + 0.015, y, f"{r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]",
                    va="center", fontsize=8, color=INK2)
            ticks.append((y, f"C - {other.replace('plus', '+')}"))
            y -= 1
        ax.text(-0.62, y + 3.55, label, fontsize=9, color=INK, weight="bold" if "pre-reg" in label else "normal")
        y -= 0.9
    ax.axvline(0, color=INK2, lw=1, zorder=1)
    ax.set_yticks([t[0] for t in ticks], [t[1] for t in ticks], fontsize=9)
    ax.set_xlim(-0.62, 1.05)
    ax.set_ylim(y + 0.5, 1.2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("paired difference in mean F1 (C minus other), 95% bootstrap CI")
    ax.set_title("TEST: does the ontology condition beat the others?", fontsize=12, loc="left")
    fig.savefig(RESULTS / "ci_differences.png", dpi=160, bbox_inches="tight")


if __name__ == "__main__":
    scores = pd.read_csv(RESULTS / "scores_test.csv")
    f1_vs_size(scores)
    ci_differences(scores)
    print("wrote", RESULTS / "f1_vs_size.png", "and", RESULTS / "ci_differences.png")
