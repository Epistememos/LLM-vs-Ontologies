"""test_run3.py - offline tests for Experiment 3 (no API calls).

1. Docs: the resolution-rule and stale-record text appears word for word in every condition's prompt, and equals
   truth3.RULES; the definitions appear in every prompt.
2. Hidden-data guard: (a) static: no harness, prompt builder, artifact or sandbox file list mentions data/hidden/;
   (b) runtime, in a fresh process: after importing run3, opening or listing data/hidden/ raises PermissionError;
   (c) runtime, in the B3 sandbox: a program opening a hidden file by absolute path is refused.
3. Reproduction: a hand-written glue program (B3) and a hand-written simple SPARQL query (C3) for every one of the
   76 questions, run through the real execute paths and scored against the answer key: all must score F1 = 1.
Run (from the repo root): python exp3/test_run3.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "exp1"), str(HERE)]
import score3  # noqa: E402
import truth3  # noqa: E402

CTX = score3.load_context()               # read the hidden key BEFORE the guarded harness is imported
RULES = truth3.RULES
HIDDEN_FILE = HERE / "data" / "hidden" / "answers.json"
QS = json.loads((HERE / "data" / "questions.json").read_text())

import run3  # noqa: E402  (installs the hidden-data guard in this process from here on)
from docs3 import DEFINITIONS  # noqa: E402

PY = {
    "is_down": 'g.is_down(g.resolve({name!r}), {dc!r})',
    "down_by_team": 'sorted(s for s in g.down_services({dc!r}, primary_only=True) if g.team[s] == {team!r})',
    "breached_slas": "g.breached_slas({dc!r})",
    "sla_breached": "{sla!r} in g.breached_slas({dc!r})",
    "count_down": "len(g.down_services({dc!r}, primary_only=True))",
    "cmdb_deps": 'sorted(d for d in g.transitive_dependencies({ci!r}) if g.cls[d] in ("service", "customer_facing_service"))',
    "mon_owner": "[g.team[g.resolve({name!r})]]",
}
SPARQL = {
    "is_down": 'ASK {{ ?x ex:name "{name}" ; ex:downIn ex:{dc} }}',
    "down_by_team": "SELECT ?s WHERE {{ ?s ex:downIn ex:{dc} ; a ex:Primary ; ex:ownedBy ex:{team} }}",
    "breached_slas": "SELECT ?l WHERE {{ ?l ex:breachedIn ex:{dc} }}",
    "sla_breached": "ASK {{ ex:{sla} ex:breachedIn ex:{dc} }}",
    "count_down": "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {{ ?s ex:downIn ex:{dc} ; a ex:Primary }}",
    "cmdb_deps": "SELECT DISTINCT ?d WHERE {{ ex:{ci} ex:dependsOnTransitively ?d . ?d a ex:Service }}",
    "mon_owner": 'SELECT ?t WHERE {{ ?x ex:name "{name}" ; ex:ownedBy ?t }}',
}


def params(text):
    find = lambda pat: (re.search(pat, text) or [None, None])[1]
    return {"dc": find(r"datacenter (dc-[a-z]+)"), "name": find(r'"([^"]+)"'), "team": find(r"by (team-[a-z]+)"),
            "sla": find(r"is (SLA-[A-Z]+-\d+) breached"), "ci": find(r"does (CI-\d+) transitively")}


def check_docs():
    prompts = {c: run3.system_prompt(c, 100) for c in ("A3", "B3", "C3")}
    from docs3 import RULES as DOC_RULES
    ok = DOC_RULES == RULES and all(RULES in p for p in prompts.values()) and all(DEFINITIONS in p for p in prompts.values())
    stale = 'a record whose status is "decommissioned" (CMDB) or "retired" (monitoring) is stale'
    ok &= all(stale in p for p in prompts.values())
    print(f"1. docs: rules == truth3.RULES and present word for word in A3/B3/C3 prompts, definitions present: "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def code_strings(path):
    """String values the file's code can use (not docstrings or comments); the guard's own source is excluded."""
    text = path.read_text(encoding="utf-8")
    if path.suffix != ".py":
        return [text]
    import ast
    tree = ast.parse(text)
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(n)}
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docs and n.value != run3.GUARD]


def check_guard():
    harness = [HERE / f for f in ("run3.py", "glue.py", "docs3.py", "rules3.py", "to_rdf3.py", "derive_tables.py",
                                  "ontology3.ttl")] + [HERE.parent / "exp1" / f for f in ("sandbox.py", "llm.py", "common.py",
                                                                                          "run_B.py", "run_C.py")]
    mentions = [p.name for p in harness if any("hidden" in s for s in code_strings(p))]
    files = [str(v) for n in (20, 100, 500) for v in list(run3.sandbox_files(n, "").values()) + list(run3.runner_files(n).values())]
    static_ok = not mentions and not any(re.search(r"[\\/]data[\\/]hidden", f) for f in files)
    probe = (f"import sys; sys.path[:0] = [{str(HERE)!r}]; import run3, os\n"
             f"for f in (lambda: open({str(HIDDEN_FILE)!r}), lambda: os.listdir({str(HIDDEN_FILE.parent)!r})):\n"
             "    try:\n        f(); print('OPENED')\n    except PermissionError:\n        print('REFUSED')\n")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True).stdout.split()
    process_ok = out == ["REFUSED", "REFUSED"]
    code = f"open({str(HIDDEN_FILE)!r}).read()\nprint('{{\"answer_type\": \"set\", \"answer\": []}}')"
    _, err, info = run3.execute_b3(f"```python\n{code}\n```", {"size": 20})
    sandbox_ok = err is not None and "PermissionError" in info.get("stderr", "")
    print(f"2. guard: static (no mention, no hidden file in any sandbox) {'PASS' if static_ok else 'FAIL ' + str(mentions)} | "
          f"harness process refuses open + listdir {'PASS' if process_ok else 'FAIL ' + str(out)} | "
          f"B3 sandbox refuses absolute-path open {'PASS' if sandbox_ok else 'FAIL'}")
    return static_ok and process_ok and sandbox_ok


def check_reproduction():
    ok, per_kind = True, {}
    for q in QS:
        p = params(q["text"])
        prog = (f"```python\nimport json\nfrom glue import Infra3\ng = Infra3('cmdb.json', 'monitoring.json', 'mapping_tables.json')\n"
                f"ans = {PY[q['kind']].format(**p)}\nprint(json.dumps({{'answer_type': '{q['answer_type']}', 'answer': ans}}))\n```")
        fb, eb, _ = run3.execute_b3(prog, q)
        fc, ec, _ = run3.execute_c3(f"```sparql\n{SPARQL[q['kind']].format(**p)}\n```\n" +
                                    json.dumps({"answer_type": q["answer_type"]}), q)
        s = [score3.score_final(f, q, CTX)["f1"] if f else 0.0 for f in (fb, fc)]
        k = per_kind.setdefault(q["kind"], [0, 0, 0])
        k[0] += 1
        k[1] += s[0] == 1.0
        k[2] += s[1] == 1.0
        if s != [1.0, 1.0]:
            ok = False
            print(f"   FAIL {q['qid']} {q['kind']}: B3 {s[0]} {eb or ''} | C3 {s[1]} {ec or ''}")
    print("3. reproduction on all questions (B3 glue program, C3 simple SPARQL):")
    for kind, (n, b, c) in per_kind.items():
        print(f"     {kind:14} n={n:2}  B3 {b:2}/{n}  C3 {c:2}/{n}")
    return ok


if __name__ == "__main__":
    results = [check_docs(), check_guard(), check_reproduction()]
    print("\nALL STEP-2 TESTS PASS" if all(results) else "\nFAILURES")
    sys.exit(0 if all(results) else 1)
