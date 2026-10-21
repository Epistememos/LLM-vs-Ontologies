"""analyze3.py - the pre-registered Experiment 3 TEST analysis (reads data/hidden/; run after the harness).

Written after the freeze and before any TEST result existed. It implements PREREG_EXP3.md and changes no frozen file:
- H1 primary: C3 - B3 on TEST cross-source questions, per-question F1 averaged over the 3 repeats, cluster bootstrap
  by (question text x graph seed), 10,000 resamples, seed 0, 95% percentile CI; decision on the cluster CI.
- H1 secondary: per-question paired bootstrap; disagreement rule.
- Descriptive: A3 contrast (two smaller graphs), per-seed results, controls, per-trap error split, C3 SPARQL validity,
  answer variation across repeats, retries, timeouts, median latency, cost.
Run (from the repo root): python exp3/analyze3.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "exp1"), str(HERE.parent / "exp2"), str(HERE)]
import score3  # noqa: E402
from pilot3 import canon_answer, trap_answers  # noqa: E402
from score import paired_bootstrap  # noqa: E402
from score2 import cluster_bootstrap  # noqa: E402

CONDS, REPEATS = ("A3", "B3", "C3"), (1, 2, 3)


def load(split="test"):
    ctx = score3.load_context()
    qs = {q["qid"]: q for q in json.loads((HERE / "data" / "questions.json").read_text())}
    rows = []
    for c in CONDS:
        for k in REPEATS:
            path = HERE / "results" / f"{c}_r{k}_{split}.jsonl"
            for rec in map(json.loads, path.read_text().splitlines()):
                q = qs[rec["qid"]]
                s = score3.score_final(rec.get("final"), q, ctx)
                pred = (rec.get("final") or {}).get("answer")
                rows.append(dict(condition=c, repeat=k, qid=q["qid"], size=q["size"], scope=q["scope"], kind=q["kind"],
                                 text=q["text"], f1=s["f1"], parsed=s["parsed"], halluc=s["n_halluc"],
                                 retries=rec["retries"], timeouts=rec.get("timeouts", 0), latency=rec["latency_s"],
                                 cost=rec["cost_usd"], spent=0 if rec["cached"] else rec["cost_usd"],
                                 valid=(rec["attempts"][-1].get("failure") is None) if c == "C3" else None,
                                 first_valid=(rec["attempts"][0].get("failure") is None) if c == "C3" else None,
                                 pred=json.dumps(canon_answer(pred, q, ctx["canon"][q["size"]]) if pred is not None else None)))
    return pd.DataFrame(rows), qs, ctx


def ci_row(label, df, a, b):
    c, p = cluster_bootstrap(df, a, b), paired_bootstrap(df, a, b)
    decide = lambda r: "supported" if r["lo"] > 0 else "contradicted" if r["hi"] < 0 else "not supported (CI includes 0)"
    return {"comparison": label, "mean diff": round(c["diff"], 3), "cluster 95% CI": f"[{c['lo']:+.3f}, {c['hi']:+.3f}]",
            "per-question 95% CI": f"[{p['lo']:+.3f}, {p['hi']:+.3f}]", "n / clusters": f"{c['n']} / {c['clusters']}",
            "cluster reading": decide(c), "per-question reading": decide(p)}


def main():
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", None)
    rows, qs, ctx = load()
    per_q = rows.groupby(["condition", "qid", "size", "scope", "kind", "text"], as_index=False).f1.mean()
    per_q["text"] = per_q["text"] + " @" + per_q["size"].astype(str)   # cluster = question text x graph seed
    cross, ctrl = per_q[per_q.scope == "cross"], per_q[per_q.scope == "control"]

    print("=== H1 (pre-registered): C3 - B3 on TEST cross-source questions, F1 averaged over 3 repeats ===")
    h1 = pd.DataFrame([ci_row("C3 - B3 (H1)", cross, "C3", "B3")]).set_index("comparison")
    print(h1.to_string())
    r = h1.iloc[0]
    print("decision (cluster CI):", r["cluster reading"],
          "| disagreement rule:", "the two CIs disagree; the decision follows the cluster CI and the result is sensitive to "
          "the correlation assumption" if r["cluster reading"] != r["per-question reading"] else "both CIs agree")

    print("\n=== A3 contrast (descriptive, 22- and 120-node graphs, cross-source) ===")
    small = cross[cross["size"].isin((20, 100))]
    print(pd.DataFrame([ci_row("B3 - A3", small, "B3", "A3"), ci_row("C3 - A3", small, "C3", "A3")]).set_index("comparison").to_string())

    print("\n=== Mean F1 per graph (descriptive; repeats averaged) ===")
    t = per_q.pivot_table(index=["scope", "size"], columns="condition", values="f1", aggfunc="mean").round(3)
    t["questions"] = per_q[per_q.condition == "B3"].groupby(["scope", "size"]).size()
    print(t.to_string())
    print("all cross-source:", cross.groupby("condition").f1.mean().round(3).to_dict(),
          "| all controls:", ctrl.groupby("condition").f1.mean().round(3).to_dict())

    traps = trap_answers(qs.values(), ctx)
    wrong = rows[(rows.scope == "cross") & (rows.f1 < 1)].copy()
    def classify(r):
        if r.pred == "null":
            return "no answer"
        gold = json.dumps(canon_answer(ctx["answers"][r.qid]["answer"], qs[r.qid], ctx["canon"][r["size"]]))
        hits = [v for v, a in traps[r.qid].items() if json.dumps(a) == r.pred and json.dumps(a) != gold]
        return ", ".join(hits) or "other"
    wrong["matches"] = wrong.apply(classify, axis=1) if len(wrong) else []
    print("\n=== Wrong cross-source answers by the wrong reading they match (all repeats; exploratory) ===")
    print(pd.crosstab(wrong.condition, wrong.matches, margins=True).to_string() if len(wrong) else "none")

    print("\n=== Answer variation across the 3 repeats ===")
    var = rows.groupby(["condition", "qid"]).agg(distinct=("pred", "nunique"), f1_range=("f1", lambda x: x.max() - x.min()))
    print(var.groupby("condition").agg(questions=("distinct", "size"), varying=("distinct", lambda x: int((x > 1).sum())),
                                       mean_f1_range=("f1_range", "mean")).round(3).to_string())

    c3 = rows[rows.condition == "C3"]
    print(f"\nC3 SPARQL validity: {c3.valid.astype(bool).mean():.1%} final, {c3.first_valid.astype(bool).mean():.1%} first try "
          f"({len(c3)} queries)")
    agg = rows.groupby("condition").agg(records=("qid", "size"), parsed=("parsed", "mean"), hallucinated_ids=("halluc", "sum"),
                                        retried=("retries", lambda x: int((x > 0).sum())), timeouts=("timeouts", "sum"),
                                        median_latency_s=("latency", "median"), cost_attributed=("cost", "sum"),
                                        spent=("spent", "sum"))
    print("\n=== Reliability and cost (all repeats) ===\n", agg.round(3).to_string())
    print(f"TEST spend: ${rows.spent.sum():.2f}")
    return rows, per_q


if __name__ == "__main__":
    main()
