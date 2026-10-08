"""test_harness.py - offline tests for the B/B+ and C harnesses. No API calls.

1. Hand-written Python (as B would write) and SPARQL (as C would write) for each question kind,
   run through the real sandbox and harness mapping, scored against the answer key.
   For C this also checks that the RDF + schema can express the ground-truth semantics.
2. Sandbox guards: exception, timeout, network, subprocess, env scrubbing, file visibility.
3. The retry loop with a stubbed LLM: retry on error, never on a valid empty result.
Run: python test_harness.py
"""
import json
import os
import re

import common
import run_B
import run_C
import sandbox
from score import score_one, valid_ids_by_size

QS = json.loads((common.DATA / "questions.json").read_text())
ANS = json.loads((common.DATA / "answers.json").read_text())
VALID = valid_ids_by_size()
EMIT = 'print(json.dumps({{"answer_type": "{t}", "answer": ans}}))'

B_PRELUDE = """import json, networkx as nx
g = json.load(open("graph.json"))
node = {v["id"]: v for v in g["nodes"]}
D = nx.DiGraph([(s, o) for s, r, o in g["edges"] if r == "dependsOn"])
"""
LOST = """R = nx.Graph([(s, o) for s, r, o in g["edges"] if r == "replicaOf"])
region = {s: o for s, r, o in g["edges"] if r == "deployedIn"}
grp = lambda x: nx.node_connected_component(R, x) if x in R else {x}
lost = lambda x: {region[m] for m in grp(x)} <= {RG}
svcs = [k for k, v in node.items() if v["type"] in ("Service", "CustomerFacingService")]
down = sorted(s for s in svcs if lost(s) or any(lost(d) for d in (nx.descendants(D, s) if s in D else ())))
""".replace("{", "{{").replace("}", "}}").replace("{{RG}}", '{{"{0}"}}')  # escaped for str.format
PRIMARY_DOWN = 'reps = {{s for s, r, o in g["edges"] if r == "replicaOf"}}\npdown = [s for s in down if s not in reps]\n'
NOT_REPLICA = " FILTER NOT EXISTS {{ ?s ex:replicaOf ?p }}"
DOWN_Q = """?s rdf:type/rdfs:subClassOf* ex:Service ; ex:dependsOn* ?n .
  FILTER NOT EXISTS {{ ?n (ex:replicaOf|^ex:replicaOf)* ?m . ?m ex:deployedIn ?r . FILTER(?r != ex:{0}) }}"""

