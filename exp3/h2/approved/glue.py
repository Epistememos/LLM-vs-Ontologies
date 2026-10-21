"""glue.py - B3's glue library over the two exports (standard library only).

    from glue import Infra3
    g = Infra3("cmdb.json", "monitoring.json", "mapping_tables.json")

Entities are identified by their CMDB CI ID. Every name either export uses (CI ID, CMDB name, monitoring
component ID, display name, alias) resolves to it with g.resolve(name). The resolution rules are applied:
CMDB is authoritative for class, tier, region, replicas and service-to-service dependencies; monitoring for team,
SLA and service-to-datastore dependencies; stale records are dropped together with every relation to them.
A failure is named by a CMDB datacenter (e.g. "dc-fra") and passed explicitly to the failure methods.
"""
import json
import re

SERVICE_CLASSES = {"service", "customer_facing_service"}
COMPONENT_CLASSES = SERVICE_CLASSES | {"database", "queue"}


def mon_id(ci_name):
    """CMDB name -> monitoring component ID (the identity rule linking the two exports)."""
    return "mon:" + re.sub(r"_(svc|db|q)$", "", ci_name).replace("_", "-")


class Infra3:
    def __init__(self, cmdb="cmdb.json", monitoring="monitoring.json", tables="mapping_tables.json", size=None):
        cm = json.load(open(cmdb))["records"]
        mo = json.load(open(monitoring))
        mon = {r["component"]: r for r in mo["records"]}
        self.sla_availability = {s["sla_id"]: s["availability"] for s in mo["slas"]}
        crosswalk = json.load(open(tables))  # {size: tables}; pass size unless the file holds one graph's tables
        crosswalk = crosswalk[str(size)] if size is not None else next(iter(crosswalk.values()))
        self.team_of_owner_group = crosswalk["owner_group_to_team"]
        self.zone_of_datacenter = crosswalk["datacenter_to_zone"]

        # ---- identity and stale records
        self.names = {}                      # any identifier -> CI ID
        self.stale = set()                   # CI IDs of stale components
        self.record = {}                     # CI ID -> (cmdb record, monitoring record)
        for r in cm:
            m = mon[mon_id(r["ci_name"])]
            ci = r["ci_id"]
            self.record[ci] = (r, m)
            for name in [ci, r["ci_name"], m["component"], m["display_name"]] + m["aliases"]:
                self.names[name] = ci
            if r["status"] == "decommissioned" or m["status"] == "retired":
                self.stale.add(ci)

        # ---- resolved facts for live components (authoritative source per fact)
        self.cls, self.tier, self.region, self.replica_of, self.team, self.sla, self.deps = {}, {}, {}, {}, {}, {}, {}
        for ci, (r, m) in self.record.items():
            if ci in self.stale:
                continue
            self.cls[ci], self.tier[ci], self.region[ci] = r["ci_class"], r["tier"], r["site"]   # CMDB
            if r["replica_of_ci"] and r["replica_of_ci"] not in self.stale:
                self.replica_of[ci] = r["replica_of_ci"]
            self.team[ci], self.sla[ci] = m["team"], m["sla"]                                          # monitoring
            targets = list(r["depends_on_ci"]) + [self.names[u] for u in m["upstream"]]
            self.deps[ci] = sorted({t for t in targets if t not in self.stale})

    # ---- lookup
    def resolve(self, name):
        """CI ID for any identifier used by either export (KeyError if unknown)."""
        return self.names[name]

    def names_of(self, ci):
        return sorted(k for k, v in self.names.items() if v == ci)

    def components(self, *classes):
        classes = set(classes) or COMPONENT_CLASSES
        return sorted(ci for ci, c in self.cls.items() if c in classes)

    def services(self):
        return self.components(*SERVICE_CLASSES)

    def is_primary(self, ci):
        return ci in self.cls and ci not in self.replica_of

    def primaries(self, *classes):
        return [ci for ci in self.components(*classes) if self.is_primary(ci)]

    # ---- definitions (same as Experiment 2)
    def transitive_dependencies(self, ci):
        seen, stack = set(), list(self.deps.get(ci, []))
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.deps.get(n, []))
        return seen

    def replica_group(self, ci):
        links = {}
        for a, b in self.replica_of.items():
            links.setdefault(a, set()).add(b)
            links.setdefault(b, set()).add(a)
        seen, stack = {ci}, [ci]
        while stack:
            for m in links.get(stack.pop(), ()):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        return seen

    def footprint(self, ci):
        return {self.region[m] for m in self.replica_group(ci)}

    def is_lost(self, ci, datacenter):
        if self.cls.get(ci) == "database":  # a database needs at least two footprint regions outside the failed one
            return len(self.footprint(ci) - {datacenter}) < 2
        return self.footprint(ci) == {datacenter}

    def is_down(self, ci, datacenter):
        if self.cls.get(ci) not in SERVICE_CLASSES:
            return False
        return self.is_lost(ci, datacenter) or any(self.is_lost(d, datacenter) for d in self.transitive_dependencies(ci))

    def down_services(self, datacenter, primary_only=False):
        down = [s for s in self.services() if self.is_down(s, datacenter)]
        return [s for s in down if self.is_primary(s)] if primary_only else down

    def breached_slas(self, datacenter):
        return sorted({self.sla[s] for s in self.down_services(datacenter) if self.sla.get(s)})
