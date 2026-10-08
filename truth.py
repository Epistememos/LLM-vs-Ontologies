"""truth.py - ground truth computed from the JSON graph with NetworkX.

Independent of rdflib and of every LLM harness. Run `python truth.py` for summary stats
and a check that every planted case in data/planted_{n}.json is detected.
"""
import json
from collections import Counter
from pathlib import Path

import networkx as nx

DATA = Path(__file__).parent / "data"
SERVICE_TYPES = {"Service", "CustomerFacingService"}
INFRA_TYPES = SERVICE_TYPES | {"Database", "Queue"}


class Truth:
    def __init__(self, n):
        g = json.loads((DATA / f"graph_{n}.json").read_text())
        self.nodes = {v["id"]: v for v in g["nodes"]}
        self.edges = [tuple(e) for e in g["edges"]]
        self.dep, self.rep = nx.DiGraph(), nx.Graph()
        self.dep.add_nodes_from(self.ids(*INFRA_TYPES))
        self.owner, self.region, self.sla = {}, {}, {}
        for s, r, o in self.edges:
            if r == "dependsOn":
                self.dep.add_edge(s, o)
            elif r == "replicaOf":  # s is the replica of o; the group is symmetric
                self.rep.add_edge(s, o)
            elif r == "ownedBy":
                self.owner[s] = o
            elif r == "deployedIn":
                self.region[s] = o
            elif r == "hasSLA":
                self.sla[s] = o
        assert nx.is_directed_acyclic_graph(self.dep)

    def ids(self, *types):
        return sorted(k for k, v in self.nodes.items() if v["type"] in types)

    def tier(self, x):
        return self.nodes[x].get("tier")

    # --- multi-hop
    def dependents(self, x):
        """Nodes that transitively depend on x."""
        return sorted(nx.ancestors(self.dep, x))

    def dependencies(self, x):
        """Nodes x transitively depends on."""
        return sorted(nx.descendants(self.dep, x))

    # --- replicas and region failure
    def replica_group(self, x):
        return nx.node_connected_component(self.rep, x) if x in self.rep else {x}

    def footprint(self, x):
        return {self.region[m] for m in self.replica_group(x)}

    def lost(self, x, r):
        return self.footprint(x) <= {r}

    def down_services(self, r):
        return sorted(s for s in self.ids(*SERVICE_TYPES)
                      if self.lost(s, r) or any(self.lost(d, r) for d in nx.descendants(self.dep, s)))

    def breached_slas(self, r):
        return sorted({self.sla[s] for s in self.down_services(r) if s in self.sla})

    def cfs_without_cross_region_replica(self):
        return [c for c in self.ids("CustomerFacingService") if len(self.footprint(c)) == 1]

    # --- constraints
    def tier_violations(self):
        return sorted((s, o) for s, o in self.dep.edges if self.tier(s) == 1 and self.tier(o) == 3)

    # --- out-of-schema (derived quantities)
    def longest_chain(self, x):
        """Number of edges on the longest dependsOn path starting at x."""
        memo = {}
        def depth(n):
            if n not in memo:
                memo[n] = max((1 + depth(m) for m in self.dep.successors(n)), default=0)
            return memo[n]
        return depth(x)

    def shortest_path_len(self, x, y):
        return nx.shortest_path_length(self.dep, x, y)

    def count_paths(self, x, y):
        """Number of distinct dependsOn paths from x to y."""
        memo = {y: 1}
        def paths(n):
            if n not in memo:
                memo[n] = sum(paths(m) for m in self.dep.successors(n))
            return memo[n]
        return paths(x)

    def primaries(self, *types):
        """Nodes of the given types that are not themselves a replica of another node."""
        replicas = {s for s, r, _ in self.edges if r == "replicaOf"}
        return [x for x in self.ids(*types) if x not in replicas]


def check(n):
    t = Truth(n)
    p = json.loads((DATA / f"planted_{n}.json").read_text())
    rp = p["failure_region"]
    down = set(t.down_services(rp))
    c, s1, s2, d = p["deep_chain"]
    d2, s3 = p["remote_dependents_db"], p["safe_service"]
    mode_ok = {"none": lambda x: len(t.replica_group(x)) == 1,
               "same": lambda x: len(t.replica_group(x)) > 1 and len(t.footprint(x)) == 1,
               "cross": lambda x: len(t.footprint(x)) > 1}
    checks = {
        "violations planted == detected": [tuple(v) for v in p["violations"]] == t.tier_violations(),
        "deep: db lost, chain not lost, cfs down": t.lost(d, rp) and not any(t.lost(x, rp) for x in (c, s1, s2))
            and c in down and d in t.dependencies(c),
        "remote db: lost, dependents elsewhere but down": t.lost(d2, rp)
            and all(t.region[x] != rp and x in down for x in t.dep.predecessors(d2)),
        "safe: in Rp, not lost": t.region[s3] == rp and not t.lost(s3, rp),
        "forced replica modes": all(mode_ok[m](x) for x, m in p["forced_replica_modes"].items()),
    }

    types = Counter(v["type"] for v in t.nodes.values())
    rels = Counter(r for _, r, _ in t.edges)
    cross = sum(t.region[a] != t.region[b] for a, b in t.rep.edges)
    hubs = sorted(t.dep.in_degree(t.ids(*INFRA_TYPES)), key=lambda kv: -kv[1])[:5]
    print(f"\n=== graph_{n}: {len(t.nodes)} nodes, {len(t.edges)} edges ===")
    print("  nodes by class :", dict(sorted(types.items())))
    print("  edges by rel   :", dict(sorted(rels.items())))
    print(f"  replicaOf      : {rels['replicaOf']} ({cross} cross-region, {rels['replicaOf'] - cross} same-region)")
    print("  top hubs (in-degree):", hubs)
    print("  max dependency chain:", max(t.longest_chain(x) for x in t.dep))
    print(f"  tier-1->tier-3 violations: {len(t.tier_violations())} (planted {len(p['violations'])})")
    print(f"  CFS w/o cross-region replica: {len(t.cfs_without_cross_region_replica())} / {types['CustomerFacingService']}")
    for r in t.ids("Region"):
        print(f"  if {r} fails: {len(t.down_services(r))} services down, SLAs breached {t.breached_slas(r)}")
    for name, ok in checks.items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return all(checks.values())


if __name__ == "__main__":
    assert all([check(n) for n in (20, 100, 500)])
