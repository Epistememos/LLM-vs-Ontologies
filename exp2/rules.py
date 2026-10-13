"""rules.py - materialize the derived classes and properties of ontology2.ttl with SPARQL CONSTRUCT
rules, applied stratum by stratum, each to a fixpoint. Rules that use negation (FILTER NOT EXISTS) sit
in a later stratum than everything they negate over, so the result is well defined.

    from rules import load_materialized
    g = load_materialized("exp2/data/scenarios/graph_100_reg-2.ttl")
"""
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

EX = Namespace("http://example.org/br#")
NS = {"ex": EX, "rdf": RDF, "rdfs": RDFS, "owl": OWL, "xsd": XSD}
ONTOLOGY = Path(__file__).resolve().parent / "ontology2.ttl"

STRATA = [
    ("type closure", [
        "CONSTRUCT { ?x a ?d } WHERE { ?x a ?c . ?c rdfs:subClassOf ?d . }",
    ]),
    ("dependency closure", [
        "CONSTRUCT { ?x ex:dependsOnTransitively ?y } WHERE { ?x ex:dependsOn ?y . }",
        "CONSTRUCT { ?x ex:dependsOnTransitively ?y } WHERE { ?x ex:dependsOn ?m . ?m ex:dependsOnTransitively ?y . }",
    ]),
    ("replica groups", [
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?x } WHERE { ?x a ex:Component . }",
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?y . ?y ex:inReplicaGroupWith ?x } WHERE { ?x ex:replicaOf ?y . }",
        "CONSTRUCT { ?x ex:inReplicaGroupWith ?z } WHERE { ?x ex:inReplicaGroupWith ?y . ?y ex:inReplicaGroupWith ?z . }",
    ]),
    ("footprint, replicas", [
        "CONSTRUCT { ?x ex:hasFootprintRegion ?r } WHERE { ?x ex:inReplicaGroupWith ?m . ?m ex:deployedIn ?r . }",
        "CONSTRUCT { ?x a ex:Replica } WHERE { ?x a ex:Component ; ex:replicaOf ?y . }",
    ]),
    ("primary, lost (negation)", [
        "CONSTRUCT { ?x a ex:Primary } WHERE { ?x a ex:Component . FILTER NOT EXISTS { ?x ex:replicaOf ?y } }",
        """CONSTRUCT { ?x a ex:Lost } WHERE {
             ?f a ex:FailedRegion . ?x a ex:Component ; ex:hasFootprintRegion ?f .
             FILTER NOT EXISTS { ?x ex:hasFootprintRegion ?r . FILTER(?r != ?f) } }""",
    ]),
    ("down", [
        "CONSTRUCT { ?s a ex:Down } WHERE { ?s a ex:Service , ex:Lost . }",
        "CONSTRUCT { ?s a ex:Down } WHERE { ?s a ex:Service ; ex:dependsOnTransitively ?d . ?d a ex:Lost . }",
    ]),
    ("SLA breach, tier rule", [
        "CONSTRUCT { ?l a ex:BreachedSLA } WHERE { ?s a ex:Down ; ex:hasSLA ?l . }",
        "CONSTRUCT { ?a ex:violatesTierRule ?b } WHERE { ?a ex:dependsOn ?b . ?a ex:tier 1 . ?b ex:tier 3 . }",
        """CONSTRUCT { ?a a ex:TierRiskService } WHERE {
             ?a a ex:Service ; ex:tier 1 ; ex:dependsOnTransitively ?b . ?b ex:tier 3 . }""",
    ]),
    ("type closure of derived classes", [
        "CONSTRUCT { ?x a ?d } WHERE { ?x a ?c . ?c rdfs:subClassOf ?d . }",
    ]),
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


def load_materialized(data_ttl):
    g = Graph()
    g.parse(data_ttl)
    g.parse(ONTOLOGY)
    stats = materialize(g)
    return g, stats


if __name__ == "__main__":
    # Precompute the materialized graph (data + derived facts) for every base graph and scenario copy.
    data = Path(__file__).resolve().parent / "data"
    out = data / "materialized"
    out.mkdir(exist_ok=True)
    sources = sorted(data.glob("graph_*.ttl")) + sorted((data / "scenarios").glob("graph_*.ttl"))
    for src in sources:
        g, stats = load_materialized(src)
        g.serialize(out / src.name, format="turtle")
        print(f"  {src.name}: {len(g)} triples, {sum(a for _, a in stats.values())} derived")
