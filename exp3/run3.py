"""run3.py - Experiment 3 harnesses for A3, B3 and C3 (prompt builders, execute paths, hidden-data guard).

Reuses exp1's pieces unchanged (llm.call, common.solve_with_retry, the sandbox runner and SPARQL runner, run_B's code
extraction, run_C's query extraction and result mapping, score.parse_answer).
Hidden-data guard: an audit hook that refuses any open/listing of a path under data/hidden/ is installed in this
process on import and at the top of every sandbox program and SPARQL runner. Audit hooks cannot be removed.
Repeats: repeat k > 1 uses its own cache namespace (condition "e3-<C>-r<k>"), so it bypasses the response cache
without changing temperature or exp1's llm.py.
Run (from the repo root): python exp3/run3.py {A3,B3,C3} [--size 20|100|500|all] [--split dev|test] [--repeat k] [--dry-run]
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "exp1"), str(HERE)]

GUARD = r'''import sys as _sys, os as _os, re as _re
def _hidden_guard(event, args, _pat=_re.compile(r"[\\/]data[\\/]hidden([\\/]|$)", _re.I), _os=_os):
    if event in ("open", "os.listdir", "os.scandir", "glob.glob", "shutil.copyfile", "shutil.copytree") and args:
        p = args[0]
        if isinstance(p, (str, bytes, _os.PathLike)) and _pat.search(_os.path.abspath(_os.fsdecode(p))):
            raise PermissionError("data/hidden/ is not readable by any condition")
_sys.addaudithook(_hidden_guard)
del _sys, _os, _re
'''
exec(GUARD)  # noqa: S102  guard this harness process before anything else is imported

import anthropic  # noqa: E402
import common  # noqa: E402
import llm  # noqa: E402
import run_B  # noqa: E402
import run_C  # noqa: E402
import sandbox  # noqa: E402
from docs3 import a3_doc, b3_doc, c3_doc  # noqa: E402
from score import parse_answer  # noqa: E402

DATA3 = HERE / "data"
GLUE, TABLES, ONTOLOGY = HERE / "glue.py", HERE / "mapping_tables.json", HERE / "ontology3.ttl"
CONDITIONS = ("A3", "B3", "C3")
A3_SIZES = (20, 100)                    # pre-registered: A3 on the two smaller graphs only
PROMPT_VERSION = {"A3": 1, "B3": 2, "C3": 2}  # v2: clarity fix 1 of 3, see LOG3.md
PATH_FIX = "import sys as _s; _s.path.insert(0, '.'); del _s\n"
llm._client = anthropic.Anthropic(timeout=120.0)   # as in Experiment 2

A3_SYSTEM = """You answer questions about a company's infrastructure. Both source exports are below.
{doc}

cmdb.json:
{cmdb}

monitoring.json:
{monitoring}

mapping_tables.json:
{tables}

End your reply with exactly one JSON object on its own line: {spec}"""

B3_SYSTEM = """You answer questions about a company's infrastructure by writing a Python program.
The working directory holds cmdb.json, monitoring.json, mapping_tables.json and glue.py.
{doc}

Sample records (the files hold many more):
{sample}

