# Standing rules for this repository

- Experiments 1 and 2 are frozen (tags `exp1-final`, `exp2-final`): never modify their files, results or hashes.
- No tuning toward a C3 win. Log every change to a prompt, question or harness with the evidence that motivated it.
- `data/hidden/` (e.g. `exp3/data/hidden/`) is never read at runtime and never shown to any condition: not in
  prompts, sandboxes or harnesses.
- The H2 changes are fixed in `exp3/PREREG_EXP3.md` and may not be altered after any run.
- Max 3 prompt iterations per condition, clarity fixes only, each logged with evidence.
- The DEV/TEST split never moves.
- Ask before spending over ~$5 of API budget; print the call count and cost estimate with a 1.6x correction before
  any run.
- Claude Code authors both B3 and C3 artifacts; log line counts and fix counts for each.

## Current status

Experiment 3 step 1 done (generator, truth3, questions, PREREG draft); step 2 not started.
