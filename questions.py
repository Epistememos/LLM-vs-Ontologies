"""questions.py - programmatic questions with ground-truth answers from truth.py.

Writes data/questions.json (what harnesses may read: no answers) and
data/answers.json (answer key, read only by score.py). Run: python questions.py
"""
import json
import random

from truth import DATA, SERVICE_TYPES, Truth

SIZES = (20, 100, 500)
PER_LEVEL = 10
DEV_FRAC = 0.3
# Per-level quotas by kind; shortfalls are filled from any remaining candidates of that level.
QUOTAS = {
    "L1": {"owner": 4, "region": 4, "tier": 2},
    "L2": {"dependents": 3, "dependencies": 3, "cfs_dependents": 2, "depends_bool": 2},
    "L3": {"cfs_no_cross": 1, "team_db_unreplicated": 3, "count_region": 3, "unused_db": 1, "tier_no_sla": 2},
    "L4": {"region_sla": 3, "region_down": 2, "region_survivors": 2, "region_count_down": 1,
           "violations": 1, "transitive_violations": 1},
    "L5": {"longest_chain": 2, "shortest_path": 2, "path_count": 1},
}
FAILURE_DEF = (
    "Definitions: 'X replicaOf Y' means X is a replica of Y. A node's replica group is the node plus every "
    "node connected to it through replicaOf links in either direction, transitively. A node's footprint is the "
    "set of regions where members of its replica group are deployed. When region R fails, a node is lost if its "
    "footprint contains only R. A service is down if it is lost or if any node it transitively depends on "
    "(via dependsOn) is lost.")
PRIMARY = ("(consider only primary nodes: a node X is primary if the data has no edge 'X replicaOf Y', "
           "i.e. X is not itself a replica of another node)")


def candidates(t, n):
    """All candidate questions per level: {level: {kind: [(text, answer_type, answer), ...]}}."""
    svc = t.primaries(*SERVICE_TYPES)
    infra = t.primaries(*SERVICE_TYPES, "Database", "Queue")
    dbs = t.primaries("Database")
    cfs = t.primaries("CustomerFacingService")
    regions, teams = t.ids("Region"), t.ids("Team")
    c = {lvl: {k: [] for k in q} for lvl, q in QUOTAS.items()}

    for x in infra:
        c["L1"]["owner"].append((f"Which team owns {x}?", "set", [t.owner[x]]))
        c["L1"]["region"].append((f"In which region is {x} deployed?", "set", [t.region[x]]))
    for x in svc:
        c["L1"]["tier"].append((f"What is the tier of {x}?", "number", t.tier(x)))

    for x in infra:
        if t.dependents(x):
            c["L2"]["dependents"].append(
                (f"Which nodes transitively depend on {x} (directly or through a chain of dependsOn)?",
                 "set", t.dependents(x)))
            cf = [a for a in t.dependents(x) if a in cfs]
            if cf:
                c["L2"]["cfs_dependents"].append(
                    (f"Which customer-facing services transitively depend on {x}?", "set", cf))
        if len(t.dependencies(x)) >= 2:
            c["L2"]["dependencies"].append(
                (f"What are all upstream dependencies of {x}, i.e. every node it transitively depends on?",
                 "set", t.dependencies(x)))
    for x in svc:
        direct = set(t.dep.successors(x))
        deep = [y for y in t.dependencies(x) if y not in direct]
        far = [y for y in infra if y != x and y not in t.dependencies(x)]
        for y, ans in ((deep[0], True) if deep else (None, None), (far[0], False) if far else (None, None)):
            if y:
                c["L2"]["depends_bool"].append((f"Does {x} transitively depend on {y}?", "bool", ans))

    c["L3"]["cfs_no_cross"].append(
        ("Which customer-facing services have no replica deployed in a different region from their own? "
         f"{PRIMARY} {FAILURE_DEF}", "set", [x for x in t.cfs_without_cross_region_replica() if x in cfs]))
    for team in teams:
        owned = [d for d in dbs if t.owner[d] == team]
        if owned:
            c["L3"]["team_db_unreplicated"].append(
                (f"Which databases owned by {team} have no replica at all? {PRIMARY}",
                 "set", [d for d in owned if len(t.replica_group(d)) == 1]))
    for r in regions:
        c["L3"]["count_region"].append(
            (f"How many services of any kind (including replicas) are deployed in {r}?", "number",
             sum(t.region[s] == r for s in t.ids(*SERVICE_TYPES))))
    c["L3"]["unused_db"].append(
        (f"Which databases have no node directly depending on them? {PRIMARY}", "set",
         [d for d in dbs if not t.dependents(d)]))
    for k in (1, 2, 3):
        c["L3"]["tier_no_sla"].append(
            (f"Which tier-{k} services have no SLA? {PRIMARY}", "set",
             [s for s in svc if t.tier(s) == k and s not in t.sla]))

    for r in regions:
        down = t.down_services(r)
        if n != 20:  # at 20 nodes every failure breaches every SLA, so the question carries no signal
            c["L4"]["region_sla"].append(
                (f"If region {r} fails, which SLAs are breached? An SLA is breached if any service that "
                 f"has it is down. {FAILURE_DEF}", "set", t.breached_slas(r)))
        down_primary = [s for s in down if s in svc]  # replicas have no dependsOn of their own; see PROMPT_LOG.md
        c["L4"]["region_down"].append(
            (f"If region {r} fails, which services are down? {PRIMARY} {FAILURE_DEF}", "set", down_primary))
        c["L4"]["region_survivors"].append(
            (f"If region {r} fails, which customer-facing services deployed in {r} are NOT down? {PRIMARY} "
             f"{FAILURE_DEF}", "set", [x for x in cfs if t.region[x] == r and x not in down]))
        c["L4"]["region_count_down"].append(
            (f"If region {r} fails, how many services are down? {PRIMARY} {FAILURE_DEF}",
             "number", len(down_primary)))
    c["L4"]["violations"].append(
        ("Which dependsOn edges violate the rule that tier-1 services must not depend directly on tier-3 "
         "services? Give each edge as 'SOURCE->TARGET'.", "set", [f"{a}->{b}" for a, b in t.tier_violations()]))
    c["L4"]["transitive_violations"].append(
        ("Which tier-1 services transitively depend on at least one tier-3 service?", "set",
         [s for s in t.ids(*SERVICE_TYPES) if t.tier(s) == 1 and any(t.tier(d) == 3 for d in t.dependencies(s))]))

    for x in svc:
        if t.longest_chain(x) >= 2:
            c["L5"]["longest_chain"].append(
                (f"How many dependsOn edges are on the longest dependency chain starting at {x}?",
                 "number", t.longest_chain(x)))
        for y in t.dependencies(x):
            sp = t.shortest_path_len(x, y)
            if sp >= 2:
                c["L5"]["shortest_path"].append(
                    (f"What is the minimum number of dependsOn edges on a path from {x} to {y}?", "number", sp))
            if t.count_paths(x, y) >= 2:
                c["L5"]["path_count"].append(
                    (f"How many distinct dependsOn paths lead from {x} to {y}?", "number", t.count_paths(x, y)))
    return c


