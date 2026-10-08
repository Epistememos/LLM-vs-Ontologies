"""run_A.py - condition A: LLM alone, the full graph serialized in the prompt, no tools, no retry.

The prompt gives the data only (node types and attributes, edge triples); no schema documentation,
the same information B gets from the raw JSON. Run: python run_A.py --size 20 --split dev [--dry-run]
"""
import json

import llm
from common import ANSWER_SPEC, DATA, cli, estimate, load_questions, question_prompt, save_results
from score import parse_answer

PROMPT_VERSION = 1  # bump on every DEV tuning iteration and log it in PROMPT_LOG.md
SYSTEM = """You answer questions about a company's infrastructure graph. The complete graph is below.
Each NODE line is: id type [attribute=value ...]. Each EDGE line is: source relation target.
Work from this data only. End your reply with exactly one JSON object on its own line: {spec}"""


def serialize(n):
    g = json.loads((DATA / f"graph_{n}.json").read_text())
    nodes = [" ".join([v["id"], v["type"]] + [f"{k}={v[k]}" for k in v if k not in ("id", "type")])
             for v in g["nodes"]]
    return "NODES\n" + "\n".join(nodes) + "\n\nEDGES\n" + "\n".join(" ".join(e) for e in g["edges"])


def system_prompt(n):
    return SYSTEM.format(spec=ANSWER_SPEC) + "\n\n" + serialize(n)


def run(q):
    rec = llm.call("A", system_prompt(q["size"]), [{"role": "user", "content": question_prompt(q)}],
                   cache_system=True)
    final = parse_answer(rec["text"])
    return dict(condition="A", qid=q["qid"], final=final, retries=0,
                error=None if final else "no parseable answer",
                attempts=[dict(text=rec["text"])],
                **{k: rec[k] for k in ("tokens_in", "tokens_out", "latency_s", "cost_usd", "cached")})


if __name__ == "__main__":
    args = cli(__doc__)
    qs = load_questions(args.sizes, args.split)
    print(f"A: {len(qs)} questions, model {llm.MODEL}")
    estimate(qs, system_prompt, out_tokens=650)
    if not args.dry_run:
        records = [run(q) for q in qs]
        print("wrote", save_results("A", args.split, records),
              f"| spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")
