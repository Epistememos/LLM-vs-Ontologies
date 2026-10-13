"""check_docs.py - verify that the definitions moved out of the question text are all in each condition's docs,
and that no question text carries a definition or names the failed region.
Run (from the repo root): python exp2/check_docs.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import questions as exp1_questions  # noqa: E402  exp1 question templates, read only
from docs import DATA_NOTE_JSON, DATA_NOTE_RDF, DEFINITIONS, bplus_doc, bplusplus_doc  # noqa: E402
from rdflib import Graph, RDFS  # noqa: E402

norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()

# Each definition exp1 carried in question text: (name, exp1 wording as asked, required exp2 docs wording).
# The exp1 clause must occur in exp1's generated question texts; the exp2 clause must occur in every
# condition's docs. Differences between the two columns are the only rewordings (region-neutral grammar).
REQUIRED = [
    ("replicaOf direction", "'x replicaof y' means x is a replica of y", "'x replicaof y' means x is a replica of y"),
    ("replica group", "the node plus every node connected to it through replicaof links in either direction, transitively",
     "a node plus every node connected to it through replicaof links in either direction, transitively"),
    ("footprint", "the set of regions where members of its replica group are deployed",
     "the set of regions where members of a node's replica group are deployed"),
    ("lost", "a node is lost if its footprint contains only r", "a node is lost if its footprint contains only the failed region"),
    ("down", "a service is down if it is lost or if any node it transitively depends on (via dependson) is lost",
     "a service is down if it is lost or if any node it transitively depends on (via dependson) is lost"),
    ("primary", "x is primary if the data has no edge 'x replicaof y', i.e. x is not itself a replica of another node",
     "x is primary if the data has no edge 'x replicaof y', i.e. x is not itself a replica of another node"),
    ("breached SLA", "an sla is breached if any service that has it is down", "an sla is breached if any service that has it is down"),
    ("tier rule", "tier-1 services must not depend directly on tier-3 services", "tier-1 services must not depend directly on tier-3 services"),
    ("transitive dependency", "directly or through a chain of dependson", "directly or through a chain of dependson links"),
    ("tier risk", "transitively depend on at least one tier-3 service", "transitively depends on at least one tier-3 service"),
]


def ontology_text():
    g = Graph().parse(HERE / "ontology2.ttl")
    return " ".join(str(o) for o in g.objects(None, RDFS.comment))


def main():
    ok = True
    docs = {"B+ (exp2-docs)": bplus_doc(), "B++": bplusplus_doc(), "C2 (ontology2.ttl comments)": ontology_text()}

    # 0. the exp1 clauses really are what exp1 put in its question text (its generated questions)
    exp1_src = norm(" ".join(q["text"] for q in json.loads((HERE.parent / "data" / "questions.json").read_text())))

    print(f"{'definition':22} {'in exp1 Qs':10} " + " ".join(f"{k[:14]:14}" for k in docs) + " reworded")
    for name, old, new in REQUIRED:
        in_exp1 = old in exp1_src
        hits = [new in norm(text) for text in docs.values()]
        ok &= in_exp1 and all(hits)
        print(f"{name:22} {'yes' if in_exp1 else 'NO':10} " + " ".join(f"{'yes' if h else 'MISSING':14}" for h in hits)
              + ("  -" if old == new else f"  '{old}' -> '{new}'"))

    # 1. data notes: present where they belong, no definitions inside
    notes_ok = DATA_NOTE_JSON in bplus_doc() and DATA_NOTE_JSON in bplusplus_doc() and \
        not any(clause in norm(DATA_NOTE_JSON + " " + DATA_NOTE_RDF) for _, _, clause in REQUIRED)
    ok &= notes_ok
    print(f"\ndata-format notes present and definition-free: {'yes' if notes_ok else 'NO'}")
    print(f"  JSON: {DATA_NOTE_JSON}\n  RDF : {DATA_NOTE_RDF}")

    # 2. questions: no definitional clause, no region IDs in scenario questions
    qs = json.loads((HERE / "data" / "questions.json").read_text())
    leaks = [(q["qid"], c) for q in qs for _, _, c in REQUIRED if c in norm(q["text"])]
    leaks += [(q["qid"], "is down if"), ] if any("is down if" in norm(q["text"]) for q in qs) else []
    regions = [q["qid"] for q in qs if q["scenario"] and re.search(r"\breg-\d", q["text"])]
    ok &= not leaks and not regions
    print(f"questions carrying a definition: {leaks or 'none'}")
    print(f"scenario questions naming a region: {regions or 'none'} (of {sum(1 for q in qs if q['scenario'])})")

    # 3. every defined term the questions use is defined in DEFINITIONS
    used = {"down": "down", "lost": "lost", "primary": "primary", "breached": "breached", "tier rule": "tier rule",
            "tier risk": "tier risk", "failed region": "failed"}
    missing = [t for t, w in used.items() if any(w in norm(q["text"]) for q in qs)
               and t != "failed region" and t not in norm(DEFINITIONS)]
    ok &= not missing
    print(f"terms used in questions but undefined in the docs: {missing or 'none'}")
    print("\nALL CHECKS PASS" if ok else "\nCHECK FAILED")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
