"""gen3.py - Experiment 3 data: two conflicting source exports derived from one hidden canonical graph.

    hidden/graph_{n}.json   canonical graph (exp1 format; read only by truth3.py and the scorer)
    hidden/er_key_{n}.json  entity-resolution key (read only by truth3.py and the scorer)
    cmdb_{n}.json           CMDB-style export: CI IDs, underscore names, datacenters, CI owner groups
    monitoring_{n}.json     monitoring export: mon: IDs, display names, aliases, zones, teams, SLAs

The canonical topology comes from exp1's generator (imported, unmodified) with new seeds.
Run (from the repo root): python exp3/gen3.py
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gen  # noqa: E402  exp1 generator, used as a library

DATA3 = HERE / "data"
HIDDEN = DATA3 / "hidden"
# One graph seed per size scale (about 23 / 121 / 559 nodes): the first seed at or after 3020 / 3100 / 3500 for
# which exp1's unmodified generator can plant its cases (3020 could not; chosen before any data was inspected).
SEEDS = {20: 3021, 100: 3100, 500: 3500}

# Difficulty knobs, fixed before any run and recorded in PREREG_EXP3.md. Changed only by the pre-registered
# pilot rule (raise, re-pilot, at most 2 rounds, each logged).
DIFFICULTY = {
    "alias_rate": 0.5,                          # share of monitoring cross-references written as an alias
    "stale": {20: 2, 100: 3, 500: 5},           # ghost services flagged stale in one source, with live dependents
    "conflicts": {20: 2, 100: 4, 500: 8},       # planted region conflicts and, separately, team conflicts
}

COMP = {"CustomerFacingService": "customer_facing_service", "Service": "service", "Database": "database",
        "Queue": "queue"}
SUFFIX = {"customer_facing_service": ("svc", "Service"), "service": ("svc", "Service"),
          "database": ("db", "DB"), "queue": ("q", "Queue")}
WORDS = ("payments orders checkout inventory search auth billing catalog shipping notify pricing fraud ledger "
         "profile cart reviews media gateway reporting session tax refunds loyalty coupons address returns "
         "warehouse routing quotes invoices ratings wishlist identity consent audit export ingest feeds metrics").split()
TEAM_WORDS = ("platform commerce growth trust data infra mobile web core edge storage risk ops finance "
              "search fulfil partner content insights identity").split()
DATACENTERS = ["dc-fra", "dc-iad", "dc-sin", "dc-sfo", "dc-ams"]
ZONES = ["eu-central-1", "us-east-1", "ap-southeast-1", "us-west-2", "eu-west-1"]
SLA_WORDS = ["GOLD", "SILVER", "BRONZE", "PLATINUM"]


def names_for(comps, nodes, edges, rng):
    """Unique base name per component; a replica shares its primary's base name plus '-replica-k'."""
    primary_of = {s: o for s, r, o in edges if r == "replicaOf"}
    pairs = rng.sample([(a, b) for a in WORDS for b in WORDS if a != b], len(comps))
    base, k = {}, 0
    for x in comps:
        if x not in primary_of:
            base[x] = f"{pairs[k][0]}-{pairs[k][1]}"
            k += 1
    for x in comps:
        if x in primary_of:
            sibs = sorted(s for s, p in primary_of.items() if p == primary_of[x])
            base[x] = f"{base[primary_of[x]]}-replica-{sibs.index(x) + 1}"
    return base


