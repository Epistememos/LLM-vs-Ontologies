"""summary_figure.py - one figure with every experiment's pre-registered comparison and its 95% CI.

Recomputes each difference from the committed TEST scores with the experiment's own bootstrap (no API calls), checks
it against the published value, and writes notebook/summary_ci.png.
Run (from the repo root): python tools/summary_figure.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "exp1"), str(ROOT / "exp2"), str(ROOT / "exp3")]
import analyze3  # noqa: E402  (Experiment 3 scoring reads the answer key in data/hidden/, offline only)
from score import THESIS_LEVELS, paired_bootstrap  # noqa: E402
from score2 import cluster_bootstrap  # noqa: E402

OUT = ROOT / "notebook" / "summary_ci.png"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
PRIMARY, OTHER = "#2a78d6", "#a19f97"


def comparisons():
    s1 = pd.read_csv(ROOT / "exp1" / "results" / "scores_test.csv")
    core1 = s1[s1.level.isin(THESIS_LEVELS)]
    s2 = pd.read_csv(ROOT / "exp2" / "results" / "scores_test.csv")
    l4 = s2[s2.level == "L4"]
    rows3, _, _ = analyze3.load()
    per_q = rows3.groupby(["condition", "qid", "size", "scope", "text"], as_index=False).f1.mean()
    per_q["text"] = per_q["text"] + " @" + per_q["size"].astype(str)
    cross = per_q[per_q.scope == "cross"]
    small = cross[cross["size"].isin((20, 100))]
    return [  # (label, result, pre-registered primary?, published value)
        ("Exp 1: C − B+  (ontology vs documented code)", paired_bootstrap(core1, "C", "Bplus"), True, (-0.005, -0.055, 0.055)),
        ("Exp 1: C − A  (ontology vs LLM alone)", paired_bootstrap(core1, "C", "A"), False, (0.163, 0.083, 0.250)),
        ("Exp 2: C2 − B+  (rule ontology vs prose)", cluster_bootstrap(l4, "C2", "Bplus"), True, (0.026, 0.000, 0.071)),
        ("Exp 2: C2 − B++  (rule ontology vs Python helpers)", cluster_bootstrap(l4, "C2", "Bplusplus"), False, (0.000, 0.000, 0.000)),
        ("Exp 3: C3 − B3  (resolving ontology vs resolving Python)", cluster_bootstrap(cross, "C3", "B3"), True, (0.000, 0.000, 0.000)),
        ("Exp 3: C3 − A3  (resolving ontology vs LLM alone)", cluster_bootstrap(small, "C3", "A3"), False, (0.532, 0.377, 0.687)),
        ("Exp 3: B3 − A3  (resolving Python vs LLM alone)", cluster_bootstrap(small, "B3", "A3"), False, (0.532, 0.377, 0.687)),
    ]


def main():
    rows = comparisons()
    for label, r, _, pub in rows:
        got = tuple(round(float(r[k]), 3) for k in ("diff", "lo", "hi"))
        assert got == pub, f"{label}: computed {got}, published {pub}"
        print(f"{label:60} {got[0]:+.3f} [{got[1]:+.3f}, {got[2]:+.3f}]  matches the write-up")

    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.edgecolor": GRID, "xtick.color": INK2, "ytick.color": INK, "text.color": INK,
                         "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(11, 4.8))
    for y, (label, r, primary, _) in enumerate(reversed(rows)):
        color = PRIMARY if primary else OTHER
        ax.plot([r["lo"], r["hi"]], [y, y], color=color, lw=2, solid_capstyle="round")
        ax.plot(r["diff"], y, "o", ms=8, color=color, mec=SURFACE, mew=2)
        ax.text(max(r["hi"], r["diff"]) + 0.02, y, f"{r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]",
                va="center", fontsize=8.5, color=INK2)
    labels = [label for label, *_ in reversed(rows)]
    ax.set_yticks(range(len(rows)), labels, fontsize=9)
    for tick, (_, _, primary, _) in zip(ax.get_yticklabels(), reversed(rows)):
        tick.set_fontweight("bold" if primary else "normal")
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlim(-0.15, 1.15)
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    ax.set_xlabel("difference in mean F1 (TEST), with 95% bootstrap CI")
    ax.plot([], [], "o-", color=PRIMARY, label="pre-registered primary test")
    ax.plot([], [], "o-", color=OTHER, label="secondary or descriptive comparison")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.suptitle("Primary tests: no detectable advantage for the ontology in any experiment.  Grounded vs the LLM alone: large gains.",
                 x=0.01, ha="left", fontsize=10.5)
    plt.tight_layout()
    fig.savefig(OUT, dpi=130)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
