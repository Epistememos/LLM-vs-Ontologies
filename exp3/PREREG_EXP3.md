# Pre-registration: Experiment 3 (DRAFT, step 1)

**Status: frozen 2026-10-20, before any TEST question was sent.** Design, decision rules, the DEV pilot and the
difficulty decision are below; TEST results are not. Experiments 1 and 2 are frozen at tags `exp1-final` and
`exp2-final` and are not modified.

## Motivation

Experiments 1 and 2 found no measurable advantage for an ontology over equivalent documented schema plus code, on a
single clean source with static definitions. Experiment 3 tests the two settings where ontologies are usually claimed
to pay off: **several sources with conflicting identifiers**, and **definitions that change over time**.

## Hypotheses (tested separately; either may come out null; all results reported)

- **H1 (accuracy, confirmatory):** with two sources that name the same entities differently, C3 (mappings and
  definitions encoded in an ontology and rules) beats B3 (the same mappings and definitions as documented Python glue)
  on cross-source questions.
- **H2 (maintenance, exploratory and descriptive):** after a pre-specified schema change and definition change, C3
  needs fewer changed lines and breaks fewer questions than B3. H2 has no significance test and no decision rule.

## Data

- **Ground truth topology:** exp1's generator (imported unmodified), one new seed per size scale: 3021 (23-node scale;
  3020 failed the generator's own planting step), 3100 and 3500. The canonical graphs have 22, 120 and 567 nodes.
- **Two exports derived from the same truth** (`gen3.py`):
  - **CMDB-style:** `CI-NNNNN` IDs, underscore names, `ci_class`, `tier`, `status`, `owner_group` (`OG-NN`),
    `datacenter`, `replica_of_ci`, `depends_on_ci` (service-to-service only).
  - **Monitoring-style:** `mon:` IDs, display names, aliases (e.g. `mon:payments-search`, "Payments Search Service",
    `pay-sea-svc-v2`), `status`, `team`, `zone`, `sla`, `upstream` (service-to-datastore only, partly written as aliases).
  - Each fact lives in one export or both, so cross-source questions need both.
- **Planted noise, fixed per graph:** stale ghost services (2 / 3 / 5), each flagged stale in exactly one export, live
  in the other, with 2 live dependents. Contradictions: 2 / 4 / 8 region conflicts (wrong monitoring zone) and the same
  number of team conflicts (wrong CMDB owner group).
- **Hidden entity-resolution key** (`data/hidden/er_key_{n}.json`) and canonical graph (`data/hidden/graph_{n}.json`):
  read only by `truth3.py` and the scorer, never by any condition. Before any run, a guard checks that no artifact
  reads `data/hidden/` at runtime, and a test diffs each artifact's mappings (B3 glue, C3 ontology) against the key.
- **Consistency check** (`truth3.py`): rebuilding the canonical graph from the two exports, with only the key and
  the resolution rules below, must reproduce it exactly. It does for all three graphs, and no identifier is ambiguous.

### Resolution rules and stale statement (identical text in every condition's docs)

```
Resolution rules for the two exports.
- Authority: the CMDB export is authoritative for component class, tier, region (datacenter), replicas
  (replica_of_ci) and service-to-service dependencies (depends_on_ci). The monitoring export is authoritative for
  team ownership (team), SLAs (sla) and service-to-datastore dependencies (upstream). When the two exports disagree
  on a fact, use the authoritative source.
- Stale records: a record whose status is "decommissioned" (CMDB) or "retired" (monitoring) is stale. The component
  no longer exists: ignore it in both exports, together with every relation that refers to it.
```

This text is `truth3.RULES`; B3's and C3's docs must contain it verbatim (checked by a script before any run).
The definitions (replica group, footprint, primary, lost, down, SLA breach) carry over from Experiment 2 unchanged.

## Questions

