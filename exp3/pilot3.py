"""pilot3.py - DEV pilot report for Experiment 3 (reads data/hidden/; run after the harness, never inside it).

Mean F1 per condition per scale, the pre-registered ceiling check (no condition above 0.90 mean F1 on DEV
cross-source questions), the per-trap split of wrong cross-source answers, C3 SPARQL validity, retries, timeouts,
median latency and cost.
Run (from the repo root): python exp3/pilot3.py [repeat]
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "exp1"), str(HERE)]
import questions3  # noqa: E402
import score3  # noqa: E402
import truth3  # noqa: E402

CONDS = ("A3", "B3", "C3")
CEILING = 0.90


def canon_answer(value, q, canon):
    if q["answer_type"] != "set":
        return value
    items = value if isinstance(value, list) else [value]
    return sorted({canon.get(str(x).strip().lower(), str(x).strip().lower()) for x in items if x is not None})


def trap_answers(qs, ctx):
    """For each cross-source question: the answer each wrong reading would give (canonical, lower-case)."""
    out = {}
    for n in (20, 100, 500):
        _, key, _, _ = truth3.load(n)
        variants = {v: truth3.truth_for(n, truth3.rebuild(n, v)[0]) for v in questions3.VARIANTS}
        for q in (q for q in qs if q["size"] == n and q["scope"] == "cross"):
            a = ctx["answers"][q["qid"]]
            out[q["qid"]] = {v: canon_answer(questions3.answers(t, key, q["kind"], a["region"], a["entity"]), q,
                                             ctx["canon"][n]) for v, t in variants.items()}
    return out


def main(repeat=1, split="dev"):
    ctx = score3.load_context()
    qs = {q["qid"]: q for q in json.loads((HERE / "data" / "questions.json").read_text())}
    rows = []
    for c in CONDS:
        path = HERE / "results" / f"{c}_r{repeat}_{split}.jsonl"
        for rec in map(json.loads, path.read_text().splitlines()):
            q = qs[rec["qid"]]
            s = score3.score_final(rec.get("final"), q, ctx)
            last = rec["attempts"][-1]
            rows.append(dict(condition=c, qid=q["qid"], size=q["size"], scope=q["scope"], kind=q["kind"], f1=s["f1"],
                             parsed=s["parsed"], halluc=s["n_halluc"], retries=rec["retries"], timeouts=rec.get("timeouts", 0),
                             latency=rec["latency_s"], cost=rec["cost_usd"], spent=0 if rec["cached"] else rec["cost_usd"],
                             valid=(last.get("failure") is None) if c == "C3" else None,
                             first_valid=(rec["attempts"][0].get("failure") is None) if c == "C3" else None,
                             pred=(rec.get("final") or {}).get("answer")))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print("Mean F1 by condition and graph (DEV)")
    t = df.pivot_table(index=["scope", "size"], columns="condition", values="f1", aggfunc="mean")
    print(t.round(3).to_string(), "\n")
    cross = df[df.scope == "cross"]
    means = cross.groupby("condition").f1.mean()
    print("Ceiling check (pre-registered): mean F1 on DEV cross-source questions, limit 0.90")
    for c in CONDS:
        n = (cross.condition == c).sum()
        print(f"  {c}: {means.get(c, float('nan')):.3f} over {n} questions -> {'ABOVE CEILING' if means.get(c, 0) > CEILING else 'ok'}")
    print("  =>", "raise the difficulty knobs (round 1 of at most 2)" if (means > CEILING).any() else "no condition above the ceiling")

    traps = trap_answers(qs.values(), ctx)
    wrong = cross[cross.f1 < 1].copy()
    def classify(r):
        pred = canon_answer(r.pred, qs[r.qid], ctx["canon"][r["size"]]) if r.pred is not None else None
        hits = [v for v, a in traps[r.qid].items() if pred is not None and a == pred and a != canon_answer(
            ctx["answers"][r.qid]["answer"], qs[r.qid], ctx["canon"][r["size"]])]
        return ", ".join(hits) if hits else ("no answer" if pred is None else "other")
    wrong["matches"] = wrong.apply(classify, axis=1)
    print("\nWrong cross-source answers by the wrong reading they match (exploratory)")
    print(pd.crosstab(wrong.condition, wrong.matches, margins=True).to_string() if len(wrong) else "  none")

    agg = df.groupby("condition").agg(questions=("qid", "size"), parsed=("parsed", "mean"), hallucinated_ids=("halluc", "sum"),
                                      retried=("retries", lambda x: int((x > 0).sum())), timeouts=("timeouts", "sum"),
                                      median_latency_s=("latency", "median"), cost_attributed=("cost", "sum"),
                                      spent=("spent", "sum"))
    print("\nReliability and cost\n", agg.round(3).to_string())
    c3 = df[df.condition == "C3"]
    print(f"\nC3 SPARQL validity: {c3.valid.astype(bool).mean():.0%} (first try {c3.first_valid.astype(bool).mean():.0%})")
    print(f"Total spent: ${df.spent.sum():.3f}")
    return df, wrong


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
