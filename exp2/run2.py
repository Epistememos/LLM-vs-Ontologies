"""run2.py - Experiment 2 harnesses for B+ (exp2-docs), B++ and C2.

Reuses exp1's pieces unchanged (llm.call, common.solve_with_retry, the run_B prompt template and code
extraction, run_C's query extraction and result mapping, the sandbox runner and SPARQL runner, score's
answer parsing). What changes is only which files a question runs against:
  scenario question  -> the scenario copy (failed region asserted in the data)
  other question     -> the base graph
  B++                -> helpers.py is also copied into the sandbox
  C2                 -> the materialized graph (data + derived facts) and ontology2.ttl
Run (from the repo root): python exp2/run2.py {Bplus,Bplusplus,C2} [--size 20|100|500|all] [--split dev|test] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import common  # noqa: E402
import llm  # noqa: E402
import run_B  # noqa: E402
import run_C  # noqa: E402
import sandbox  # noqa: E402
from docs import DATA_NOTE_RDF, bplus_doc, bplusplus_doc  # noqa: E402
from score import parse_answer  # noqa: E402

DATA2 = HERE / "data"
common.DATA, common.RESULTS = DATA2, HERE / "results"  # graph samples from exp2 base graphs; results under exp2/
ONTOLOGY = HERE / "ontology2.ttl"
HELPERS = HERE / "helpers.py"
CONDITIONS = ("Bplus", "Bplusplus", "C2")
PROMPT_VERSION = {"Bplus": 1, "Bplusplus": 2, "C2": 1}  # bump on any DEV change and log it in LOG.md
# python -I does not put the script's folder on sys.path; both B conditions get this line so B++ can import
# helpers.py and B+ runs in an identical environment.
PATH_FIX = "import sys as _s; _s.path.insert(0, '.'); del _s\n"

# A 120 s API client timeout for every exp2 condition (exp1's llm.py uses the SDK default of 10 min with retries;
# one DEV call hung for 42 min). Not part of the cache key, so cached results are unaffected.
import anthropic  # noqa: E402

llm._client = anthropic.Anthropic(timeout=120.0)

C2_SYSTEM = """You answer questions about a company's infrastructure graph by writing one SPARQL 1.1 query.
The data is an RDF graph described by the ontology below. You see only the schema, not the data.
- The prefixes ex:, rdf:, rdfs:, owl: and xsd: are predeclared. The entity with ID svc-001 is ex:svc-001.
- Classes and properties whose comment starts with "Derived." have already been computed for this graph and
  can be queried directly, like asserted facts. rdf:type is already closed under rdfs:subClassOf.
- {data_note}

Ontology (Turtle):
{ttl}

Reply with the query in a single ```sparql code block, followed by one line with the JSON object
{{"answer_type": "<set|bool|number>"}}. The harness turns the query result into the answer:
- "set": a SELECT query; each result row is one entity ID (select exactly one variable; for an edge, select two
  variables, source then target, reported as 'source->target'). No rows means the empty set.
- "bool": an ASK query.
- "number": a SELECT query returning exactly one row with one numeric value (e.g. COUNT).
Queries have a {timeout} s time limit."""


def graph_file(q, suffix):
    base = DATA2 / "scenarios" / f"graph_{q['size']}_{q['scenario']}" if q["scenario"] else DATA2 / f"graph_{q['size']}"
    return base.with_suffix(suffix)


def materialized_file(q):
    return DATA2 / "materialized" / graph_file(q, ".ttl").name


def system_prompt(cond, n):
    if cond == "C2":
        return C2_SYSTEM.format(data_note=DATA_NOTE_RDF, ttl=ONTOLOGY.read_text(), timeout=sandbox.TIMEOUT_S)
    doc = bplus_doc() if cond == "Bplus" else bplusplus_doc()
    schema = f"\n{doc}\nIn graph.json the node field 'type' holds the most specific class.\n"
    return run_B.SYSTEM.format(sample=common.graph_sample(n), schema=schema, spec=common.ANSWER_SPEC,
                               timeout=sandbox.TIMEOUT_S)


def make_execute_py(with_helpers):
    def execute(text, q):  # run_B.execute's logic, with exp2 data files
        blocks = run_B.CODE_RE.findall(text or "")
        if not blocks:
            return None, "no ```python code block found in your reply", {}
        files = {"graph.json": graph_file(q, ".json"), "main.py": sandbox.PRELUDE + PATH_FIX + blocks[-1]}
        if with_helpers:
            files["helpers.py"] = HELPERS
        r = sandbox._run(["main.py"], files)
        info = {k: r[k] for k in ("returncode", "timeout", "stdout", "stderr")}
        if r["timeout"]:
            return None, f"the program timed out after {sandbox.TIMEOUT_S} s", info
        if r["returncode"] != 0:
            return None, f"the program raised an error:\n{r['stderr'][-1500:]}", info
        final = parse_answer(r["stdout"])
        if final is None:
            return None, f"the program printed no answer JSON object. Output ended with:\n{r['stdout'][-800:]}", info
        return final, None, info
    return execute


