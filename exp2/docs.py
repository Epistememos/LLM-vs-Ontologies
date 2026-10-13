"""docs.py - Experiment 2 documentation text. Questions carry no definitions; they live here (B+, B++)
and in ontology2.ttl (C2).

- B+ (exp2-docs) gets: exp1 SCHEMA_DOC + DEFINITIONS + DATA_NOTE_JSON.
- B++ gets the same plus HELPERS_DOC.
- C2 gets ontology2.ttl (definitions as rdfs:comment, executable as rules) + DATA_NOTE_RDF.
DATA_NOTE_JSON and DATA_NOTE_RDF say the same thing in each format and contain no definitions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import SCHEMA_DOC  # noqa: E402  exp1 prose schema, unchanged

DATA_NOTE_JSON = ('Data format: in graph.json, the Region node marked "failed": true, if any, is the region '
                  'that has failed in this scenario.')
DATA_NOTE_RDF = ('Data format: the region typed ex:FailedRegion, if any, is the region that has failed in '
                 'this scenario.')

# Every definition exp1 put in question text (FAILURE_DEF, the primary clause, the SLA sentence, the tier
# rule, the transitive-dependency gloss, the tier-1 -> tier-3 risk), same wording, region-neutral.
DEFINITIONS = """Definitions.
- 'X replicaOf Y' means X is a replica of Y.
- Replica group: a node plus every node connected to it through replicaOf links in either direction, transitively.
- Footprint: the set of regions where members of a node's replica group are deployed.
- Primary: a Service, Database or Queue X is primary if the data has no edge 'X replicaOf Y', i.e. X is not
  itself a replica of another node.
- Transitive dependency: X transitively depends on Y if Y is reachable from X directly or through a chain of
  dependsOn links.
- Lost: when a region fails, a node is lost if its footprint contains only the failed region.
- Down: a service is down if it is lost or if any node it transitively depends on (via dependsOn) is lost.
- Breached SLA: an SLA is breached if any service that has it is down.
- Tier rule: tier-1 services must not depend directly on tier-3 services; a dependsOn edge from a tier-1
  service to a tier-3 service violates the tier rule.
- Tier risk: a tier-1 service is a tier risk if it transitively depends on at least one tier-3 service."""

HELPERS_DOC = """Helper library. helpers.py is in the working directory; import it instead of re-implementing
the definitions above:
    from helpers import Infra
    g = Infra("graph.json")
    g.failed_region                      # the failed region's ID, or None
    g.of_type(*types), g.services(), g.components()
    g.primaries(*types), g.is_primary(x)
    g.transitive_dependencies(x), g.transitive_dependents(x)
    g.replica_group(x), g.footprint(x)
    g.is_lost(x, region=None), g.lost_components(region=None)
    g.is_down(x, region=None), g.down_services(region=None, primary_only=False)
    g.breached_slas(region=None)
    g.tier(x), g.tier_violations(), g.tier_risk_services()
    g.nodes        # dict: node ID -> record, e.g. g.nodes[x]["type"]
    g.edges        # list of (source, relation, target) tuples
    g.region[x], g.owner[x], g.sla[x]    # dicts (index with [ ], do not call): region, owning team, SLA of x
Methods taking a region default to the failed region. Each implements the definition of the same name."""


def bplus_doc():
    return f"{SCHEMA_DOC}\n\n{DEFINITIONS}\n\n{DATA_NOTE_JSON}"


def bplusplus_doc():
    return f"{bplus_doc()}\n\n{HELPERS_DOC}"
