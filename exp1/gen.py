"""gen.py - seeded synthetic infrastructure graph.

Writes, per size: data/graph_{n}.json (raw data), data/graph_{n}.ttl (same graph as RDF
instances), data/planted_{n}.json (manifest of deliberately planted cases).
Run: python gen.py   (generates all sizes and verifies JSON == RDF)
"""
import json
import random
from decimal import Decimal
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace

EX = Namespace("http://example.org/br#")
DATA = Path(__file__).parent / "data"

# Node budget ~= regions + teams + cfs + svc + db + q + slas(cfs + extra) + replicas
SIZES = {
    20: dict(seed=20, regions=2, teams=2, cfs=3, svc=4, db=3, q=1, extra_slas=0, violations=1),
    100: dict(seed=100, regions=3, teams=5, cfs=10, svc=35, db=15, q=5, extra_slas=4, violations=3),
    500: dict(seed=500, regions=5, teams=15, cfs=40, svc=190, db=70, q=25, extra_slas=15, violations=8),
}
REPLICA_PROB = {"CustomerFacingService": 0.6, "Service": 0.35, "Database": 0.7}
CROSS_PROB = 0.75  # given a replica, probability it lives in another region
LOCALITY = 0.85  # probability a node is deployed in the region of one of its dependents


def wsample(rng, items, weights, k):
    """Weighted sample without replacement."""
    items, weights, out = list(items), list(weights), []
    for _ in range(min(k, len(items))):
        i = rng.choices(range(len(items)), weights)[0]
        out.append(items.pop(i))
        weights.pop(i)
    return out