def pick(rng, kinds, quotas, total):
    chosen, rest = [], []
    for kind, quota in quotas.items():
        pool = rng.sample(kinds[kind], len(kinds[kind]))
        chosen += [(kind, q) for q in pool[:quota]]
        rest += [(kind, q) for q in pool[quota:]]
    return chosen + rng.sample(rest, max(0, min(total - len(chosen), len(rest))))


def build():
    questions, answers = [], {}
    for n in SIZES:
        t, rng = Truth(n), random.Random(1000 + n)
        for level, kinds in candidates(t, n).items():
            total = 5 if level == "L5" else PER_LEVEL
            chosen = pick(rng, kinds, QUOTAS[level], total)[:total]
            rng.shuffle(chosen)
            n_dev = max(1, round(DEV_FRAC * len(chosen)))
            for i, (kind, (text, atype, ans)) in enumerate(chosen):
                qid = f"{n}-{level}-{i:02d}"
                questions.append(dict(qid=qid, size=n, level=level, kind=kind, answer_type=atype,
                                      split="dev" if i < n_dev else "test", text=text))
                answers[qid] = ans
    (DATA / "questions.json").write_text(json.dumps(questions, indent=1))
    (DATA / "answers.json").write_text(json.dumps(answers, indent=1))
    return questions, answers


if __name__ == "__main__":
    import pandas as pd
    qs, ans = build()
    df = pd.DataFrame(qs)
    print(pd.crosstab([df["size"], df["split"]], df["level"], margins=True))
    for level in QUOTAS:
        print(f"\n--- {level} examples (size 100) ---")
        for q in [q for q in qs if q["size"] == 100 and q["level"] == level][:2]:
            a = ans[q["qid"]]
            shown = a if not isinstance(a, list) or len(a) <= 12 else a[:12] + [f"... ({len(a)} total)"]
            print(f"[{q['qid']} {q['kind']} {q['answer_type']}] {q['text'][:200]}\n   -> {shown}")
