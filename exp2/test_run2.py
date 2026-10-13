"""test_run2.py - offline test of the exp2 harnesses (no API calls): a hand-written Python program
(B+ with the definitions inlined, B++ importing helpers.py) and a hand-written simple SPARQL query (C2) for
every question kind, run through the real execute paths and scored against the answer key.
Run (from the repo root): python exp2/test_run2.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import run2  # noqa: E402
from score import score_one  # noqa: E402

QS = json.loads((HERE / "data" / "questions.json").read_text())
ANS = json.loads((HERE / "data" / "answers.json").read_text())
VALID = {n: {v["id"] for v in json.loads((HERE / "data" / f"graph_{n}.json").read_text())["nodes"]} for n in (20, 100, 500)}
HELPERS_SRC = (HERE / "helpers.py").read_text()

PY = {  # expression over g = Infra("graph.json"); {0}, {1} are IDs taken from the question text
    "is_down": 'g.is_down("{0}")',
    "down_by_team": 'sorted(s for s in g.down_services(primary_only=True) if g.owner[s] == "{0}")',
    "is_lost": 'g.is_lost("{0}")',
    "sla_breached": '"{0}" in g.breached_slas()',
    "is_tier_risk": '"{0}" in g.tier_risk_services()',
    "violates_edge": '("{0}", "{1}") in g.tier_violations()',
    "breached_slas": "g.breached_slas()",
    "count_down": "len(g.down_services(primary_only=True))",
    "survivors": '[x for x in g.primaries("CustomerFacingService") if g.region[x] == g.failed_region and not g.is_down(x)]',
    "down_cfs": '[x for x in g.primaries("CustomerFacingService") if g.is_down(x)]',
    "lost_dbs": '[d for d in g.primaries("Database") if g.is_lost(d)]',
    "violations": '[f"{{a}}->{{b}}" for a, b in g.tier_violations()]',
    "tier_risks": "g.tier_risk_services()",
    "failed_region": "[g.failed_region]",
}
SPARQL = {
    "is_down": "ASK {{ ex:{0} a ex:Down }}",
    "down_by_team": "SELECT ?s WHERE {{ ?s a ex:Down , ex:Primary ; ex:ownedBy ex:{0} }}",
    "is_lost": "ASK {{ ex:{0} a ex:Lost }}",
    "sla_breached": "ASK {{ ex:{0} a ex:BreachedSLA }}",
    "is_tier_risk": "ASK {{ ex:{0} a ex:TierRiskService }}",
    "violates_edge": "ASK {{ ex:{0} ex:violatesTierRule ex:{1} }}",
    "breached_slas": "SELECT ?l WHERE {{ ?l a ex:BreachedSLA }}",
    "count_down": "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {{ ?s a ex:Down , ex:Primary }}",
    "survivors": "SELECT ?x WHERE {{ ?x a ex:CustomerFacingService , ex:Primary ; ex:deployedIn ?r . ?r a ex:FailedRegion . "
                 "FILTER NOT EXISTS {{ ?x a ex:Down }} }}",
    "down_cfs": "SELECT ?x WHERE {{ ?x a ex:CustomerFacingService , ex:Primary , ex:Down }}",
    "lost_dbs": "SELECT ?d WHERE {{ ?d a ex:Database , ex:Primary , ex:Lost }}",
    "violations": "SELECT ?a ?b WHERE {{ ?a ex:violatesTierRule ?b }}",
    "tier_risks": "SELECT ?s WHERE {{ ?s a ex:TierRiskService }}",
    "failed_region": "SELECT ?r WHERE {{ ?r a ex:FailedRegion }}",
}
ID = re.compile(r"\b(?:svc|db|sla|team|q)-\d+\b")


def program(q, inline_helpers):
    expr = PY[q["kind"]].format(*ID.findall(q["text"]))
    head = HELPERS_SRC if inline_helpers else "from helpers import Infra\n"
    return (f"```python\n{head}\nimport json\ng = Infra('graph.json')\nans = {expr}\n"
            f"print(json.dumps({{'answer_type': '{q['answer_type']}', 'answer': ans}}))\n```")


def score(final, q):
    return score_one(final, q["answer_type"], ANS[q["qid"]], VALID[q["size"]])["f1"] if final else 0.0


def main():
    ok, per_kind = True, {}
    for q in QS:
        f_bp, e_bp, _ = run2.EXECUTE["Bplus"](program(q, inline_helpers=True), q)
        f_bpp, e_bpp, _ = run2.EXECUTE["Bplusplus"](program(q, inline_helpers=False), q)
        reply = f"```sparql\n{SPARQL[q['kind']].format(*ID.findall(q['text']))}\n```\n" \
                f'{{"answer_type": "{q["answer_type"]}"}}'
        f_c2, e_c2, _ = run2.EXECUTE["C2"](reply, q)
        s = [score(f_bp, q), score(f_bpp, q), score(f_c2, q)]
        k = per_kind.setdefault(q["kind"], [0, 0, 0, 0])
        k[0] += 1
        for i, v in enumerate(s):
            k[i + 1] += v == 1.0
        if s != [1.0, 1.0, 1.0]:
            ok = False
            print(f"  FAIL {q['qid']} {q['kind']}: {s} errors={[e_bp, e_bpp, e_c2]}")
    print(f"{'kind':15} {'n':>3} {'B+':>4} {'B++':>4} {'C2':>4}")
    for kind, (n, a, b, c) in per_kind.items():
        print(f"{kind:15} {n:>3} {a:>4} {b:>4} {c:>4}")
    print("\nall harness paths reproduce the answer key" if ok else "\nFAILURES")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
