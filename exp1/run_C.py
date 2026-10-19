"""run_C.py - condition C: LLM + ontology. The model sees only the schema (prose + schema.ttl),
never the data; it writes one SPARQL query, the harness executes it with rdflib, and on an error
(parse error, execution error, timeout, missing type declaration, or a result that cannot be mapped
to the declared answer type) it gets ONE retry with the error message. An empty result is valid.

The harness maps the result deterministically from the model's declared answer_type:
  set    -> SELECT; one entity per row (two or more selected variables are joined as 'a->b')
  bool   -> ASK
  number -> SELECT returning exactly one row with one numeric value (e.g. COUNT)
Limitation: C cannot post-process an awkwardly shaped result, A and B can.
Run: python run_C.py --size 20 --split dev [--dry-run]
"""
import json
import re
from pathlib import Path

import llm
import sandbox
from common import SCHEMA_DOC, cli, estimate, load_questions, save_results, solve_with_retry

PROMPT_VERSION = 1  # bump on every DEV tuning iteration and log it in PROMPT_LOG.md
SCHEMA_TTL = (Path(__file__).parent / "schema.ttl").read_text()
SYSTEM = """You answer questions about a company's infrastructure graph by writing one SPARQL 1.1 query.
The data is an RDF graph described by the ontology below. You see only the schema, not the data.
- The prefixes ex:, rdf:, rdfs:, owl: and xsd: are predeclared. The entity with ID svc-001 is ex:svc-001.
- No reasoner runs: each node is typed only with its most specific class and only direct dependsOn edges are
  stored. Use property paths, e.g. ex:dependsOn+ for transitive dependency and rdf:type/rdfs:subClassOf* for
  class membership.

{schema}

Ontology (Turtle):
{ttl}

Reply with the query in a single ```sparql code block, followed by one line with the JSON object
{{"answer_type": "<set|bool|number>"}}. The harness turns the query result into the answer:
- "set": a SELECT query; each result row is one entity ID (select exactly one variable; for an edge, select two
  variables, source then target, reported as 'source->target'). No rows means the empty set.
- "bool": an ASK query.
- "number": a SELECT query returning exactly one row with one numeric value (e.g. COUNT).
Queries have a {timeout} s time limit."""

QUERY_RE = re.compile(r"```(?:sparql)?\s*\n(.*?)```", re.S | re.I)
TYPE_RE = re.compile(r'\{\s*"answer_type"\s*:\s*"(set|bool|number)"\s*\}')


def system_prompt(n=None):  # identical for every size: C never sees the data
    return SYSTEM.format(schema=SCHEMA_DOC, ttl=SCHEMA_TTL, timeout=sandbox.TIMEOUT_S)


def to_answer(res, atype):
    """Map an executed query result to (answer, error)."""
    if atype == "bool":
        if res["kind"] != "ask":
            return None, "a bool answer needs an ASK query"
        return res["value"], None
    if res["kind"] != "select":
        return None, f"a {atype} answer needs a SELECT query"
    rows = [[c for c in row if c is not None] for row in res["rows"]]
    if atype == "set":
        return sorted({"->".join(map(str, r)) for r in rows if r}), None
    if len(rows) != 1 or len(rows[0]) != 1 or isinstance(rows[0][0], bool) \
            or not isinstance(rows[0][0], (int, float)):
        shape = f"{len(rows)} row(s)" + (f", first row {rows[0][:3]}" if rows else "")
        return None, f"a number answer needs exactly one row with one numeric value; got {shape}"
    return rows[0][0], None


def execute(text, q):
    # A fenced block holding only the type declaration is not a query (seen on DEV; see PROMPT_LOG.md).
    blocks = [b for b in QUERY_RE.findall(text or "") if not TYPE_RE.fullmatch(b.strip())]
    declared = TYPE_RE.findall(text or "")
    if not blocks:
        return None, "no ```sparql code block found in your reply", {"failure": "no_query"}
    if not declared:
        return None, 'no {"answer_type": ...} declaration found after the query', {"failure": "no_type"}
    query, atype = blocks[-1], declared[-1]
    res = sandbox.run_sparql(query, q["size"])
    info = {"query": query, "declared_type": atype}
    if "error_kind" in res:
        return None, f"the query failed ({res['error_kind']}): {res['error'][:1200]}", info | {"failure": res["error_kind"]}
    answer, err = to_answer(res, atype)
    if err:
        return None, err, info | {"failure": "unmappable"}
    return {"answer_type": atype, "answer": answer}, None, info | {"failure": None, "n_rows": len(res.get("rows", []))}


def run(q):
    rec = solve_with_retry("C", system_prompt(), q, execute)
    first, last = rec["attempts"][0], rec["attempts"][-1]
    rec["sparql_valid"] = last.get("failure") is None           # final query parsed, ran and mapped
    rec["first_try_valid"] = first.get("failure") is None
    rec["failure_type"] = "ok" if rec["sparql_valid"] else f"invalid:{last.get('failure')}"
    return rec


if __name__ == "__main__":
    args = cli(__doc__)
    qs = load_questions(args.sizes, args.split)
    print(f"C: {len(qs)} questions, model {llm.MODEL}")
    estimate(qs, system_prompt, out_tokens=500, calls_per_q=1.3)
    if not args.dry_run:
        records = [run(q) for q in qs]
        print("wrote", save_results("C", args.split, records),
              f"| spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")
        print(f"SPARQL validity {sum(r['sparql_valid'] for r in records)}/{len(records)}, "
              f"first-try {sum(r['first_try_valid'] for r in records)}/{len(records)}, "
              f"retried {sum(r['retries'] > 0 for r in records)}")