def run_sparql(query, q):  # sandbox.run_sparql's logic, against the materialized exp2 graph
    r = sandbox._run(["runner.py"], {"runner.py": sandbox.SPARQL_RUNNER, "data.ttl": materialized_file(q),
                                     "schema.ttl": ONTOLOGY}, stdin=query)
    if r["timeout"]:
        return {"error_kind": "timeout", "error": f"query timed out after {sandbox.TIMEOUT_S} s"}
    try:
        return json.loads(r["stdout"].strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"error_kind": "execution", "error": r["stderr"][-1500:] or "runner produced no output"}


def execute_c2(text, q):  # run_C.execute's logic, with run_sparql above
    blocks = [b for b in run_C.QUERY_RE.findall(text or "") if not run_C.TYPE_RE.fullmatch(b.strip())]
    declared = run_C.TYPE_RE.findall(text or "")
    if not blocks:
        return None, "no ```sparql code block found in your reply", {"failure": "no_query"}
    if not declared:
        return None, 'no {"answer_type": ...} declaration found after the query', {"failure": "no_type"}
    query, atype = blocks[-1], declared[-1]
    res = run_sparql(query, q)
    info = {"query": query, "declared_type": atype}
    if "error_kind" in res:
        return None, f"the query failed ({res['error_kind']}): {res['error'][:1200]}", info | {"failure": res["error_kind"]}
    answer, err = run_C.to_answer(res, atype)
    if err:
        return None, err, info | {"failure": "unmappable"}
    return {"answer_type": atype, "answer": answer}, None, info | {"failure": None, "n_rows": len(res.get("rows", []))}


EXECUTE = {"Bplus": make_execute_py(False), "Bplusplus": make_execute_py(True), "C2": execute_c2}


def run(cond, q):
    rec = common.solve_with_retry(f"e2-{cond}", system_prompt(cond, q["size"]), q, EXECUTE[cond])
    rec["condition"] = cond
    if cond == "C2":
        first, last = rec["attempts"][0], rec["attempts"][-1]
        rec["sparql_valid"] = last.get("failure") is None
        rec["first_try_valid"] = first.get("failure") is None
        rec["failure_type"] = "ok" if rec["sparql_valid"] else f"invalid:{last.get('failure')}"
    return rec


def load_questions(sizes, split):
    qs = json.loads((DATA2 / "questions.json").read_text())
    return [q for q in qs if q["size"] in sizes and q["split"] == split]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("condition", choices=CONDITIONS)
    p.add_argument("--size", default="all")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    sizes = common.SIZES if a.size == "all" else (int(a.size),)
    qs = load_questions(sizes, a.split)
    print(f"{a.condition}: {len(qs)} questions, model {llm.MODEL}")
    common.estimate(qs, lambda n: system_prompt(a.condition, n), out_tokens=800 if a.condition != "C2" else 500,
                    calls_per_q=1.2)
    if not a.dry_run:
        records = [run(a.condition, q) for q in qs]
        print("wrote", common.save_results(a.condition, a.split, records),
              f"| spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")
        if a.condition == "C2":
            print(f"SPARQL validity {sum(r['sparql_valid'] for r in records)}/{len(records)}, "
                  f"first-try {sum(r['first_try_valid'] for r in records)}/{len(records)}")