- `questions3.py`, answers from the canonical graph. **Cross-source** (5 kinds): `is_down`, `down_by_team`,
  `breached_slas`, `sla_breached`, `count_down`. A failure is named by a CMDB datacenter, services by monitoring
  display names or aliases, teams and SLAs by monitoring IDs. **Single-source controls** (2 kinds): `cmdb_deps`,
  `mon_owner`.
- Answer namespaces: services as CMDB CI IDs, SLAs as monitoring SLA IDs, teams as monitoring team names. The scorer
  maps any known identifier of the right entity through the hidden key and counts unknown IDs as hallucinations.
- Quotas per graph, fixed: is_down 8, down_by_team 5, breached_slas 3, sla_breached 4, count_down 2, cmdb_deps 2,
  mon_owner 2 (fewer when a small graph lacks distinct entities). Yes/no kinds are balanced.
- **DEV/TEST split by seed** (seeded shuffle per graph, first 30% DEV), made before any run and never moved:
  76 questions, 23 DEV and 53 TEST. TEST holds **44 cross-source** and 9 control questions.
- **Trap audit** (no model involved): 53% of cross-source questions change answer under at least one wrong reading:
  ignoring the monitoring export 27/64, keeping stale records 14/64, trusting the non-authoritative source 8/64,
  matching entities by name similarity instead of the mappings 6/64 (a diagnostic: monitoring identifiers matched
  to the CMDB record with the most similar normalized name).

## Conditions (same model, temperature 0, 8192 output tokens, 60 s timeout, one retry on errors only, as in Exp 2)

| Condition | Gets | Tool |
|---|---|---|
| **A3** (baseline, **23- and 120-node graphs only**) | both exports in the prompt + docs (schemas, rules, definitions) | none |
| **B3** | export schemas + docs + a glue library (entity resolution, field mapping, footprint/lost/down) | Python sandbox over both exports |
| **C3** | ontology + rules with the mappings and definitions, materialized before querying; class and property names | one SPARQL query |

- Artifacts resolve entities completely, with equal mappings in B3 and C3 (diffed against the key). The team and
  region crosswalks are derived from the exports by majority vote over non-stale records and shared by both.
- Failure is region-parametric: C3 materializes `lostIn`, `downIn` and `breachedIn` for every region before
  querying; B3's glue takes the datacenter as an argument. Neither artifact or harness learns the failed region from
  the hidden answer key.
- Hidden-data guard: an audit hook refusing any open or listing under `data/hidden/` runs in the harness process
  and at the top of every sandbox program and SPARQL runner.
- B3 and C3 get the same information. I author both artifacts and review both. Line counts, fix
  counts and my review hours are logged for each.
- Prompt versions at freeze: A3 1, B3 2, C3 2 (one clarity iteration each for B3 and C3, logged with its exact text
  and evidence in `LOG3.md`).
- Prompt iterations: at most 3 per condition, clarity fixes only, each logged with its evidence. No tuning toward a
  C3 win.

## Repeats

Every TEST question runs **3 times per condition** at temperature 0, bypassing the response cache for repeats 2 and
3. Each repeat after the first uses its own cache namespace, so the cache is bypassed without changing the model
settings. Repeats are stored separately. Answer variation across repeats is reported per condition.

## Primary analysis (H1)

- Metric: per-question F1 (set precision/recall; exact match for bool and number), **averaged over the 3 repeats**.
- Population: TEST **cross-source** questions, all three graphs pooled (n = 44).
- Statistic: mean paired difference **F1(C3) − F1(B3)**.
- **Primary CI: cluster bootstrap by (question text × graph seed)**: resample clusters with replacement; 10,000
  resamples, numpy seed 0, 95% percentile interval.
- Decision rules on the cluster CI: **supported** if the lower bound is above 0; **not supported** if the CI includes
  0; **contradicted** if the upper bound is below 0.
- **Secondary CI:** per-question bootstrap (as in Experiments 1 and 2). If the two disagree, the decision follows the
  cluster CI; both are reported and the result is described as sensitive to the correlation assumption.