def build(cfg):
    rng = random.Random(cfg["seed"])
    nodes, edges = {}, set()
    svc_ids = iter(f"svc-{i:03d}" for i in rng.sample(range(1, 1000), 999))
    db_ids = iter(f"db-{i:03d}" for i in rng.sample(range(1, 1000), 999))
    sla_ids = iter(f"sla-{i:02d}" for i in rng.sample(range(1, 100), 99))

    def add(nid, typ, **attrs):
        nodes[nid] = dict(id=nid, type=typ, **attrs)
        return nid

    regions = [add(f"reg-{i + 1}", "Region") for i in range(cfg["regions"])]
    teams = [add(f"team-{i + 1:02d}", "Team") for i in range(cfg["teams"])]
    cfs = [add(next(svc_ids), "CustomerFacingService", tier=rng.choices([1, 2], [0.7, 0.3])[0])
           for _ in range(cfg["cfs"])]
    svc = [add(next(svc_ids), "Service", tier=rng.choices([1, 2, 3], [0.3, 0.4, 0.3])[0])
           for _ in range(cfg["svc"])]
    dbs = [add(next(db_ids), "Database") for _ in range(cfg["db"])]
    qs = [add(f"q-{i + 1:03d}", "Queue") for i in range(cfg["q"])]
    tier = lambda n: nodes[n].get("tier")

    # Skewed fan-out: a few hub services (from the deep half) and hub databases get large weights.
    hub_svc = set(rng.sample(svc[len(svc) // 2:], max(1, round(0.06 * len(svc)))))
    hub_db = set(rng.sample(dbs, max(1, round(0.1 * len(dbs)))))
    w_svc = {s: 12 if s in hub_svc else 1 for s in svc}
    w_data = {d: 8 if d in hub_db else 1 for d in dbs} | {q: 1 for q in qs}

    def ok(src, dst):  # generation never creates a Tier-1 -> Tier-3 edge; those are planted
        return not (tier(src) == 1 and tier(dst) == 3)

    # Layered DAG: cfs -> internal services (only to later ones in `svc` order) -> databases/queues
    for c in cfs:
        cand = [s for s in svc if ok(c, s)]
        for s in wsample(rng, cand, [w_svc[s] for s in cand], rng.randint(1, 3)):
            edges.add((c, "dependsOn", s))
        if rng.random() < 0.3:
            edges.add((c, "dependsOn", rng.choice(dbs)))
    for i, s in enumerate(svc):
        cand = [t for t in svc[i + 1:] if ok(s, t)]
        picked = wsample(rng, cand, [w_svc[t] for t in cand], rng.randint(0, 3))
        data = wsample(rng, list(w_data), list(w_data.values()), rng.randint(0 if picked else 1, 2))
        for t in picked + data:
            edges.add((s, "dependsOn", t))

    for n in cfs + svc + dbs + qs:
        edges.add((n, "ownedBy", rng.choice(teams)))
    # Region locality: walking the DAG top-down, a node usually shares a dependent's region.
    region = {}
    for n in cfs + svc + dbs + qs:
        ups = sorted(a for (a, r, b) in edges if b == n and r == "dependsOn")
        region[n] = region[rng.choice(ups)] if ups and rng.random() < LOCALITY else rng.choice(regions)

    # SLAs: one per customer-facing service, plus shared ones for some Tier-1 internal services.
    for c in cfs:
        edges.add((c, "hasSLA", add(next(sla_ids), "SLA", availability=99.99 if tier(c) == 1 else 99.9)))
    extra = [add(next(sla_ids), "SLA", availability=rng.choice([99.9, 99.95, 99.99]))
             for _ in range(cfg["extra_slas"])]
    for s in svc:
        if extra and tier(s) == 1 and rng.random() < 0.6:
            edges.add((s, "hasSLA", rng.choice(extra)))

    # ---- Planted cases -------------------------------------------------------------------
    rp, others = regions[0], regions[1:]
    order = {n: i for i, n in enumerate(cfs + svc)}
    deps = lambda n: [d for (a, r, d) in edges if a == n and r == "dependsOn"]
    dependents = lambda n: [a for (a, r, d) in edges if d == n and r == "dependsOn"]
    planted = {"failure_region": rp}

    # 1. Tier-1 -> Tier-3 violations (respecting DAG order).
    cand = [(a, b) for a in cfs + svc for b in svc
            if tier(a) == 1 and tier(b) == 3 and order[a] < order[b] and (a, "dependsOn", b) not in edges]
    assert len(cand) >= cfg["violations"], "not enough violation candidates; change seed"
    planted["violations"] = sorted(rng.sample(cand, cfg["violations"]))
    for a, b in planted["violations"]:
        edges.add((a, "dependsOn", b))

    # Critical closure: hubs and everything they transitively depend on are always replicated
    # cross-region (otherwise any single loss under a hub takes down most of the graph).
    critical, stack = set(), list(hub_svc | hub_db)
    while stack:
        n = stack.pop()
        if n not in critical:
            critical.add(n)
            stack += deps(n)

    # 2. Deep loss: cfs -> s1 -> s2 -> db, db only in Rp, the chain itself outside Rp.
    chains = [(c, s1, s2, d) for c in cfs for s1 in deps(c) if s1 in svc for s2 in deps(s1)
              if s2 in svc for d in deps(s2) if d in dbs]
    assert chains, "no deep chain; change seed"
    c, s1, s2, d = rng.choice([ch for ch in chains if ch[3] not in critical] or chains)
    region[d] = rp
    for n in (c, s1, s2):
        region[n] = rng.choice(others)
    forced = {d: "none"}
    planted["deep_chain"] = [c, s1, s2, d]

    # 3. A database lost in Rp whose direct dependents all live elsewhere.
    cand = [x for x in dbs if x != d and dependents(x)]
    d2 = rng.choice([x for x in cand if x not in critical] or cand)
    region[d2], forced[d2] = rp, "none"
    for n in dependents(d2):
        region[n] = rng.choice(others)
    planted["remote_dependents_db"] = d2

    # 4. A service in Rp that survives because it has a replica outside Rp.
    protected = {c, s1, s2, *dependents(d2)}
    s3 = rng.choice([x for x in cfs if x not in protected] or [x for x in svc if x not in protected])
    region[s3], forced[s3] = rp, "cross"
    planted["safe_service"] = s3

    # 5. Customer-facing replica coverage: at least one with none / same-region / cross-region.
    modes = {forced[x] for x in cfs if x in forced}
    free = [x for x in cfs if x not in forced]
    for mode in ("none", "same", "cross"):
        if mode not in modes:
            forced[free.pop(0)] = mode
    planted["forced_replica_modes"] = dict(sorted(forced.items()))

    # ---- Replicas (X replicaOf Y: X is the replica of Y) --------------------------------
    for p in cfs + svc + dbs:
        mode = forced.get(p) or ("cross" if p in critical else None)
        if mode is None:
            mode = "none" if rng.random() >= REPLICA_PROB[nodes[p]["type"]] else (
                "cross" if rng.random() < CROSS_PROB else "same")
        if mode == "none":
            continue
        rid = add(next(db_ids if p in dbs else svc_ids), nodes[p]["type"],
                  **({"tier": tier(p)} if tier(p) else {}))
        region[rid] = region[p] if mode == "same" else rng.choice([r for r in regions if r != region[p]])
        owner = next(o for (a, r, o) in edges if a == p and r == "ownedBy")
        edges |= {(rid, "replicaOf", p), (rid, "ownedBy", owner)}

    edges |= {(n, "deployedIn", r) for n, r in region.items()}
    return nodes, edges, planted


def write(n, nodes, edges, planted):
    DATA.mkdir(exist_ok=True)
    graph = {"nodes": sorted(nodes.values(), key=lambda x: x["id"]),
             "edges": [list(e) for e in sorted(edges)]}
    (DATA / f"graph_{n}.json").write_text(json.dumps(graph, indent=1))
    (DATA / f"planted_{n}.json").write_text(json.dumps(planted, indent=1))

    g = Graph()
    g.bind("ex", EX)
    for v in graph["nodes"]:
        s = EX[v["id"]]
        g.add((s, RDF.type, EX[v["type"]]))
        if "tier" in v:
            g.add((s, EX.tier, Literal(v["tier"])))
        if "availability" in v:
            g.add((s, EX.availability, Literal(Decimal(str(v["availability"])), datatype=XSD.decimal)))
    for a, r, b in graph["edges"]:
        g.add((EX[a], EX[r], EX[b]))
    g.serialize(DATA / f"graph_{n}.ttl", format="turtle")


def verify_roundtrip(n):
    """Parse the TTL back and check it encodes exactly the JSON graph."""
    js = json.loads((DATA / f"graph_{n}.json").read_text())
    j_nodes = {v["id"]: v for v in js["nodes"]}
    j_edges = {tuple(e) for e in js["edges"]}

    g = Graph().parse(DATA / f"graph_{n}.ttl")
    loc = lambda u: str(u).removeprefix(str(EX))
    r_nodes, r_edges = {}, set()
    for s, p, o in g:
        node = r_nodes.setdefault(loc(s), {"id": loc(s)})
        if p == RDF.type:
            node["type"] = loc(o)
        elif p == EX.tier:
            node["tier"] = int(o)
        elif p == EX.availability:
            node["availability"] = float(o)
        else:
            r_edges.add((loc(s), loc(p), loc(o)))
    ok = r_nodes == j_nodes and r_edges == j_edges
    print(f"  roundtrip {n}: {'IDENTICAL' if ok else 'MISMATCH'} "
          f"({len(j_nodes)} nodes, {len(j_edges)} edges, {len(g)} triples)")
    if not ok:
        print("   node diff:", set(r_nodes) ^ set(j_nodes), " edge diff:", list(r_edges ^ j_edges)[:10])
    return ok


if __name__ == "__main__":
    for n, cfg in SIZES.items():
        write(n, *build(cfg))
        assert verify_roundtrip(n)
