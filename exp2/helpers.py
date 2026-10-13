"""helpers.py - executable definitions for condition B++ (standard library only).

    from helpers import Infra
    g = Infra("graph.json")

The graph file may mark one region as failed ("failed": true on the Region node); every method
that takes a region argument defaults to that failed region.

Definitions implemented here (identical to the C2 ontology rules):
  replica group  : a node plus every node linked to it by replicaOf in either direction, transitively
  footprint      : the set of regions where members of a node's replica group are deployed
  primary        : a Service, Database or Queue that is not itself a replica (no outgoing replicaOf)
  lost           : a component whose footprint contains only the failed region
  down           : a service (of any kind) that is lost or transitively depends on a lost node
  breached SLA   : an SLA held by at least one down service
  tier violation : a direct dependsOn edge from a tier-1 service to a tier-3 service
  tier risk      : a tier-1 service that transitively depends on a tier-3 service
"""
import json
from collections import defaultdict

SERVICE_TYPES = {"Service", "CustomerFacingService"}
COMPONENT_TYPES = SERVICE_TYPES | {"Database", "Queue"}


class Infra:
    def __init__(self, path="graph.json"):
        data = json.load(open(path))
        self.nodes = {v["id"]: v for v in data["nodes"]}
        self.edges = [tuple(e) for e in data["edges"]]
        self.deps = defaultdict(set)      # x -> nodes x directly depends on
        self.dependents = defaultdict(set)  # x -> nodes directly depending on x
        self.replica_links = defaultdict(set)  # undirected replicaOf adjacency
        self.region, self.owner, self.sla = {}, {}, {}
        self.replicas = set()             # nodes that are a replica of something
        for s, r, o in self.edges:
            if r == "dependsOn":
                self.deps[s].add(o)
                self.dependents[o].add(s)
            elif r == "replicaOf":
                self.replica_links[s].add(o)
                self.replica_links[o].add(s)
                self.replicas.add(s)
            elif r == "deployedIn":
                self.region[s] = o
            elif r == "ownedBy":
                self.owner[s] = o
            elif r == "hasSLA":
                self.sla[s] = o
        failed = [k for k, v in self.nodes.items() if v["type"] == "Region" and v.get("failed")]
        self.failed_region = failed[0] if failed else None

    # ---- types
    def of_type(self, *types):
        return sorted(k for k, v in self.nodes.items() if v["type"] in types)

    def services(self):
        return self.of_type(*SERVICE_TYPES)

    def components(self):
        return self.of_type(*COMPONENT_TYPES)

    def is_primary(self, x):
        return self.nodes[x]["type"] in COMPONENT_TYPES and x not in self.replicas

    def primaries(self, *types):
        return [x for x in self.of_type(*(types or COMPONENT_TYPES)) if self.is_primary(x)]

    # ---- dependency closure
    def transitive_dependencies(self, x):
        seen, stack = set(), list(self.deps[x])
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.deps[n])
        return seen

    def transitive_dependents(self, x):
        seen, stack = set(), list(self.dependents[x])
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.dependents[n])
        return seen

    # ---- replicas and failure
    def replica_group(self, x):
        seen, stack = {x}, [x]
        while stack:
            for m in self.replica_links[stack.pop()]:
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        return seen

    def footprint(self, x):
        return {self.region[m] for m in self.replica_group(x)}

    def is_lost(self, x, region=None):
        region = region or self.failed_region
        return self.footprint(x) == {region}

    def lost_components(self, region=None):
        return [x for x in self.components() if self.is_lost(x, region)]

    def is_down(self, x, region=None):
        if self.nodes[x]["type"] not in SERVICE_TYPES:
            return False
        return self.is_lost(x, region) or any(self.is_lost(d, region) for d in self.transitive_dependencies(x))

    def down_services(self, region=None, primary_only=False):
        down = [s for s in self.services() if self.is_down(s, region)]
        return [s for s in down if self.is_primary(s)] if primary_only else down

    def breached_slas(self, region=None):
        return sorted({self.sla[s] for s in self.down_services(region) if s in self.sla})

    # ---- tier rule
    def tier(self, x):
        return self.nodes[x].get("tier")

    def tier_violations(self):
        return sorted((s, o) for s, r, o in self.edges
                      if r == "dependsOn" and self.tier(s) == 1 and self.tier(o) == 3)

    def tier_risk_services(self):
        return [s for s in self.services()
                if self.tier(s) == 1 and any(self.tier(d) == 3 for d in self.transitive_dependencies(s))]