def build(n):
    rng = random.Random(SEEDS[n] + 1)
    nodes, edges, planted = gen.build(gen.SIZES[n] | {"seed": SEEDS[n]})
    edges = sorted(edges)
    comps = sorted(k for k, v in nodes.items() if v["type"] in COMP)
    rel = lambda r: {s: o for s, rr, o in edges if rr == r}
    region, owner, sla, primary_of = rel("deployedIn"), rel("ownedBy"), rel("hasSLA"), rel("replicaOf")
    deps = {x: sorted(o for s, r, o in edges if r == "dependsOn" and s == x) for x in comps}

    # ---- identifiers in each source
    base = names_for(comps, nodes, edges, rng)
    ci_nums = rng.sample(range(1000, 99999), len(comps) + 20)
    ent = {}
    for i, x in enumerate(comps):
        cls = COMP[nodes[x]["type"]]
        short, word = SUFFIX[cls]
        words = base[x].split("-")
        abbrev = "-".join(w[:3] for w in words if not w.isdigit() and w != "replica")
        ver = f"-r{base[x].rsplit('-', 1)[1]}" if "replica" in base[x] else ""
        ent[x] = {"cmdb": f"CI-{ci_nums[i]:05d}", "cmdb_name": base[x].replace("-", "_") + f"_{short}",
                  "monitoring": f"mon:{base[x]}", "display": " ".join(w.capitalize() for w in words) + f" {word}",
                  "aliases": [f"{abbrev}-{short}-v2{ver}"], "class": cls}
    teams = sorted(k for k, v in nodes.items() if v["type"] == "Team")
    team_words = rng.sample(TEAM_WORDS, len(teams))
    team_key = {t: {"cmdb": f"OG-{i + 11:02d}", "monitoring": f"team-{w}"} for i, (t, w) in enumerate(zip(teams, team_words))}
    regions = sorted(k for k, v in nodes.items() if v["type"] == "Region")
    region_key = {r: {"cmdb": DATACENTERS[i], "monitoring": ZONES[i]} for i, r in enumerate(regions)}
    slas = sorted(k for k, v in nodes.items() if v["type"] == "SLA")
    sla_key = {s: f"SLA-{rng.choice(SLA_WORDS)}-{i + 1:02d}" for i, s in enumerate(slas)}

    services = [x for x in comps if COMP[nodes[x]["type"]] in ("service", "customer_facing_service")]
    datastores = [x for x in comps if x not in services]
    ref = lambda x: rng.choice([ent[x]["display"]] + ent[x]["aliases"]) if rng.random() < DIFFICULTY["alias_rate"] \
        else ent[x]["monitoring"]

    # ---- planted contradictions: the non-authoritative source gets a wrong value
    region_conflicts = sorted(rng.sample(services, DIFFICULTY["conflicts"][n]))
    team_conflicts = sorted(rng.sample(comps, DIFFICULTY["conflicts"][n]))

    cmdb, mon = [], []
    for x in comps:
        og = team_key[owner[x]]["cmdb"]
        if x in team_conflicts:
            og = rng.choice([v["cmdb"] for t, v in team_key.items() if t != owner[x]])
        cmdb.append({"ci_id": ent[x]["cmdb"], "ci_name": ent[x]["cmdb_name"], "ci_class": ent[x]["class"],
                     "tier": nodes[x].get("tier"), "status": "operational", "owner_group": og,
                     "datacenter": region_key[region[x]]["cmdb"],
                     "replica_of_ci": ent[primary_of[x]]["cmdb"] if x in primary_of else None,
                     "depends_on_ci": [ent[d]["cmdb"] for d in deps[x] if d in services]})
        zone = region_key[region[x]]["monitoring"]
        if x in region_conflicts:
            zone = rng.choice([v["monitoring"] for r, v in region_key.items() if r != region[x]])
        mon.append({"component": ent[x]["monitoring"], "display_name": ent[x]["display"], "aliases": ent[x]["aliases"],
                    "kind": "datastore" if x in datastores else "service", "status": "active",
                    "team": team_key[owner[x]]["monitoring"], "zone": zone,
                    "sla": sla_key[sla[x]] if x in sla else None,
                    "upstream": [ref(d) for d in deps[x] if d in datastores]})

    # ---- stale ghosts: flagged stale in exactly one source, look live in the other, and have live dependents
    stale = []
    for i in range(DIFFICULTY["stale"][n]):
        w = f"legacy-{rng.choice(WORDS)}-{i + 1}"
        g = {"cmdb": f"CI-{ci_nums[len(comps) + i]:05d}", "monitoring": f"mon:{w}", "flagged_in": "cmdb" if i % 2 else "monitoring"}
        stale.append(g)
        dc = rng.choice(DATACENTERS[:len(regions)])
        cmdb.append({"ci_id": g["cmdb"], "ci_name": w.replace("-", "_") + "_svc", "ci_class": "service",
                     "tier": rng.choice([1, 2, 3]), "status": "decommissioned" if g["flagged_in"] == "cmdb" else "operational",
                     "owner_group": rng.choice(list(team_key.values()))["cmdb"], "datacenter": dc,
                     "replica_of_ci": None, "depends_on_ci": []})
        mon.append({"component": g["monitoring"], "display_name": w.replace("-", " ").title() + " Service", "aliases": [],
                    "kind": "service", "status": "retired" if g["flagged_in"] == "monitoring" else "active",
                    "team": rng.choice(list(team_key.values()))["monitoring"],
                    "zone": region_key[regions[DATACENTERS.index(dc)]]["monitoring"], "sla": None, "upstream": []})
        g["dependents"] = sorted(ent[s]["cmdb"] for s in rng.sample([s for s in services if s not in primary_of], 2))
        for rec in cmdb:
            if rec["ci_id"] in g["dependents"]:
                rec["depends_on_ci"].append(g["cmdb"])

    rng.shuffle(cmdb)
    rng.shuffle(mon)
    sla_catalog = [{"sla_id": sla_key[s], "availability": nodes[s]["availability"]} for s in slas]
    key = {"entities": ent, "teams": team_key, "regions": region_key, "slas": sla_key, "stale": stale,
           "planted": {"region_conflicts": region_conflicts, "team_conflicts": team_conflicts}}
    graph = {"nodes": sorted(nodes.values(), key=lambda v: v["id"]), "edges": [list(e) for e in edges]}
    return graph, key, {"export": "cmdb", "records": cmdb}, {"export": "monitoring", "records": mon, "slas": sla_catalog}


def write(n):
    HIDDEN.mkdir(parents=True, exist_ok=True)
    graph, key, cmdb, mon = build(n)
    for path, obj in ((HIDDEN / f"graph_{n}.json", graph), (HIDDEN / f"er_key_{n}.json", key),
                      (DATA3 / f"cmdb_{n}.json", cmdb), (DATA3 / f"monitoring_{n}.json", mon)):
        path.write_bytes(json.dumps(obj, indent=1).encode())  # LF line endings on every platform
    return graph, key, cmdb, mon


if __name__ == "__main__":
    for n in SEEDS:
        g, k, c, m = write(n)
        print(f"  size {n}: {len(g['nodes'])} canonical nodes | cmdb {len(c['records'])} records | "
              f"monitoring {len(m['records'])} records | stale {len(k['stale'])}")
