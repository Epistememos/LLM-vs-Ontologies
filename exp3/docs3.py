"""docs3.py - Experiment 3 documentation text given to the conditions.

RULES and DEFINITIONS are identical for A3, B3 and C3. RULES must equal truth3.RULES word for word (checked by
test_run3.py); it is copied here, not imported, so no prompt builder imports code that can read data/hidden/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "exp2"))
from docs import DEFINITIONS  # noqa: E402  exp2 definitions, unchanged

RULES = """Resolution rules for the two exports.
- Authority: the CMDB export is authoritative for component class, tier, region (datacenter), replicas
  (replica_of_ci) and service-to-service dependencies (depends_on_ci). The monitoring export is authoritative for
  team ownership (team), SLAs (sla) and service-to-datastore dependencies (upstream). When the two exports disagree
  on a fact, use the authoritative source.
- Stale records: a record whose status is "decommissioned" (CMDB) or "retired" (monitoring) is stale. The component
  no longer exists: ignore it in both exports, together with every relation that refers to it."""

ANSWERS = """Answer format: give services and other components as CMDB CI IDs (e.g. CI-12345), SLAs as monitoring SLA IDs
(e.g. SLA-GOLD-01) and teams as monitoring team names (e.g. team-platform). A failure is named by its CMDB
datacenter (e.g. dc-fra)."""

EXPORTS = """The two exports describe the same infrastructure with different identifiers.
cmdb.json: {"export": "cmdb", "records": [...]}; each record has ci_id (CI-NNNNN), ci_name, ci_class (service,
  customer_facing_service, database, queue), tier, status, owner_group (OG-NN), datacenter, replica_of_ci,
  depends_on_ci (list of ci_id; service-to-service dependencies).
monitoring.json: {"export": "monitoring", "records": [...], "slas": [...]}; each record has component (mon:<name>),
  display_name, aliases, kind (service or datastore), status, team, zone, sla, upstream (service-to-datastore
  dependencies, each written as a component ID, display name or alias); slas lists sla_id and availability.
mapping_tables.json: crosswalks {"owner_group_to_team": {...}, "datacenter_to_zone": {...}}.
Identity: the monitoring component of a CMDB record is "mon:" + its ci_name without the class suffix (_svc, _db, _q),
with "_" replaced by "-"."""

GLUE = """Glue library. glue.py is in the working directory and already applies the resolution rules and the identity rule;
import it instead of re-implementing them:
    from glue import Infra3
    g = Infra3("cmdb.json", "monitoring.json", "mapping_tables.json")
    g.resolve(name)                       # CI ID for any identifier either export uses (KeyError if unknown)
    g.names_of(ci)                        # every identifier of a component
    g.components(*classes), g.services(), g.primaries(*classes), g.is_primary(ci)
    g.cls[ci], g.tier[ci], g.region[ci], g.team[ci], g.sla[ci]   # dicts (index with [ ]): resolved facts
    g.deps[ci], g.replica_of[ci]          # dicts: direct dependencies (both exports), replica target
    g.transitive_dependencies(ci), g.replica_group(ci), g.footprint(ci)
    g.is_lost(ci, datacenter), g.is_down(ci, datacenter)
    g.down_services(datacenter, primary_only=False), g.breached_slas(datacenter)
    g.stale                               # set of CI IDs of stale components (already excluded everywhere)
    g.team_of_owner_group, g.zone_of_datacenter                  # crosswalk dicts
Classes are the ci_class strings above. Each method implements the definition of the same name."""

C3_NOTE = """The graph has been built from both exports by the rules: entities are ex:<CI ID> (e.g. ex:CI-12345), every
identifier of an entity is an ex:name literal (so a service named "Payments Search Service" is
?x ex:name "Payments Search Service"), teams are ex:<team name>, regions ex:<datacenter>, SLAs ex:<SLA ID>.
Failure is region-parametric: ?x ex:lostIn ex:dc-fra, ?s ex:downIn ex:dc-fra, ?l ex:breachedIn ex:dc-fra."""


def common():
    return f"{RULES}\n\n{DEFINITIONS}\n\n{ANSWERS}"


def b3_doc():
    return f"{EXPORTS}\n\n{common()}\n\n{GLUE}"


def a3_doc():
    return f"{EXPORTS}\n\n{common()}"


def c3_doc():
    return f"{common()}\n\n{C3_NOTE}"
