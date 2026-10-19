"""truth3.py - Experiment 3 ground truth and the cross-export consistency check.

Ground truth is exp1's NetworkX Truth run on the hidden canonical graph. The consistency check rebuilds the
canonical graph from the two exports, using only the hidden entity-resolution key and the documented
resolution rules (RULES below), and requires an exact match. Variants of the rebuild that break one rule
(drop monitoring data, keep stale records, trust the wrong source) measure how much each difficulty knob bites.
Run (from the repo root): python exp3/truth3.py
"""
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import truth  # noqa: E402  exp1 ground truth, used as a library

DATA3, HIDDEN = HERE / "data", HERE / "data" / "hidden"
SIZES = (20, 100, 500)
TYPE = {"customer_facing_service": "CustomerFacingService", "service": "Service", "database": "Database", "queue": "Queue"}

# The resolution rules every condition is given, word for word (docs and PREREG_EXP3.md).
RULES = """Resolution rules for the two exports.
- Authority: the CMDB export is authoritative for component class, tier, region (datacenter), replicas
  (replica_of_ci) and service-to-service dependencies (depends_on_ci). The monitoring export is authoritative for
  team ownership (team), SLAs (sla) and service-to-datastore dependencies (upstream). When the two exports disagree
  on a fact, use the authoritative source.
- Stale records: a record whose status is "decommissioned" (CMDB) or "retired" (monitoring) is stale. The component
  no longer exists: ignore it in both exports, together with every relation that refers to it."""


def load(n):
    rd = lambda p: json.loads(p.read_text())
    return rd(HIDDEN / f"graph_{n}.json"), rd(HIDDEN / f"er_key_{n}.json"), \
        rd(DATA3 / f"cmdb_{n}.json"), rd(DATA3 / f"monitoring_{n}.json")


def truth_for(n, graph=None):
    """exp1 Truth over the canonical graph, or over a variant graph dict."""
    if graph is None:
        truth.DATA = HIDDEN
        return truth.Truth(n)
    tmp = HIDDEN / "variants"
    tmp.mkdir(exist_ok=True)
    (tmp / f"graph_{n}.json").write_bytes(json.dumps(graph).encode())
    truth.DATA = tmp
    t = truth.Truth(n)
    truth.DATA = HIDDEN
    return t


def resolvers(key):
    """Every identifier either export uses -> canonical ID (built from the hidden key only)."""
    ids = {}
    for canon, e in key["entities"].items():
        for name in [e["cmdb"], e["monitoring"], e["display"]] + e["aliases"]:
            assert ids.setdefault(name, canon) == canon, f"identifier {name} is ambiguous"
    team = {v["cmdb"]: t for t, v in key["teams"].items()} | {v["monitoring"]: t for t, v in key["teams"].items()}
    region = {v["cmdb"]: r for r, v in key["regions"].items()} | {v["monitoring"]: r for r, v in key["regions"].items()}
    sla = {v: s for s, v in key["slas"].items()}
    return ids, team, region, sla


def norm_name(x):
    """Name normalization used by the 'name_similarity' wrong reading (a naive merger, not the real mapping)."""
    x = re.sub(r"^mon:", "", x.lower())
    x = re.sub(r"_(svc|db|q)$", "", x)
    words = [w for w in re.split(r"[-_ ]+", x) if w and w not in ("service", "db", "queue", "svc", "q", "v2")
             and not re.fullmatch(r"r\d+", w)]
    return " ".join(words)


def fuzzy_matcher(cmdb):
    """Map any monitoring identifier to the CMDB ci_id with the most similar normalized name."""
    names = sorted((norm_name(r["ci_name"]), r["ci_id"]) for r in cmdb["records"])
    def match(x):
        nx_ = norm_name(x)
        return max(names, key=lambda nc: (difflib.SequenceMatcher(None, nx_, nc[0]).ratio(), nc[1]))[1]
    return match


def rebuild(n, variant=None):
    """Canonical graph rebuilt from the exports.
    variant: None | 'cmdb_only' | 'keep_stale' | 'wrong_authority' | 'name_similarity'."""
    canon, key, cmdb, mon = load(n)
    ids, team, region, sla = resolvers(key)
    stale_ids = {g["cmdb"] for g in key["stale"]} | {g["monitoring"] for g in key["stale"]}
    flagged = {r["ci_id"] for r in cmdb["records"] if r["status"] == "decommissioned"} | \
              {r["component"] for r in mon["records"] if r["status"] == "retired"}
    ghost = {}  # stale ID -> pseudo canonical ID (only kept in the 'keep_stale' variant)
    for i, g in enumerate(key["stale"]):
        ghost[g["cmdb"]] = ghost[g["monitoring"]] = f"stale-{i + 1}"
    resolve = lambda x: ids.get(x) or ghost[x]
    keep = lambda x: variant == "keep_stale" or x not in stale_ids

    nodes = {v["id"]: v for v in canon["nodes"] if v["type"] not in TYPE.values()}  # teams, regions, SLAs
    edges = set()
    mon_by = {r["component"]: r for r in mon["records"]}
    if variant == "name_similarity":  # monitoring records and references matched to CMDB records by name only
        match = fuzzy_matcher(cmdb)
        mon_of = {match(m["component"]): m for m in mon["records"]}
    for r in cmdb["records"]:
        if not keep(r["ci_id"]):
            continue
        x = resolve(r["ci_id"])
        nodes[x] = {"id": x, "type": TYPE[r["ci_class"]]} | ({"tier": r["tier"]} if r["tier"] else {})
        if variant == "name_similarity":
            m = mon_of.get(r["ci_id"], {"team": None, "sla": None, "upstream": [], "zone": None})
        else:
            m = mon_by[key["entities"][x]["monitoring"] if x in key["entities"] else
                       next(g["monitoring"] for g in key["stale"] if g["cmdb"] == r["ci_id"])]
        reg = region[m["zone"]] if variant == "wrong_authority" else region[r["datacenter"]]
        own = team[r["owner_group"]] if variant == "wrong_authority" or m["team"] is None else team[m["team"]]
        edges |= {(x, "deployedIn", reg), (x, "ownedBy", own)}
        if r["replica_of_ci"]:
            edges.add((x, "replicaOf", resolve(r["replica_of_ci"])))
        edges |= {(x, "dependsOn", resolve(d)) for d in r["depends_on_ci"] if keep(d)}
        if m["sla"]:
            edges.add((x, "hasSLA", sla[m["sla"]]))
        if variant == "name_similarity":
            targets = {match(u) for u in m["upstream"]}
            edges |= {(x, "dependsOn", resolve(t)) for t in targets if keep(t)}
        elif variant != "cmdb_only":
            edges |= {(x, "dependsOn", resolve(u)) for u in m["upstream"]}
    return {"nodes": sorted(nodes.values(), key=lambda v: v["id"]), "edges": sorted(list(e) for e in edges)}, flagged, stale_ids


