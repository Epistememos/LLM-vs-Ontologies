"""score.py - parse model answers, score them against data/answers.json, aggregate.

Every harness writes results/{condition}_{split}.jsonl with one record per question:
  {condition, qid, final: {"answer_type": ..., "answer": ...} | null, tokens_in, tokens_out,
   latency_s, retries, ...condition-specific fields}
Run: python score.py [split]   (default split: dev)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA, RESULTS = ROOT / "data", ROOT / "results"
PREFIXES = ("http://example.org/br#", "ex:")
THESIS_LEVELS = ("L2", "L3", "L4")  # pre-registered: L1 is lookup, L5 is out-of-schema


def parse_answer(text):
    """Return the last JSON object in `text` that has an 'answer' key, or None."""
    dec, found = json.JSONDecoder(), None
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text, i)
            except ValueError:
                continue
            if isinstance(obj, dict) and "answer" in obj:
                found = obj
    return found


def norm_id(x):
    s = str(x).strip().strip("<>").strip().lower()
    for p in PREFIXES:
        s = s.removeprefix(p)
    if "->" in s:
        return "->".join(norm_id(part) for part in s.split("->"))
    return s


def coerce(value, atype):
    """Map a raw answer value to the question's type; None if impossible."""
    if atype == "set":
        if value is None:
            return None
        items = value if isinstance(value, list) else [value]
        return {norm_id(v) for v in items}
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if atype == "bool":
        if isinstance(value, bool):
            return value
        return {"true": True, "yes": True, "false": False, "no": False}.get(str(value).strip().lower())
    if atype == "number":
        if isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    raise ValueError(atype)


def score_one(final, atype, gold, valid_ids):
    """Precision/recall/F1 for sets (exact match for scalars) plus hallucination counts."""
    out = dict(parsed=final is not None, type_ok=False, precision=0.0, recall=0.0, f1=0.0,
               n_returned=0, n_halluc=0)
    if final is None:
        return out
    out["type_ok"] = final.get("answer_type") == atype
    pred = coerce(final.get("answer"), atype)
    if pred is None:
        return out
    if atype != "set":
        hit = float(pred == (float(gold) if atype == "number" else gold))
        return out | dict(precision=hit, recall=hit, f1=hit)
    gold = {norm_id(g) for g in gold}
    ids = [p for item in pred for p in item.split("->")]
    out["n_returned"], out["n_halluc"] = len(ids), sum(p not in valid_ids for p in ids)
    if not pred and not gold:
        return out | dict(precision=1.0, recall=1.0, f1=1.0)
    tp = len(pred & gold)
    p = tp / len(pred) if pred else 1.0
    r = tp / len(gold) if gold else 1.0
    return out | dict(precision=p, recall=r, f1=2 * p * r / (p + r) if p + r else 0.0)


def valid_ids_by_size():
    return {n: {v["id"] for v in json.loads((DATA / f"graph_{n}.json").read_text())["nodes"]}
            for n in (20, 100, 500)}


def score_records(records):
    qs = {q["qid"]: q for q in json.loads((DATA / "questions.json").read_text())}
    answers = json.loads((DATA / "answers.json").read_text())
    valid = valid_ids_by_size()
    rows = []
    for rec in records:
        q = qs[rec["qid"]]
        s = score_one(rec.get("final"), q["answer_type"], answers[rec["qid"]], valid[q["size"]])
        meta = {k: v for k, v in rec.items() if k not in ("final", "attempts", "text")}
        rows.append(meta | {k: q[k] for k in ("size", "level", "kind", "answer_type", "split")} | s)
    return pd.DataFrame(rows)


def paired_bootstrap(df, cond_a, cond_b, n_boot=10_000, seed=0):
    """Mean F1(cond_a) - F1(cond_b) over shared questions, with a 95% percentile bootstrap CI."""
    wide = df.pivot_table(index="qid", columns="condition", values="f1").dropna(subset=[cond_a, cond_b])
    diff = (wide[cond_a] - wide[cond_b]).to_numpy()
    if len(diff) == 0:
        return dict(diff=np.nan, lo=np.nan, hi=np.nan, n=0)
    rng = np.random.default_rng(seed)
    boots = diff[rng.integers(0, len(diff), (n_boot, len(diff)))].mean(axis=1)
    return dict(diff=diff.mean(), lo=np.percentile(boots, 2.5), hi=np.percentile(boots, 97.5), n=len(diff))


def summarize(df):
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print("\nMean F1 by condition x level x size")
    print(df.pivot_table(index=["condition", "size"], columns="level", values="f1", aggfunc="mean").round(2))
    agg = df.groupby("condition").agg(
        f1=("f1", "mean"), parsed=("parsed", "mean"), type_ok=("type_ok", "mean"),
        returned=("n_returned", "sum"), halluc=("n_halluc", "sum"),
        tokens_in=("tokens_in", "mean"), tokens_out=("tokens_out", "mean"), latency_s=("latency_s", "mean"),
        retry_rate=("retries", lambda x: (x > 0).mean()),
        timeouts=("timeouts", "sum"))  # sandbox/query timeouts: machine-speed effects, reported separately
    agg["halluc_rate"] = agg["halluc"] / agg["returned"].clip(lower=1)
    print("\nPer condition\n", agg.round(3))
    c = df[df["condition"] == "C"]
    if len(c):
        valid = c["sparql_valid"].astype(bool)
        print(f"\nC: SPARQL validity {valid.mean():.0%} (first try {c['first_try_valid'].astype(bool).mean():.0%}), "
              f"retry rate {(c['retries'] > 0).mean():.0%}")
        kind = np.where(~valid, "invalid query", np.where(c["f1"] == 1, "correct", "valid but wrong"))
        print(pd.crosstab(c["level"], kind))
        print("invalid-query causes:", c.loc[~valid, "failure_type"].value_counts().to_dict())
    core = df[df["level"].isin(THESIS_LEVELS)]
    if "C" in set(df["condition"]):
        print(f"\nPaired bootstrap, levels {THESIS_LEVELS}:")
        for other in ("A", "B", "Bplus"):
            if other in set(df["condition"]):
                r = paired_bootstrap(core, "C", other)
                print(f"  C - {other}: {r['diff']:+.3f}  95% CI [{r['lo']:+.3f}, {r['hi']:+.3f}]  n={r['n']}")


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    records = [json.loads(line) for f in sorted(RESULTS.glob(f"*_{split}.jsonl"))
               for line in f.read_text().splitlines() if line.strip()]
    if not records:
        sys.exit(f"no results for split '{split}' in {RESULTS}")
    df = score_records(records)
    df["timeouts"] = df.get("timeouts", 0)
    df["timeouts"] = df["timeouts"].fillna(0).astype(int)
    df.to_csv(RESULTS / f"scores_{split}.csv", index=False)
    summarize(df)
