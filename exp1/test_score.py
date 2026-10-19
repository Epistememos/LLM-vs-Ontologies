"""test_score.py - hand-made right/wrong answers for the scorer. Run: python test_score.py"""
import pandas as pd

from score import paired_bootstrap, parse_answer, score_one

VALID = {"svc-001", "svc-002", "svc-003", "db-001", "team-01", "sla-01"}


def check(name, got, **expected):
    for k, v in expected.items():
        assert abs(got[k] - v) < 1e-9, f"{name}: {k}={got[k]} expected {v}"
    print(f"ok  {name}")


def s(answer, atype, gold, declared=None):
    final = None if answer is ... else {"answer_type": declared or atype, "answer": answer}
    return score_one(final, atype, gold, VALID)


# sets
check("exact set", s(["svc-001", "db-001"], "set", ["db-001", "svc-001"]), precision=1, recall=1, f1=1)
check("half recall", s(["svc-001"], "set", ["svc-001", "db-001"]), precision=1, recall=0.5, f1=2 / 3)
check("extra item", s(["svc-001", "svc-002"], "set", ["svc-001"]), precision=0.5, recall=1, f1=2 / 3)
check("disjoint", s(["svc-002"], "set", ["svc-001"]), f1=0)
check("both empty", s([], "set", []), f1=1)
check("empty pred, gold non-empty", s([], "set", ["svc-001"]), f1=0, recall=0)
check("non-empty pred, gold empty", s(["svc-001"], "set", []), f1=0, precision=0)
check("IRI / prefix / case normalized",
      s(["http://example.org/br#svc-001", "ex:DB-001", " <svc-003> "], "set", ["svc-001", "db-001", "svc-003"]), f1=1)
check("duplicates collapse", s(["svc-001", "svc-001"], "set", ["svc-001"]), f1=1)
check("bare string wrapped", s("team-01", "set", ["team-01"]), f1=1)
check("hallucinated ids counted", s(["svc-001", "svc-999", "db-777"], "set", ["svc-001"]),
      n_returned=3, n_halluc=2, precision=1 / 3)
check("edges normalized", s(["ex:svc-001 -> SVC-003"], "set", ["svc-001->svc-003"]), f1=1, n_halluc=0)
check("edge with fake endpoint", s(["svc-001->svc-404"], "set", ["svc-001->svc-003"]), f1=0, n_halluc=1)

# scalars
check("number exact", s(3, "number", 3), f1=1)
check("number as string", s("3", "number", 3), f1=1)
check("number float equal", s(3.0, "number", 3), f1=1)
check("number wrong", s(4, "number", 3), f1=0)
check("number in 1-list", s([3], "number", 3), f1=1)
check("bool True as number rejected", s(True, "number", 1), f1=0)
check("bool exact", s(True, "bool", True), f1=1)
check("bool string", s("false", "bool", False), f1=1)
check("bool wrong", s(False, "bool", True), f1=0)
check("bool garbage", s("maybe", "bool", True), f1=0)

# parse failures and type declaration
check("no answer", s(..., "set", ["svc-001"]), f1=0, parsed=0)
check("declared wrong type still scored by question type", s(["svc-001"], "set", ["svc-001"], "number"),
      f1=1, type_ok=0)

# parse_answer
assert parse_answer('text {"answer_type": "set", "answer": ["a"]} more') == {"answer_type": "set", "answer": ["a"]}
assert parse_answer('{"answer": 1} then {"answer": 2}') == {"answer": 2}, "takes the last answer object"
assert parse_answer('```json\n{"answer_type": "bool", "answer": true}\n```')["answer"] is True
assert parse_answer('{"foo": 1} no answer here') is None
assert parse_answer("broken {answer: [1,}") is None
print("ok  parse_answer")

# paired bootstrap: constant difference -> CI collapses on it; identical -> zero
df = pd.DataFrame([dict(qid=f"q{i}", condition=c, f1=f) for i in range(20)
                   for c, f in (("C", 1.0), ("A", 0.5), ("B", 1.0))])
r = paired_bootstrap(df, "C", "A")
assert r["diff"] == 0.5 and r["lo"] == 0.5 and r["hi"] == 0.5 and r["n"] == 20
r = paired_bootstrap(df, "C", "B")
assert r["diff"] == 0 and r["lo"] == 0 and r["hi"] == 0
print("ok  paired_bootstrap")
print("\nall scorer tests passed")