- **Weight of each scale:** the cross-source TEST questions are 15 / 15 / 14 on the 22- / 120- / 567-node graphs,
  one cluster each, so 29 of 44 (two thirds of the clusters) come from the two larger scales and the primary CI is
  dominated by them. Per-seed results are reported descriptively only, with no per-seed test.
- **Control questions** are reported per seed and size: TEST 2 / 3 / 4 and DEV 2 / 1 / 0 on the 22- / 120- /
  567-node graphs (12 in total).

## Secondary and descriptive analyses

- C3 − B3 on control questions; per graph, per kind (exploratory).
- A3 on the two smaller graphs, against B3 and C3 on the same questions (descriptive).
- Error split by trap: for each wrong answer, whether it matches the ignore-monitoring, keep-stale or
  wrong-authority answer (exploratory).
- Hallucinations, parse rate, retries, C3 SPARQL validity, timeouts per condition, median latency, tokens, cost.

## H2 change test (exploratory, descriptive)

Both changes are fixed now, before any run, and applied only after the baseline TEST results are frozen:

1. **Schema change:** the CMDB export renames the field `datacenter` to `site` (values unchanged).
2. **Definition change ("lost"):** a non-database component is lost if its footprint contains only the failed region
   (unchanged); **a database is lost if fewer than two of its footprint regions lie outside the failed region**.

Impact, computed from ground truth before any run: the "lost" change alters **29 of 53 TEST answers** (29 of 44
cross-source, 0 of 9 controls; 9 / 10 / 10 on the three graphs). The field rename changes no answer by construction:
it is a format change that can only break artifacts, not alter the truth.

Procedure: (a) re-run TEST with the **unchanged** artifacts and docs against the changed export and the changed answer
key, and classify each question that breaks as **loud** (error, failed retry or no answer) or **silent** (runs, wrong
answer); (b) apply the minimal correct edit to each artifact and its docs (I review both), record lines
changed (`git diff --numstat`) and my time; (c) re-run and re-score. Reported: lines changed, loud vs silent
breakage counts, and accuracy before and after, per condition.

## Difficulty and headroom (decided before any TEST run)

- **Knobs** (`gen3.DIFFICULTY`) at the start: alias_rate 0.5; stale ghosts 2 / 3 / 5; region and team conflicts
  2 / 4 / 8 each.
  The knobs change only the exports, never the canonical graph, so questions, answers and the DEV/TEST split stay
  fixed if they are raised.
- **Pilot on Haiku 4.5, DEV only, pre-registered ceiling rule:** if any condition's mean F1 on DEV cross-source
  questions is **above 0.90**, raise the knobs (alias_rate +0.2, stale ×2, conflicts ×2), regenerate the exports and
  re-pilot. At most 2 rounds, each logged. The final knob values are recorded here before TEST.
- A smaller model is piloted as a bonus only, if one is still served.

### Pilot results (DEV, Haiku 4.5, one repeat)

| Mean F1, DEV cross-source questions | A3 (22 / 120 nodes) | B3 | C3 |
|---|---|---|---|
| Round 0 (alias 0.5; stale 2/3/5; conflicts 2/4/8) | 0.644 | **1.000** | **0.950** |
| Round 1 (alias 0.7; stale 4/6/10; conflicts 4/8/16) | 0.620 | **1.000** | **0.950** |

- Both rounds triggered the ceiling rule (B3 and C3 above 0.90). Round 1 raised the knobs as pre-registered and moved
  only A3. **The difficulty rule ended after round 1; round 2 was not used.** Reason: B3's glue and C3's rules
  resolve all knob-controlled noise (aliases, stale records, contradictions) before the model sees it, so the knobs
  cannot move B3 or C3, and round 1 confirmed no movement.
- **Final knob values: round 1** (alias_rate 0.7; stale 4 / 6 / 10; conflicts 4 / 8 / 16). With them, 64% of
  cross-source questions change answer under at least one wrong reading: ignoring the monitoring export 27/64,
  keeping stale records 24/64, trusting the non-authoritative source 22/64, matching names by similarity 2/64.