def verify(n):
    """Consistency checks; returns a dict of named booleans."""
    canon, key, cmdb, mon = load(n)
    graph, flagged, stale_ids = rebuild(n)
    resolvers(key)  # raises if any identifier is ambiguous
    ent = key["entities"]
    region_of = {s: o for s, r, o in canon["edges"] if r == "deployedIn"}
    owner_of = {s: o for s, r, o in canon["edges"] if r == "ownedBy"}
    cmdb_by = {r["ci_id"]: r for r in cmdb["records"]}
    mon_by = {r["component"]: r for r in mon["records"]}
    zone = lambda x: mon_by[ent[x]["monitoring"]]["zone"]
    og = lambda x: cmdb_by[ent[x]["cmdb"]]["owner_group"]
    return {
        "rebuild from both exports == canonical graph": graph == {"nodes": canon["nodes"], "edges": sorted(canon["edges"])},
        "every stale flag is a key ghost and vice versa": flagged == {g[g["flagged_in"]] for g in key["stale"]},
        "each ghost looks live in the other export": all(
            (cmdb_by[g["cmdb"]]["status"] == "operational") if g["flagged_in"] == "monitoring" else
            (mon_by[g["monitoring"]]["status"] == "active") for g in key["stale"]),
        "each ghost has live dependents": all(
            sum(g["cmdb"] in cmdb_by[d]["depends_on_ci"] for d in g["dependents"]) == 2 for g in key["stale"]),
        "region conflicts: monitoring zone disagrees": all(
            zone(x) != key["regions"][region_of[x]]["monitoring"] for x in key["planted"]["region_conflicts"]),
        "team conflicts: CMDB owner group disagrees": all(
            og(x) != key["teams"][owner_of[x]]["cmdb"] for x in key["planted"]["team_conflicts"]),
        "no conflicts outside the planted ones": sum(zone(x) != key["regions"][region_of[x]]["monitoring"] for x in ent)
            == len(key["planted"]["region_conflicts"]) and
            sum(og(x) != key["teams"][owner_of[x]]["cmdb"] for x in ent) == len(key["planted"]["team_conflicts"]),
    }


def stats(n):
    canon, key, cmdb, mon = load(n)
    types = Counter(v["type"] for v in canon["nodes"])
    refs = [u for r in mon["records"] for u in r["upstream"]]
    aliased = sum(not u.startswith("mon:") for u in refs)
    return {"canonical nodes": len(canon["nodes"]),
            "services (cust.-facing)": f"{types['Service'] + types['CustomerFacingService']} ({types['CustomerFacingService']})",
            "databases / queues": f"{types['Database']} / {types['Queue']}",
            "regions / teams / SLAs": f"{types['Region']} / {types['Team']} / {types['SLA']}",
            "CMDB records / monitoring records": f"{len(cmdb['records'])} / {len(mon['records'])}",
            "svc->svc deps (CMDB only)": sum(len(r["depends_on_ci"]) for r in cmdb["records"]) -
                sum(len(g["dependents"]) for g in key["stale"]),
            "svc->datastore deps (monitoring only)": len(refs),
            "monitoring refs written as alias": f"{aliased}/{len(refs)}",
            "stale ghosts (dependents)": f"{len(key['stale'])} ({sum(len(g['dependents']) for g in key['stale'])})",
            "region / team conflicts": f"{len(key['planted']['region_conflicts'])} / {len(key['planted']['team_conflicts'])}"}


if __name__ == "__main__":
    import pandas as pd
    ok = True
    for n in SIZES:
        checks = verify(n)
        ok &= all(checks.values())
        print(f"graph {n}:", "  ".join(f"[{'PASS' if v else 'FAIL'}] {k}" for k, v in checks.items()))
    print("\n", pd.DataFrame({n: stats(n) for n in SIZES}).to_string())
    print("\nALL CONSISTENT" if ok else "\nINCONSISTENT")