# kind -> (regex extracting IDs from the question text, Python body, SPARQL)
CASES = {
    "owner": (r"owns (\S+)\?", 'ans = [o for s, r, o in g["edges"] if s == "{0}" and r == "ownedBy"]',
              "SELECT ?t WHERE {{ ex:{0} ex:ownedBy ?t }}"),
    "region": (r"is (\S+) deployed", 'ans = [o for s, r, o in g["edges"] if s == "{0}" and r == "deployedIn"]',
               "SELECT ?r WHERE {{ ex:{0} ex:deployedIn ?r }}"),
    "tier": (r"tier of (\S+)\?", 'ans = node["{0}"]["tier"]', "SELECT ?t WHERE {{ ex:{0} ex:tier ?t }}"),
    "dependents": (r"depend on (\S+) \(", 'ans = sorted(nx.ancestors(D, "{0}"))',
                   "SELECT DISTINCT ?n WHERE {{ ?n ex:dependsOn+ ex:{0} }}"),
    "dependencies": (r"dependencies of (\S+),", 'ans = sorted(nx.descendants(D, "{0}"))',
                     "SELECT DISTINCT ?n WHERE {{ ex:{0} ex:dependsOn+ ?n }}"),
    "cfs_dependents": (r"depend on (\S+)\?",
                       'ans = [a for a in nx.ancestors(D, "{0}") if node[a]["type"] == "CustomerFacingService"]',
                       "SELECT DISTINCT ?n WHERE {{ ?n ex:dependsOn+ ex:{0} ; "
                       "rdf:type/rdfs:subClassOf* ex:CustomerFacingService }}"),
    "depends_bool": (r"Does (\S+) transitively depend on (\S+)\?", 'ans = "{1}" in nx.descendants(D, "{0}")',
                     "ASK {{ ex:{0} ex:dependsOn+ ex:{1} }}"),
    "count_region": (r"deployed in (\S+)\?",
                     'ans = sum(1 for s, r, o in g["edges"] if r == "deployedIn" and o == "{0}" '
                     'and node[s]["type"] in ("Service", "CustomerFacingService"))',
                     "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {{ ?s rdf:type/rdfs:subClassOf* ex:Service ; "
                     "ex:deployedIn ex:{0} }}"),
    "tier_no_sla": (r"tier-(\d) services",
                    'rep = {{s for s, r, o in g["edges"] if r == "replicaOf"}}\n'
                    'sla = {{s for s, r, o in g["edges"] if r == "hasSLA"}}\n'
                    'ans = [k for k, v in node.items() if v.get("tier") == {0} and k not in rep and k not in sla]',
                    "SELECT ?s WHERE {{ ?s rdf:type/rdfs:subClassOf* ex:Service ; ex:tier {0} . "
                    "FILTER NOT EXISTS {{ ?s ex:replicaOf ?p }} FILTER NOT EXISTS {{ ?s ex:hasSLA ?x }} }}"),
    "region_down": (r"If region (\S+) fails, which services", LOST + PRIMARY_DOWN + "ans = pdown",
                    "SELECT DISTINCT ?s WHERE {{ " + DOWN_Q + NOT_REPLICA + " }}"),
    "region_count_down": (r"If region (\S+) fails, how many", LOST + PRIMARY_DOWN + "ans = len(pdown)",
                          "SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE {{ " + DOWN_Q + NOT_REPLICA + " }}"),
    "region_sla": (r"If region (\S+) fails, which SLAs",
                   LOST +
                   'ans = sorted({{o for s, r, o in g["edges"] if r == "hasSLA" and s in down}})',
                   "SELECT DISTINCT ?sla WHERE {{ " + DOWN_Q + " ?s ex:hasSLA ?sla }}"),
    "violations": (r"(?!)", 'ans = [f"{{s}}->{{o}}" for s, o in D.edges if node[s].get("tier") == 1 '
                            'and node[o].get("tier") == 3]',
                   "SELECT ?a ?b WHERE {{ ?a ex:dependsOn ?b . ?a ex:tier 1 . ?b ex:tier 3 }}"),
}


def fill(template, q, rx):
    m = re.search(rx, q["text"])
    return template.format(*(m.groups() if m else ()))


def check_kinds():
    print("1. Hand-written solutions through the real harness (all sizes)")
    for kind, (rx, py, sparql) in CASES.items():
        qs = [q for q in QS if q["kind"] == kind]
        b_ok = c_ok = 0
        for q in qs:
            code = B_PRELUDE + fill(py, q, rx) + "\n" + EMIT.format(t=q["answer_type"])
            final, err, _ = run_B.execute(f"```python\n{code}\n```", q)
            b_ok += err is None and score_one(final, q["answer_type"], ANS[q["qid"]], VALID[q["size"]])["f1"] == 1
            reply = f"```sparql\n{fill(sparql, q, rx)}\n```\n{{\"answer_type\": \"{q['answer_type']}\"}}"
            final, err, _ = run_C.execute(reply, q)
            ok = err is None and score_one(final, q["answer_type"], ANS[q["qid"]], VALID[q["size"]])["f1"] == 1
            c_ok += ok
            if not ok:
                print(f"     C FAIL {q['qid']}: err={err} got={final and final['answer']}")
        print(f"   {kind:18s} B {b_ok}/{len(qs)}   C {c_ok}/{len(qs)}")
        assert b_ok == c_ok == len(qs), kind


