# Prompt log

Every change to a condition's prompt during DEV tuning gets a row here and a `PROMPT_VERSION` bump in its
`run_*.py`. Tuning uses DEV questions only. Prompts freeze before the TEST run (see PREREG.md).

| Condition | Version | Date | Change | Why (DEV evidence) |
|---|---|---|---|---|
| A | 1 | 2026-10-08 | initial | - |
| B | 1 | 2026-10-08 | initial | - |
| B+ | 1 | 2026-10-08 | initial (= B + SCHEMA_DOC) | - |
| C | 1 | 2026-10-08 | initial | - |

Iterations used (excluding the initial version): A 0, B 0, B+ 0, C 0 (no condition-specific prompt changes).
Tuning rounds applied to all conditions equally (cap 3, mechanical or clarity fixes only): 1 used (2026-10-08: MAX_TOKENS + primary clause).

## Question-set changes (apply to every condition equally; not prompt tuning)

| Date | Change | Why (DEV evidence) | Affected |
|---|---|---|---|
| 2026-10-08 | `region_down` and `region_count_down` now ask about primary services only ("Include replicas" replaced by the primary-only clause); answers regenerated from truth.py | A on 20-L4-00 counted replicas of down services as down. Under the stated definition replicas have no dependsOn edges, so a replica of a down service can be "up": a counter-intuitive rule that tests rule-following, not topology reasoning. Question selection, qids and splits unchanged. | 10 questions (2 DEV: 20-L4-00, 20-L4-01; 8 TEST) |
| 2026-10-08 | Primary clause made explicit about edge direction in every question that uses it: "a node X is primary if the data has no edge 'X replicaOf Y', i.e. X is not itself a replica of another node". Answers unchanged (byte-identical answer key). | DEV round 1: B+ (20-L3-00, 20-L4-00, 500-L3-01) and C (500-L3-01) both coded 'primary' as 'no incoming replicaOf', the inverse of the stated definition; the shared error points at question wording, not at a condition. | 36 questions (9 DEV, 27 TEST) |

## Harness fixes (parsing/plumbing bugs, not prompt changes)

| Date | Condition | Fix | Evidence |
|---|---|---|---|
| 2026-10-08 | C | Ignore a fenced code block whose whole content is the `{"answer_type": ...}` declaration when picking the query | 20-L5-01: the model wrapped its declaration in a ```sparql fence after the real query; the harness executed the declaration and spent the retry. Intent was unambiguous (A's parser is equally lenient about where its JSON appears). |
| 2026-10-08 | all | `MAX_TOKENS` 4096 -> 8192 in llm.py, identical for every condition | DEV round 1: 3/14 of A's 500-node answers hit max_tokens mid-enumeration and returned no answer; a mechanical limit, not reasoning. Changes every cache key, so all DEV calls were re-run. |

DEV round 1 results (before these two changes) are archived in results/dev_round1/.