Reply with one complete Python 3 program in a single ```python code block. It must compute the answer and print as its
last line of output the JSON object {spec}
The standard library and networkx are available. There is no network access and a {timeout} s time limit."""

C3_SYSTEM = """You answer questions about a company's infrastructure by writing one SPARQL 1.1 query.
The data is an RDF graph described by the ontology below. You see only the schema, not the data.
- The prefixes ex:, rdf:, rdfs:, owl: and xsd: are predeclared (declare src: yourself if you use it:
  PREFIX src: <http://example.org/src#>).
- Classes and properties whose comment starts with "Derived." have already been computed and can be queried
  directly, like asserted facts. rdf:type is already closed under rdfs:subClassOf.
{doc}

Ontology (Turtle):
{ttl}

Reply with the query in a single ```sparql code block, followed by one line with the JSON object
{{"answer_type": "<set|bool|number>"}}. The harness turns the query result into the answer:
- "set": a SELECT query; each result row is one entity ID (select exactly one variable). No rows means the empty set.
- "bool": an ASK query.
- "number": a SELECT query returning exactly one row with one numeric value (e.g. COUNT).
Queries have a {timeout} s time limit."""


def export_path(n, which):
    return DATA3 / f"{which}_{n}.json"


def tables_json(n):
    return json.dumps({str(n): json.loads(TABLES.read_text())[str(n)]})


def sample(n, k=2):
    cm = json.loads(export_path(n, "cmdb").read_text())["records"]
    mo = json.loads(export_path(n, "monitoring").read_text())["records"]
    pick = lambda rs, field: [r for c in sorted({r[field] for r in rs}) for r in [x for x in rs if x[field] == c][:k]]
    return "cmdb.json records:\n" + "\n".join(json.dumps(r) for r in pick(cm, "ci_class")) + \
        "\nmonitoring.json records:\n" + "\n".join(json.dumps(r) for r in pick(mo, "kind"))


def system_prompt(cond, n):
    spec, timeout = common.ANSWER_SPEC, sandbox.TIMEOUT_S
    if cond == "A3":
        compact = lambda p: json.dumps(json.loads(p.read_text()), separators=(",", ":"))
        return A3_SYSTEM.format(doc=a3_doc(), cmdb=compact(export_path(n, "cmdb")),
                                monitoring=compact(export_path(n, "monitoring")), tables=tables_json(n), spec=spec)
    if cond == "B3":
        return B3_SYSTEM.format(doc=b3_doc(), sample=sample(n), spec=spec, timeout=timeout)
    return C3_SYSTEM.format(doc=c3_doc(), ttl=ONTOLOGY.read_text(), timeout=timeout)


def sandbox_files(n, code):
    """Every file the B3 sandbox gets; no path under data/hidden/."""
    return {"cmdb.json": export_path(n, "cmdb"), "monitoring.json": export_path(n, "monitoring"),
            "mapping_tables.json": tables_json(n), "glue.py": GLUE,
            "main.py": sandbox.PRELUDE + GUARD + PATH_FIX + code}


def execute_b3(text, q):  # run_B.execute's logic with exp3 files
    blocks = run_B.CODE_RE.findall(text or "")
    if not blocks:
        return None, "no ```python code block found in your reply", {}
    r = sandbox._run(["main.py"], sandbox_files(q["size"], blocks[-1]))
    info = {k: r[k] for k in ("returncode", "timeout", "stdout", "stderr")}
    if r["timeout"]:
        return None, f"the program timed out after {sandbox.TIMEOUT_S} s", info
    if r["returncode"] != 0:
        return None, f"the program raised an error:\n{r['stderr'][-1500:]}", info
    final = parse_answer(r["stdout"])
    if final is None:
        return None, f"the program printed no answer JSON object. Output ended with:\n{r['stdout'][-800:]}", info
    return final, None, info


def runner_files(n):
    """Every file the C3 SPARQL runner gets; no path under data/hidden/."""
    return {"runner.py": GUARD + sandbox.SPARQL_RUNNER, "data.ttl": DATA3 / "rdf" / f"materialized_{n}.ttl",
            "schema.ttl": ONTOLOGY}


def run_sparql(query, q):  # sandbox.run_sparql's logic against the materialized exp3 graph
    r = sandbox._run(["runner.py"], runner_files(q["size"]), stdin=query)
    if r["timeout"]:
        return {"error_kind": "timeout", "error": f"query timed out after {sandbox.TIMEOUT_S} s"}
    try:
        return json.loads(r["stdout"].strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"error_kind": "execution", "error": r["stderr"][-1500:] or "runner produced no output"}


def execute_c3(text, q):  # run_C.execute's logic (as in Experiment 2)
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
    return {"answer_type": atype, "answer": answer}, None, info | {"failure": None}


def run(cond, q, repeat=1):
    tag = f"e3-{cond}" + (f"-r{repeat}" if repeat > 1 else "")
    if cond == "A3":
        rec = llm.call(tag, system_prompt(cond, q["size"]), [{"role": "user", "content": common.question_prompt(q)}],
                       cache_system=True)
        final = parse_answer(rec["text"])
        out = dict(condition=cond, qid=q["qid"], final=final, retries=0, timeouts=0,
                   error=None if final else "no parseable answer", attempts=[dict(text=rec["text"])],
                   **{k: rec[k] for k in ("tokens_in", "tokens_out", "latency_s", "cost_usd", "cached")})
    else:
        out = common.solve_with_retry(tag, system_prompt(cond, q["size"]), q, execute_b3 if cond == "B3" else execute_c3)
        out["condition"] = cond
    out["repeat"] = repeat
    return out


def load_questions(sizes, split):
    qs = json.loads((DATA3 / "questions.json").read_text())
    return [q for q in qs if q["size"] in sizes and q["split"] == split]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("condition", choices=CONDITIONS)
    p.add_argument("--size", default="all")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--repeat", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    sizes = (20, 100, 500) if a.size == "all" else (int(a.size),)
    if a.condition == "A3":
        sizes = tuple(s for s in sizes if s in A3_SIZES)
    qs = load_questions(sizes, a.split)
    print(f"{a.condition} repeat {a.repeat}: {len(qs)} questions, model {llm.MODEL}")
    common.estimate(qs, lambda n: system_prompt(a.condition, n), out_tokens=800 if a.condition == "B3" else 500,
                    calls_per_q=1.0 if a.condition == "A3" else 1.2)
    if not a.dry_run:
        common.RESULTS = HERE / "results"
        records = [run(a.condition, q, a.repeat) for q in qs]
        print("wrote", common.save_results(f"{a.condition}_r{a.repeat}", a.split, records),
              f"| spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")
