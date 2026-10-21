"""rules3.py - C3's rules: resolve the two raw exports into one canonical graph and materialize the definitions.

SPARQL CONSTRUCT rules, applied stratum by stratum, each to a fixpoint; a rule using negation sits in a later
stratum than everything it negates over. The identity rule and the authority and stale rules are the same as in
glue.py (B3). Writes exp3/data/rdf/materialized_{n}.ttl. Run (from the repo root): python exp3/rules3.py
"""
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

HERE = Path(__file__).resolve().parent
EX = Namespace("http://example.org/br#")
SRC = Namespace("http://example.org/src#")
NS = {"ex": EX, "src": SRC, "rdf": RDF, "rdfs": RDFS, "owl": OWL, "xsd": XSD}
ONTOLOGY = HERE / "ontology3.ttl"
E = "http://example.org/br#"
LIVE = "?e ex:fromRecord ?c ."                 # ?e: canonical entity of a live (non-stale) CMDB record ?c
TYPE_CLOSURE = "CONSTRUCT { ?x a ?d } WHERE { ?x a ?c . ?c rdfs:subClassOf ?d . }"

STRATA = [
    ("identity across exports", [   # monitoring ID = "mon:" + CMDB name without its class suffix, "_" -> "-"
        """CONSTRUCT { ?c src:sameAs ?m } WHERE { ?c a src:CmdbRecord ; src:ciName ?n .
             BIND(CONCAT("mon:", REPLACE(REPLACE(?n, "_(svc|db|q)$", ""), "_", "-")) AS ?mid)
             ?m a src:MonRecord ; src:component ?mid . }""",
    ]),
    ("stale records", [
        'CONSTRUCT { ?c a src:Stale } WHERE { ?c a src:CmdbRecord ; src:status "decommissioned" . }',
        'CONSTRUCT { ?c a src:Stale } WHERE { ?c src:sameAs ?m . ?m src:status "retired" . }',
    ]),
    ("live entities (negation)", [
        f"""CONSTRUCT {{ ?e ex:fromRecord ?c }} WHERE {{ ?c a src:CmdbRecord ; src:ciId ?id .
             FILTER NOT EXISTS {{ ?c a src:Stale }} BIND(IRI(CONCAT("{E}", ?id)) AS ?e) }}""",
    ]),
    ("names", [
        f"""CONSTRUCT {{ ?e ex:name ?nm }} WHERE {{ {LIVE}
             {{ ?c src:ciId ?nm }} UNION {{ ?c src:ciName ?nm }} UNION {{ ?c src:sameAs ?m . ?m src:component ?nm }}
             UNION {{ ?c src:sameAs ?m . ?m src:displayName ?nm }} UNION {{ ?c src:sameAs ?m . ?m src:alias ?nm }} }}""",
    ]),
    ("canonical facts (CMDB authoritative: class, tier, region, replicas, service deps)", [
        f"""CONSTRUCT {{ ?e a ?cls }} WHERE {{ {LIVE} ?c src:ciClass ?k .
             VALUES (?k ?cls) {{ ("service" ex:Service) ("customer_facing_service" ex:CustomerFacingService)
                                 ("database" ex:Database) ("queue" ex:Queue) }} }}""",
        f"CONSTRUCT {{ ?e ex:tier ?t }} WHERE {{ {LIVE} ?c src:tier ?t . }}",
        f"""CONSTRUCT {{ ?e ex:deployedIn ?r . ?r a ex:Region }} WHERE {{ {LIVE} ?c src:datacenter ?dc .
             BIND(IRI(CONCAT("{E}", ?dc)) AS ?r) }}""",
        f"""CONSTRUCT {{ ?e ex:replicaOf ?p }} WHERE {{ {LIVE} ?c src:replicaOfCi ?pid .
             ?p ex:fromRecord ?pc . ?pc src:ciId ?pid . }}""",
        f"""CONSTRUCT {{ ?e ex:dependsOn ?t }} WHERE {{ {LIVE} ?c src:dependsOnCi ?tid .
             ?t ex:fromRecord ?tc . ?tc src:ciId ?tid . }}""",
    ]),
    ("canonical facts (monitoring authoritative: team, SLA, datastore deps)", [
        f"""CONSTRUCT {{ ?e ex:ownedBy ?tm . ?tm a ex:Team }} WHERE {{ {LIVE} ?c src:sameAs ?m . ?m src:team ?tn .
             BIND(IRI(CONCAT("{E}", ?tn)) AS ?tm) }}""",
        f"""CONSTRUCT {{ ?e ex:hasSLA ?s }} WHERE {{ {LIVE} ?c src:sameAs ?m . ?m src:sla ?sid .
             BIND(IRI(CONCAT("{E}", ?sid)) AS ?s) }}""",
        f"CONSTRUCT {{ ?e ex:dependsOn ?t }} WHERE {{ {LIVE} ?c src:sameAs ?m . ?m src:upstream ?ref . ?t ex:name ?ref . }}",
    ]),
    ("type closure", [TYPE_CLOSURE]),
    ("dependency closure", [
        "CONSTRUCT { ?x ex:dependsOnTransitively ?y } WHERE { ?x ex:dependsOn ?y . }",
        "CONSTRUCT { ?x ex:dependsOnTransitively ?y } WHERE { ?x ex:dependsOn ?m . ?m ex:dependsOnTransitively ?y . }",
    ]),
    ("replica groups", [
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?x } WHERE { ?x a ex:Component . }",
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?y . ?y ex:inReplicaGroupWith ?x } WHERE { ?x ex:replicaOf ?y . }",
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?z } WHERE { ?x ex:inReplicaGroupWith ?y . ?y ex:inReplicaGroupWith ?z . }",
    ]),
    ("footprint", [
        "CONSTRUCT { ?x ex:hasFootprintRegion ?r } WHERE { ?x ex:inReplicaGroupWith ?m . ?m ex:deployedIn ?r . }",
    ]),
    ("primary, lost (negation)", [
        "CONSTRUCT { ?x a ex:Primary } WHERE { ?x a ex:Component . FILTER NOT EXISTS { ?x ex:replicaOf ?y } }",
        """CONSTRUCT { ?x ex:lostIn ?r } WHERE { ?x a ex:Component ; ex:hasFootprintRegion ?r .
             FILTER NOT EXISTS { ?x ex:hasFootprintRegion ?r2 . FILTER(?r2 != ?r) } }""",
        """CONSTRUCT { ?x ex:lostIn ?r } WHERE { ?x a ex:Database . ?r a ex:Region .
             FILTER NOT EXISTS { ?x ex:hasFootprintRegion ?a , ?b . FILTER(?a != ?r && ?b != ?r && ?a != ?b) } }""",
    ]),
    ("down", [
        "CONSTRUCT { ?s ex:downIn ?r } WHERE { ?s a ex:Service ; ex:lostIn ?r . }",
        "CONSTRUCT { ?s ex:downIn ?r } WHERE { ?s a ex:Service ; ex:dependsOnTransitively ?d . ?d ex:lostIn ?r . }",
    ]),
    ("SLA breach", [
        "CONSTRUCT { ?l ex:breachedIn ?r } WHERE { ?s ex:downIn ?r ; ex:hasSLA ?l . }",
    ]),
    ("type closure of derived classes", [TYPE_CLOSURE]),
]


def materialize(g):
    """Apply every stratum to a fixpoint, in order. Returns {stratum: (rounds, triples added)}."""
    stats = {}
    for name, rules in STRATA:
        rounds = added = 0
        while True:
            rounds += 1
            new = {t for q in rules for t in g.query(q, initNs=NS) if t not in g}
            if not new:
                break
            for t in new:
                g.add(t)
            added += len(new)
        stats[name] = (rounds, added)
    return stats


def load_materialized(n):
    g = Graph()
    g.parse(HERE / "data" / "rdf" / f"raw_{n}.ttl")
    g.parse(ONTOLOGY)
    return g, materialize(g)


if __name__ == "__main__":
    import time
    for n in (20, 100, 500):
        t0 = time.time()
        g, stats = load_materialized(n)
        g.serialize(HERE / "data" / "rdf" / f"materialized_{n}.ttl", format="turtle")
        print(f"  graph {n}: {len(g)} triples, {sum(a for _, a in stats.values())} derived, {time.time() - t0:.1f}s")