- In both rounds C3's only misses (2 of 23) were query-shape errors: an SLA and a team looked up by `ex:name`,
  which only components have. This led to the clarity fix below; with it, C3 scored 1.000 on DEV (23/23 valid
  queries, no retries).
- Pilot cost: round 0 $0.34, round 1 $0.25, C3 clarity check $0.09.

### Consequences for the analysis, fixed before TEST

- **H1 is expected to be null on ceiling grounds.** B3 and C3 are at or near the ceiling on DEV, so the primary test
  is unlikely to separate them. H1, its decision rule and its CIs are unchanged and are reported as planned.
- **The informative parts are A3 vs B3 and C3** (the LLM alone against either form of resolved, encoded knowledge
  on conflicting sources) **and H2** (maintenance under a schema and definition change).
- **Canonical data is fixed.** Experiment 1's generator iterates Python sets, whose order changes between
  processes, so re-running it is not reproducible. The canonical graphs in `data/hidden/` are frozen as generated
  in step 1 (hashes below), and `gen3.py` derives the exports from them; the frozen data files, not the generator,
  are the source of truth.

## Budget

After DEV, print the measured TEST estimate (call count and cost, × 1.6) and ask before TEST. If it is above about
$6, pre-register a cut here before running: 2 repeats instead of 3, or dropping the 567-node graph for A3/B3.

**Measured estimate:** 3 repeats, A3 on the two smaller graphs (35 questions), B3 and C3 on all 53 TEST questions:
about 489 calls, $1.84 by the dry-run estimator, **$2.94 with the 1.6× correction**, $2.32 when scaled from DEV's
actual per-question cost. Below $6, so **no cut**: 3 repeats and all sizes as planned.

## Known limitations

- One generator, three graphs, one model; synthetic exports with planted, not organic, noise.
- I write the data, rules, glue, questions and ground truth.
- Equal mappings in B3 and C3 mean entity resolution is solved by the artifacts in both: H1 tests whether the
  ontology form helps the model use resolved mappings, not whether it resolves entities better.
- H2 measures one schema change and one definition change; it is descriptive.

## Frozen file hashes (sha256, first 16 hex chars)

Checked by `python tools/verify_frozen.py`, which accepts the raw, LF or CRLF form of each file (Git on Windows
may rewrite line endings on checkout). The hidden files are listed by hash only.

```
da9e8217f34c4543 gen3.py
a6912786a3861130 truth3.py
f02c629f207aa117 questions3.py
c49838b133fbace0 derive_tables.py
cd592d75c3cdb8a3 glue.py
bf2af301031a16a1 to_rdf3.py
d6c263e8cf5967e3 rules3.py
382f8aa2f165b2d9 ontology3.ttl
ec6a7829e79a3d7d docs3.py
d05b2e50bd7c1dfe run3.py
1f0a9d040a01ae9c score3.py
5e83506222cfed58 pilot3.py
5d13a9c430c46191 verify3.py
9ae8756fa2f406d5 test_run3.py
aec408748304a195 mapping_tables.json
5fd19421ce0d31b2 data/questions.json
e2ecb880b74abb82 data/cmdb_20.json
cca5501f4b77abae data/cmdb_100.json
01ff44de7c3b9a77 data/cmdb_500.json
47c0bd354e715cbf data/monitoring_20.json
49eb11e1eb915a2d data/monitoring_100.json
b5ab1e29b12b92f3 data/monitoring_500.json
2970fb9c6ae7b7fd data/rdf/materialized_20.ttl
107eeee693adafde data/rdf/materialized_100.ttl
cce710de90e6cf10 data/rdf/materialized_500.ttl
7e2de1042a6b4747 data/hidden/graph_20.json
d3392d3e800d1ebc data/hidden/graph_100.json
20bbda1571519393 data/hidden/graph_500.json
314577155a137fdb data/hidden/er_key_20.json
a7fd7ffff624a19d data/hidden/er_key_100.json
0d0d4e0191cd6f4b data/hidden/er_key_500.json
ee5d50cbc45689f5 data/hidden/answers.json
```
