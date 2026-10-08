"""run_B.py - condition B: LLM + Python sandbox over the raw JSON, no schema documentation.

The prompt gives the file name, the JSON shape and a few sample records per node type and
relation; never the full graph. One program, one retry on error (exception, timeout, missing
code block, or no parseable answer printed). Run: python run_B.py --size 20 --split dev [--dry-run]
"""
import re

import llm
import sandbox
from common import ANSWER_SPEC, SCHEMA_DOC, cli, estimate, graph_sample, load_questions, save_results, solve_with_retry
from score import parse_answer

PROMPT_VERSION = 1  # bump on every DEV tuning iteration and log it in PROMPT_LOG.md
SYSTEM = """You answer questions about a company's infrastructure graph by writing a Python program.
The graph is in the file graph.json in the working directory, shaped as
{{"nodes": [{{"id": ..., "type": ..., <attributes>}}, ...], "edges": [[source, relation, target], ...]}}.
Sample records (the file holds many more):
{sample}
{schema}
Reply with one complete Python 3 program in a single ```python code block. It must read graph.json, compute
the answer, and print as its last line of output the JSON object {spec}
The standard library and networkx are available. There is no network access and a {timeout} s time limit."""

CODE_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.S)


def system_prompt(n, with_schema=False):
    schema = f"\n{SCHEMA_DOC}\nIn graph.json the node field 'type' holds the most specific class.\n" if with_schema else ""
    return SYSTEM.format(sample=graph_sample(n), schema=schema, spec=ANSWER_SPEC, timeout=sandbox.TIMEOUT_S)


def execute(text, q):
    blocks = CODE_RE.findall(text or "")
    if not blocks:
        return None, "no ```python code block found in your reply", {}
    r = sandbox.run_python(blocks[-1], q["size"])
    info = {k: r[k] for k in ("returncode", "timeout", "stdout", "stderr")}
    if r["timeout"]:
        return None, f"the program timed out after {sandbox.TIMEOUT_S} s", info
    if r["returncode"] != 0:
        return None, f"the program raised an error:\n{r['stderr'][-1500:]}", info
    final = parse_answer(r["stdout"])
    if final is None:
        return None, f"the program printed no answer JSON object. Output ended with:\n{r['stdout'][-800:]}", info
    return final, None, info


def main(condition, with_schema):
    args = cli(__doc__)
    qs = load_questions(args.sizes, args.split)
    print(f"{condition}: {len(qs)} questions, model {llm.MODEL}")
    estimate(qs, lambda n: system_prompt(n, with_schema), out_tokens=800, calls_per_q=1.2)
    if not args.dry_run:
        records = [solve_with_retry(condition, system_prompt(q["size"], with_schema), q, execute) for q in qs]
        print("wrote", save_results(condition, args.split, records),
              f"| spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")


if __name__ == "__main__":
    main("B", with_schema=False)