def check_c_errors():
    print("2a. C error mapping")
    q = next(q for q in QS if q["kind"] == "count_region")
    cases = {
        "parse": "```sparql\nSELEC ?x WHERE { ?x ?p ?o }\n```\n" + '{"answer_type": "number"}',
        "multi-row number": "```sparql\nSELECT ?s WHERE { ?s ex:tier 1 }\n```\n" + '{"answer_type": "number"}',
        "bool needs ASK": "```sparql\nSELECT ?s WHERE { ?s ex:tier 1 }\n```\n" + '{"answer_type": "bool"}',
        "no declaration": "```sparql\nSELECT ?s WHERE { ?s ex:tier 1 }\n```",
        "no query": "I cannot answer that.",
    }
    for name, reply in cases.items():
        final, err, info = run_C.execute(reply, q)
        assert final is None and err, name
        print(f"   ok  {name:17s} -> {info.get('failure')}: {err[:70]}")
    final, err, _ = run_C.execute("```sparql\nSELECT ?s WHERE { ?s ex:tier 99 }\n```\n" +
                                  '{"answer_type": "set"}', q)
    assert err is None and final["answer"] == []
    print("   ok  empty SELECT is a valid empty set, not an error")


def check_sandbox():
    print("2b. Sandbox guards")
    os.environ["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    old, sandbox.TIMEOUT_S = sandbox.TIMEOUT_S, 3
    try:
        r = sandbox.run_python("import os, json\nprint(json.dumps(sorted(os.listdir('.'))))\n"
                               "print('KEY' if 'ANTHROPIC_API_KEY' in os.environ else 'NOKEY')", 20)
        assert r["stdout"].split("\n")[:2] == ['["graph.json", "main.py"]', "NOKEY"], r
        print("   ok  cwd holds only graph.json + main.py; API key not in env")
        r = sandbox.run_python("open('answers.json')", 20)
        assert r["returncode"] != 0 and "FileNotFoundError" in r["stderr"]
        print("   ok  answers.json not reachable by relative path")
        r = sandbox.run_python("import urllib.request\nurllib.request.urlopen('http://example.com')", 20)
        assert r["returncode"] != 0 and "disabled in this sandbox" in r["stderr"], r["stderr"][-300:]
        print("   ok  network call raises")
        r = sandbox.run_python("import subprocess\nsubprocess.run(['whoami'])", 20)
        assert r["returncode"] != 0 and "disabled in this sandbox" in r["stderr"]
        print("   ok  subprocess raises")
        r = sandbox.run_python("while True: pass", 20)
        assert r["timeout"]
        print("   ok  infinite loop times out")
        for name, reply in {"exception": "```python\n1/0\n```", "no block": "just text",
                            "no answer": "```python\nprint('hello')\n```"}.items():
            final, err, _ = run_B.execute(reply, QS[0])
            assert final is None and err
            print(f"   ok  B {name:10s} -> {err.splitlines()[0][:70]}")
    finally:
        sandbox.TIMEOUT_S = old


def check_retry_loop():
    print("3. Retry loop with a stubbed LLM")
    q = next(q for q in QS if q["kind"] == "owner")
    good = f"```sparql\nSELECT ?t WHERE {{ ex:{re.search(r'owns (\S+)\?', q['text'])[1]} ex:ownedBy ?t }}\n```\n" \
           '{"answer_type": "set"}'
    empty = "```sparql\nSELECT ?t WHERE { ex:nobody ex:ownedBy ?t }\n```\n" + '{"answer_type": "set"}'
    bad = "```sparql\nSELECT ?t WHERE { broken\n```\n" + '{"answer_type": "set"}'

    def stub(replies):
        seen = []
        def call(condition, system, messages, **kw):
            seen.append(messages)
            return dict(text=replies[len(seen) - 1], tokens_in=100, tokens_out=10, latency_s=0.1,
                        cost_usd=0.001, cached=False)
        return call, seen

    for name, replies, want_retries, want_valid in [("error then fix", [bad, good], 1, True),
                                                    ("valid empty", [empty, good], 0, True),
                                                    ("error twice", [bad, bad, good], 1, False)]:
        common.llm.call, seen = stub(replies)
        rec = run_C.run(q)
        assert rec["retries"] == want_retries and rec["sparql_valid"] == want_valid, (name, rec)
        if want_retries:
            assert "That failed: the query failed (parse)" in seen[1][-1]["content"]
        print(f"   ok  {name:14s}: retries={rec['retries']} valid={rec['sparql_valid']} "
              f"failure_type={rec['failure_type']} tokens_in={rec['tokens_in']}")


if __name__ == "__main__":
    check_kinds()
    check_c_errors()
    check_sandbox()
    check_retry_loop()
    print("\nall harness tests passed")
