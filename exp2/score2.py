"""score2.py - score Experiment 2 results and run its two bootstrap tests.

  cluster bootstrap (primary)    : resample distinct question texts (clusters) with replacement; every question
                                   in a drawn cluster enters; statistic = mean paired F1 difference over the
                                   drawn questions. Accounts for identical prompts across sizes/scenarios.
  per-question bootstrap (second): exp1's score.paired_bootstrap, questions resampled independently.
Both: 10,000 resamples, numpy seed 0, 95% percentile interval.
Run (from the repo root): python exp2/score2.py [dev|test]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from score import paired_bootstrap, score_one  # noqa: E402

DATA, RESULTS = HERE / "data", HERE / "results"
CONDS = ["Bplus", "Bplusplus", "C2"]


def score_records(records):
    qs = {q["qid"]: q for q in json.loads((DATA / "questions.json").read_text())}
    answers = json.loads((DATA / "answers.json").read_text())
    valid = {n: {v["id"] for v in json.loads((DATA / f"graph_{n}.json").read_text())["nodes"]} for n in (20, 100, 500)}
    rows = []
    for rec in records:
        q = qs[rec["qid"]]
        s = score_one(rec.get("final"), q["answer_type"], answers[rec["qid"]], valid[q["size"]])
        meta = {k: v for k, v in rec.items() if k not in ("final", "attempts", "text")}
        rows.append(meta | {k: q[k] for k in ("size", "level", "kind", "answer_type", "split", "scenario", "text")} | s)
    df = pd.DataFrame(rows)
    df["timeouts"] = df.get("timeouts", 0)
    return df


def cluster_bootstrap(df, cond_a, cond_b, n_boot=10_000, seed=0):
    """Mean F1(cond_a) - F1(cond_b) over shared questions; CI from resampling question-text clusters."""
    wide = df.pivot_table(index=["qid", "text"], columns="condition", values="f1").dropna(subset=[cond_a, cond_b])
    if wide.empty:
        return dict(diff=np.nan, lo=np.nan, hi=np.nan, n=0, clusters=0)
    d = (wide[cond_a] - wide[cond_b]).groupby(level="text").agg(["sum", "count"])
    sums, counts = d["sum"].to_numpy(), d["count"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), (n_boot, len(d)))
    boots = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return dict(diff=sums.sum() / counts.sum(), lo=np.percentile(boots, 2.5), hi=np.percentile(boots, 97.5),
                n=int(counts.sum()), clusters=len(d))


def summarize(df):
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    l4 = df[df["level"] == "L4"]
    print("Mean F1, L4, by size")
    t = l4.pivot_table(index="size", columns="condition", values="f1")
    t.loc["all"] = l4.groupby("condition").f1.mean()
    print(t.round(3))
    print("\nMean F1, L4, by kind")
    print(l4.pivot_table(index="kind", columns="condition", values="f1").round(2))
    chk = df[df["level"] == "check"]
    if len(chk):
        print("\nFailed-region checks (F1):", chk.pivot_table(index="qid", columns="condition", values="f1").to_dict("index"))
    agg = df.groupby("condition").agg(f1=("f1", "mean"), parsed=("parsed", "mean"), halluc=("n_halluc", "sum"),
                                      retry_rate=("retries", lambda x: (x > 0).mean()), timeouts=("timeouts", "sum"),
                                      tokens_in=("tokens_in", "mean"), tokens_out=("tokens_out", "mean"),
                                      latency_median_s=("latency_s", "median"), cost=("cost_usd", "sum"))
    print("\nPer condition (all levels)\n", agg.round(3))
    c2 = df[df["condition"] == "C2"]
    if len(c2):
        v = c2["sparql_valid"].astype(bool)
        print(f"\nC2: SPARQL validity {v.mean():.0%} (first try {c2['first_try_valid'].astype(bool).mean():.0%})")
    fmt = lambda r: f"{r['diff']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]"
    print("\nL4 paired differences, 95% CI")
    for other in ("Bplus", "Bplusplus"):
        if {"C2", other} <= set(l4["condition"]):
            c = cluster_bootstrap(l4, "C2", other)
            p = paired_bootstrap(l4, "C2", other)
            print(f"  C2 - {other:9}  cluster: {fmt(c)} (n={c['n']}, {c['clusters']} clusters)   per-question: {fmt(p)}")


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    records = [json.loads(line) for c in CONDS if (RESULTS / f"{c}_{split}.jsonl").exists()
               for line in (RESULTS / f"{c}_{split}.jsonl").read_text().splitlines() if line.strip()]
    if not records:
        sys.exit(f"no results for split '{split}'")
    df = score_records(records)
    df.to_csv(RESULTS / f"scores_{split}.csv", index=False)
    summarize(df)
