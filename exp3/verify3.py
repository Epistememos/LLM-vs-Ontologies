"""verify3.py - check both artifacts against the hidden key and the canonical ground truth (test-only; reads hidden/).

(A) mapping diff: every identifier in the key resolves to the right CMDB CI in B3's glue and C3's materialized
    graph, stale records resolve to no live entity, and both crosswalks equal the key's team and region tables.
(B) facts and definitions: class, tier, region, team, SLA, dependencies, replicas, primary, footprint, and for
    every datacenter failure the lost components, down services and breached SLAs equal truth3.py.
Run (from the repo root): python exp3/verify3.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import truth3  # noqa: E402
from glue import Infra3  # noqa: E402
from rules3 import EX, load_materialized  # noqa: E402

loc = lambda u: str(u).removeprefix(str(EX))
CLASS = {"Service": "service", "CustomerFacingService": "customer_facing_service", "Database": "database", "Queue": "queue"}


def from_truth(n):
    t = truth3.truth_for(n)
    _, key, _, _ = truth3.load(n)
    ent = key["entities"]
    ci = lambda x: ent[x]["cmdb"]
    dc = {r: v["cmdb"] for r, v in key["regions"].items()}
    team = {k: v["monitoring"] for k, v in key["teams"].items()}
    comps = t.ids(*truth3.truth.INFRA_TYPES)
    f = {"class": {ci(x): CLASS[t.nodes[x]["type"]] for x in comps},
         "tier": {ci(x): t.tier(x) for x in comps if t.tier(x)},
         "region": {ci(x): dc[t.region[x]] for x in comps},
         "team": {ci(x): team[t.owner[x]] for x in comps},
         "sla": {ci(x): key["slas"][t.sla[x]] for x in comps if x in t.sla},
         "deps": {ci(x): sorted(ci(d) for d in t.dep.successors(x)) for x in comps if list(t.dep.successors(x))},
         "replica_of": {ci(s): ci(o) for s, r, o in t.edges if r == "replicaOf"},
         "primary": sorted(ci(x) for x in t.primaries(*truth3.truth.INFRA_TYPES)),
         "footprint": {ci(x): sorted(dc[r] for r in t.footprint(x)) for x in comps}}
    for r in t.ids("Region"):
        f[f"lost@{dc[r]}"] = sorted(ci(x) for x in comps if t.lost(x, r))
        f[f"down@{dc[r]}"] = sorted(ci(s) for s in t.down_services(r))
        f[f"breached@{dc[r]}"] = sorted(key["slas"][s] for s in t.breached_slas(r))
    return f, key


def from_glue(n, dcs):
    g = Infra3(HERE / "data" / f"cmdb_{n}.json", HERE / "data" / f"monitoring_{n}.json", HERE / "mapping_tables.json", n)
    f = {"class": dict(g.cls), "tier": {k: v for k, v in g.tier.items() if v}, "region": dict(g.region),
         "team": dict(g.team), "sla": {k: v for k, v in g.sla.items() if v},
         "deps": {k: v for k, v in g.deps.items() if v}, "replica_of": dict(g.replica_of),
         "primary": sorted(g.primaries()), "footprint": {x: sorted(g.footprint(x)) for x in g.components()}}
    for d in dcs:
        f[f"lost@{d}"] = sorted(x for x in g.components() if g.is_lost(x, d))
        f[f"down@{d}"] = sorted(g.down_services(d))
        f[f"breached@{d}"] = g.breached_slas(d)
    names = {k: v for k, v in g.names.items() if v not in g.stale}
    return f, names, g.team_of_owner_group, g.zone_of_datacenter


def from_rules(n, dcs):
    g, _ = load_materialized(n)
    q = lambda s: [tuple(loc(v) if not hasattr(v, "toPython") or not isinstance(v.toPython(), (int,)) else v.toPython()
                         for v in row) for row in g.query(s)]
    pairs = lambda p: q(f"SELECT ?a ?b WHERE {{ ?a <{EX[p]}> ?b }}")
    grouped = lambda p: {a: sorted(b for x, b in pairs(p) if x == a) for a, _ in pairs(p)}
    single = lambda p: {a: b for a, b in pairs(p)}
    cls = {}
    for c in CLASS:
        for (x,) in q(f"SELECT ?x WHERE {{ ?x a <{EX[c]}> }}"):
            if c == "CustomerFacingService" or x not in cls:
                cls[x] = CLASS[c]
    f = {"class": cls, "tier": {a: int(b) for a, b in pairs("tier")}, "region": single("deployedIn"),
         "team": single("ownedBy"), "sla": single("hasSLA"), "deps": grouped("dependsOn"),
         "replica_of": single("replicaOf"), "primary": sorted(x for (x,) in q(f"SELECT ?x WHERE {{ ?x a <{EX.Primary}> }}")),
         "footprint": grouped("hasFootprintRegion")}
    for d in dcs:
        f[f"lost@{d}"] = sorted(x for x, r in pairs("lostIn") if r == d)
        f[f"down@{d}"] = sorted(x for x, r in pairs("downIn") if r == d)
        f[f"breached@{d}"] = sorted(x for x, r in pairs("breachedIn") if r == d)
    names = {str(b): a for a, b in pairs("name")}
    teams = {str(b): a for a, b in pairs("cmdbOwnerGroup")}
    zones = {a: str(b) for a, b in pairs("monitoringZone")}
    return f, names, teams, zones


def key_names(key):
    out = {}
    for e in key["entities"].values():
        for nm in [e["cmdb"], e["cmdb_name"], e["monitoring"], e["display"]] + e["aliases"]:
            out[nm] = e["cmdb"]
    return out


def main():
    ok, rows = True, []
    for n in (20, 100, 500):
        ref, key = from_truth(n)
        dcs = [v["cmdb"] for v in key["regions"].values()]
        kn = key_names(key)
        kteam = {v["cmdb"]: v["monitoring"] for v in key["teams"].values()}
        kzone = {v["cmdb"]: v["monitoring"] for v in key["regions"].values()}
        stale_ids = {g["cmdb"] for g in key["stale"]}
        for label, (facts, names, teams, zones) in (("B3 glue", from_glue(n, dcs)), ("C3 rules", from_rules(n, dcs))):
            mapping = {"names == key": names == kn, "no stale entity": not (set(names.values()) & stale_ids),
                       "team crosswalk == key": teams == kteam, "region crosswalk == key": zones == kzone}
            bad = [k for k in ref if facts.get(k) != ref[k]]
            ok &= all(mapping.values()) and not bad
            rows.append((n, label, all(mapping.values()) or [k for k, v in mapping.items() if not v],
                         f"{len(ref) - len(bad)}/{len(ref)}", bad[:4]))
    print(f"{'graph':>5}  {'artifact':9} {'mapping vs key':16} {'facts+definitions vs truth3':28} mismatches")
    for n, label, m, frac, bad in rows:
        print(f"{n:>5}  {label:9} {'OK' if m is True else str(m):16} {frac:28} {bad or ''}")
    print("\nALL MATCH" if ok else "\nMISMATCH")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
