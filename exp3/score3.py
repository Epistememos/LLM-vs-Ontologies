"""score3.py - score Experiment 3 answers. Reads data/hidden/ (answer key and entity-resolution key), so it runs
only outside the harness, never inside a condition.

Any identifier of the right entity counts: services by CI ID, CMDB name, monitoring ID, display name or alias; teams by
monitoring team name or CMDB owner group; regions by datacenter or zone; SLAs by SLA ID. Unknown identifiers count as
hallucinations. Scalars use exp1's exact-match scoring.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "exp1"), str(HERE)]
from score import score_one  # noqa: E402

HIDDEN = HERE / "data" / "hidden"


def canonicalizer(n):
    """lower-cased identifier -> lower-cased canonical token (CI ID, monitoring team, SLA ID, datacenter)."""
    key = json.loads((HIDDEN / f"er_key_{n}.json").read_text())
    c = {}
    for e in key["entities"].values():
        for nm in [e["cmdb"], e["cmdb_name"], e["monitoring"], e["display"]] + e["aliases"]:
            c[nm.lower()] = e["cmdb"].lower()
    for t in key["teams"].values():
        c[t["cmdb"].lower()] = c[t["monitoring"].lower()] = t["monitoring"].lower()
    for r in key["regions"].values():
        c[r["cmdb"].lower()] = c[r["monitoring"].lower()] = r["cmdb"].lower()
    for s in key["slas"].values():
        c[s.lower()] = s.lower()
    return c


def load_context():
    """Everything the scorer needs from data/hidden/, read once (before any guarded harness is imported)."""
    answers = json.loads((HIDDEN / "answers.json").read_text())
    return {"answers": answers, "canon": {n: canonicalizer(n) for n in (20, 100, 500)}}


def score_final(final, q, ctx):
    gold = ctx["answers"][q["qid"]]["answer"]
    canon = ctx["canon"][q["size"]]
    valid = set(canon.values())
    if q["answer_type"] != "set" or final is None:
        return score_one(final, q["answer_type"], gold, valid)
    items = final.get("answer")
    items = items if isinstance(items, list) else [items]
    mapped = {"answer_type": final.get("answer_type"),
              "answer": [canon.get(str(x).strip().lower(), str(x).strip().lower()) for x in items if x is not None]}
    return score_one(mapped, "set", [canon[g.lower()] for g in gold], valid)
