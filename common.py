"""common.py - pieces every condition shares, so the conditions differ only in what they are given."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

import llm

ROOT = Path(__file__).parent
DATA, RESULTS = ROOT / "data", ROOT / "results"
SIZES = (20, 100, 500)
MAX_RETRIES = 1  # identical budget: B, B+ and C get one retry, on errors only; A gets none

ANSWER_SPEC = ('{"answer_type": "<set|bool|number>", "answer": <value>}, where a "set" answer is a JSON list '
               'of entity IDs exactly as they appear in the data (an empty list if nothing qualifies), a "bool" '
               'answer is true or false, and a "number" answer is a single number.')

# Prose schema documentation: given verbatim to B+ and C (C additionally gets schema.ttl).
SCHEMA_DOC = """Schema documentation.
Classes:
- Service: a software service, with attribute tier (integer 1-3; 1 is the most critical).
- CustomerFacingService: a subclass of Service; every CustomerFacingService is also a Service.
- Database and Queue: data stores. Service (with its subclass), Database and Queue are the infrastructure components.
- Team, Region, and SLA (with attribute availability, a percentage).
Relations (directed, source -> target):
- dependsOn (component -> component): the source needs the target to work. Dependency is transitive: if A
  dependsOn B and B dependsOn C, then A transitively depends on C. Only direct dependencies are stored.
- ownedBy (component -> Team): every component has exactly one owning team.
- deployedIn (component -> Region): every component is deployed in exactly one region.
- hasSLA (Service -> SLA): the service is bound by that SLA; not every service has one.
- replicaOf (X -> Y, between Services or between Databases): X is a replica of Y. A replica has the same type,
  tier and owner as the node it replicates, and no dependsOn or hasSLA links of its own. A primary is a node that
  is not a replica of anything. A node and its replicas form a replica group; group membership is symmetric
  (if X replicaOf Y, X is in Y's group and Y is in X's group)."""


def question_prompt(q):
    return f"Question: {q['text']}\nExpected answer_type: \"{q['answer_type']}\""


def graph_sample(n, per_group=2):
    """First few nodes per type and edges per relation, as they appear in graph.json."""
    g = json.loads((DATA / f"graph_{n}.json").read_text())
    nodes, edges = defaultdict(list), defaultdict(list)
    for v in g["nodes"]:
        nodes[v["type"]].append(v)
    for e in g["edges"]:
        edges[e[1]].append(e)
    pick = lambda d: [json.dumps(x) for k in sorted(d) for x in d[k][:per_group]]
    return "nodes:\n" + "\n".join(pick(nodes)) + "\nedges:\n" + "\n".join(pick(edges))


def solve_with_retry(condition, system, q, execute):
    """Ask, execute the reply, and retry once with the error message if execution failed.

    execute(reply_text, q) -> (final | None, error | None, info). A legitimately empty
    answer is not an error and is never retried.
    """
    messages = [{"role": "user", "content": question_prompt(q)}]
    tot = dict(tokens_in=0, tokens_out=0, latency_s=0.0, cost_usd=0.0)
    attempts, cached = [], True
    for attempt in range(MAX_RETRIES + 1):
        rec = llm.call(condition, system, messages, cache_system=True)
        for k in tot:
            tot[k] += rec[k]
        cached &= rec["cached"]
        final, err, info = execute(rec["text"], q)
        attempts.append(dict(text=rec["text"], error=err, **info))
        if err is None or attempt == MAX_RETRIES:
            break
        messages = messages + [
            {"role": "assistant", "content": rec["text"]},
            {"role": "user", "content": f"That failed: {err}\nFix the problem and reply again in the same format."}]
    timeouts = sum(bool(a.get("timeout")) or a.get("failure") == "timeout" for a in attempts)
    return dict(condition=condition, qid=q["qid"], final=final if err is None else None,
                retries=len(attempts) - 1, timeouts=timeouts, error=err, cached=cached, attempts=attempts, **tot)


def load_questions(sizes, split):
    """Questions only - the answer key lives in data/answers.json and is never read by a harness."""
    qs = json.loads((DATA / "questions.json").read_text())
    return [q for q in qs if q["size"] in sizes and q["split"] == split]


def save_results(condition, split, records):
    """Merge into results/{condition}_{split}.jsonl, replacing earlier records for the same qids."""
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{condition}_{split}.jsonl"
    old = {}
    if path.exists():
        old = {r["qid"]: r for r in map(json.loads, path.read_text().splitlines()) if r}
    old |= {r["qid"]: r for r in records}
    path.write_text("".join(json.dumps(r) + "\n" for r in sorted(old.values(), key=lambda r: r["qid"])))
    return path


def cli(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--size", default="20", help="20, 100, 500 or all")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--dry-run", action="store_true", help="estimate calls and cost, call nothing")
    a = p.parse_args()
    a.sizes = SIZES if a.size == "all" else (int(a.size),)
    return a


def estimate(qs, system_for_size, out_tokens=500, calls_per_q=1.0):
    """Rough cost if nothing is on disk: one cache write per size, then cache reads."""
    total, n_calls = 0.0, 0
    for n in sorted({q["size"] for q in qs}):
        prefix = llm.approx_tokens(system_for_size(n))
        sub = [q for q in qs if q["size"] == n]
        for i, q in enumerate(sub):
            qt = llm.approx_tokens(question_prompt(q))
            total += calls_per_q * llm.cost_usd(llm.MODEL, qt, prefix if i == 0 else 0,
                                                0 if i == 0 else prefix, out_tokens)
        n_calls += len(sub) * calls_per_q
        print(f"  size {n}: {len(sub)} questions, system prefix ~{prefix:,.0f} tokens")
    print(f"  ~{n_calls:.0f} calls, estimated ${total:.3f} (~{out_tokens} output tokens/call)")
