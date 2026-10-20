# Blast Radius: do ontologies help AI reason about how systems depend on each other?

When a datacenter goes down at a large company, someone has to answer a hard question fast: *what else breaks?*
Which services stop working, which customers are affected, which contracts are breached? This is called the
**blast radius** of a failure, and answering it means following chains of dependencies across hundreds of systems.

Companies increasingly want AI assistants, built on large language models like the one behind ChatGPT, to answer
questions like this. A popular claim is that these assistants work much better if they are given an **ontology**: a
formal, machine-readable description of what exists in the business and how it all connects. Ontologies are
expensive to build, so it matters whether the claim is true.

This repository is a series of small, carefully controlled experiments that test it:

> "AI models grounded in an ontology are better at reasoning about how systems depend on each other than AI models alone."

Short answer so far: **giving the AI well-organized, pre-processed knowledge helps a lot, but the formal ontology
format itself made no measurable difference.** What mattered was the work an ontology is supposed to do (deciding
what things are and computing what they mean), not the technology it is written in. The rest of this page explains
how I tested that, what I found, and what I think it means for the future of ontologies, including what it suggests
about operational ontologies such as Palantir's, both where that approach is right and where it falls short.

---

## Contents

1. [Key ideas in plain words](#key-ideas-in-plain-words)
2. [How the experiments work](#how-the-experiments-work)
3. [What I found, experiment by experiment](#what-i-found-experiment-by-experiment)
4. [What this means for ontologies](#what-this-means-for-ontologies)
5. [Where ontologies are heading: what this says about Palantir's approach](#where-ontologies-are-heading-what-this-says-about-palantirs-approach)
6. [What these experiments cannot tell you](#what-these-experiments-cannot-tell-you)
7. [Glossary](#glossary)
8. [For technical readers](#for-technical-readers)

---

## Key ideas in plain words

**Large language model (LLM).** The kind of AI behind chat assistants. It reads text and writes text. It is very
good with language, but it can make mistakes when it has to keep track of many precise facts at once, such as a long
list of which system depends on which. All experiments here use one model, Anthropic's Haiku 4.5, set to give the same
answer every time it sees the same question.

**Infrastructure as a map.** A company's technology looks like a map of connected points: *services* (the software
that does the work, like a checkout service), *databases* (where data is stored), *teams* that own them, *regions*
(the datacenters where they run), and *SLAs* (contracts promising a level of availability to customers). Arrows show
what depends on what. If the checkout service needs the payments database, and the payments database runs only in a
datacenter in Frankfurt, then a Frankfurt outage takes checkout down too, even if checkout itself runs elsewhere.
Many services also have **replicas**, backup copies in another region, which can keep them alive when one region fails.

**Ontology.** Think of it as a combination of a dictionary and a rulebook for a business, written so that a computer
can use it. It says what kinds of things exist ("a customer-facing service is a kind of service"), how they relate
("a service depends on a database"), and sometimes rules for working things out ("a service is down if anything it
depends on is down"). Ontologies are usually written in special standard languages (RDF and OWL) and questioned
with a matching query language (SPARQL).

**Grounding.** Giving an AI real, structured information to work from instead of asking it to rely on memory or on a
wall of pasted text.

**The question being tested.** If I give the AI the same knowledge in different forms (raw data, data plus a manual,
data plus ready-made code, or a formal ontology), does the ontology form produce better answers?

---

## How the experiments work

### A made-up company with known answers

Each experiment builds a fictional company's infrastructure from scratch, at three sizes: about 24, 120 and 550
connected items. Because I generate it myself, I know the correct answer to every question exactly, computed by a
separate program that never shares code with the AI setups being tested. I also plant tricky cases on purpose: a
database that fails deep inside a chain of dependencies, a service that survives only because of its backup copy, rule
violations hidden in the data.

### The questions

The AI is asked questions like:

- "Which team owns the payments service?" (simple lookup)
- "Which services depend, directly or indirectly, on database X?" (following chains)
- "If the Frankfurt datacenter fails, which customer contracts (SLAs) are breached?" (failure analysis)
- "Which services break the rule that critical services must not depend on low-priority ones?" (rule checking)

Each answer is a list of names, a yes/no, or a number, so it can be graded automatically.

### The setups being compared

Each experiment gives the same AI the same questions about the same company, but with different help. Roughly:

| Setup | What the AI gets | Everyday comparison |
|---|---|---|
| **AI alone** | the whole map pasted into its instructions | memorizing a city map and answering from memory |
| **AI + code** | the data files and the ability to write and run a small program | being handed the map and a calculator |
| **AI + code + manual** | the same, plus a written description of what everything means | the map, a calculator and a guidebook |
| **AI + ready-made tools** | the same, plus pre-written functions that already compute things like "what is down" | a navigation app that already knows the routes |
| **AI + ontology** | a formal ontology describing everything, which it questions with SPARQL | a professionally built atlas with an index and rules |

### How answers are scored

Each answer gets a score from **0 to 1** (called **F1**). For a list answer, it balances two things: did the AI
include every correct item, and did it avoid adding wrong ones? A perfect answer scores 1. An answer that finds half
the right items and nothing wrong scores about 0.67. A yes/no or number is either right (1) or wrong (0). The scores
reported are averages over many questions.

### How I kept it fair

Testing AI is easy to fool yourself with: you can keep adjusting things until your favourite setup wins. To avoid
that, every experiment follows the same discipline, borrowed from clinical research:

- **Practice questions and exam questions.** Questions are split in advance into a practice set (DEV), which I may use
  to fix genuine bugs, and an exam set (TEST), which no setup sees until the very end and which is run once.
- **Rules written down before the exam.** Before any exam question is run, I write down and lock (*pre-register*) the
  exact comparison, how it will be calculated, and what result would count as supporting or contradicting the claim.
  Every locked file is fingerprinted, so any later change would be detectable.
- **Same budget for everyone.** Every setup gets the same AI model, the same instructions about answer format, and
  the same number of retries if its program crashes.
- **Honest uncertainty.** Each comparison comes with a **95% confidence interval**, a range of plausible values for
  the true difference. If the range includes zero, the experiment cannot tell the setups apart.
- **Report everything.** Results are published whether or not they support the claim. Every change made along the
  way is logged with its reason.

---

## What I found, experiment by experiment

### Experiment 1: does an ontology beat plain data and code?

**Setup.** Four setups: AI alone, AI + code, AI + code + manual, and AI + ontology. The key comparison was the
ontology against *code + manual*, because both had the same knowledge; only the form differed.

**Results** (exam set, average score on the reasoning questions):

| AI alone | AI + code | AI + code + manual | AI + ontology |
|---|---|---|---|
| 0.77 | 0.88 | 0.94 | 0.94 |

- **Organized data plus a tool beat memory, by a lot, and more so as the company grew.** On the largest company,
  the AI alone scored 0.54 while the ontology setup scored 0.89.
- **The ontology tied with code plus a manual.** The difference was −0.005, with a confidence range of −0.055 to
  +0.055: essentially zero. By the rules I wrote in advance, the claim was **not supported**.
- **Where the ontology setup struggled:** failure questions. To answer "is this database lost if Frankfurt fails?",
  the AI had to write a query meaning "*every* backup copy of it is in Frankfurt". It wrote that logic wrong in 9 of
  12 such questions, most often checking one copy instead of all of them.

**My diagnosis afterwards.** The ontology in Experiment 1 was thin. It described what kinds of things existed, but
the hard ideas, like "lost" and "down", were only explained in words inside each question. So the experiment really
compared "a query language plus a description" against "code plus the same description". It never gave the ontology
the job that ontologies are meant to do. That shaped Experiment 2. Details: [Experiment 1 write-up](exp1/README.md),
[addendum](exp1/ADDENDUM.md).

### Experiment 2: what if the ontology does the reasoning in advance?

**Setup.** This time the ontology came with **rules** that work out "lost", "down", "breached" and "primary" for
every item in advance, so the AI only had to look the answers up. It was compared with two setups holding the exact
same definitions: written as a manual (prose), and written as ready-made Python functions.

**Results** (exam set, failure and rule-checking questions):

| Definitions as a manual | Definitions as Python functions | Definitions as ontology rules |
|---|---|---|
| 0.97 | 1.00 | 1.00 |

- **Doing the reasoning in advance removed the remaining mistakes.** The manual-only setup got 2 of 51 questions
  wrong, both from misreading what "primary" means. Both pre-computed setups got everything right, and they answered
  with about a fifth of the text and in about a quarter of the time.
- **But the ontology was no better than the equivalent Python.** Both scored a perfect 1.00. The ontology's advantage
  over the manual (+0.026, range 0.000 to +0.071) was too small to rule out zero, so the claim was again **not
  supported**.
- **The test hit a ceiling.** I predicted this beforehand: when even the weakest setup scores 0.97, there is little
  room left to show a difference. Details: [Experiment 2 write-up](exp2/README.md).

### Experiment 3: the situation ontologies are made for (in progress)

**Setup.** Real companies rarely have one clean list of their systems. They have several systems that each keep
their own records and disagree. Experiment 3 recreates that with two sources describing the same infrastructure:

- an **asset inventory** (a CMDB) that calls a service `CI-04821` with the name `payments_search_svc`;
- a **monitoring system** that calls the same service `mon:payments-search`, "Payments Search Service" or
  `pay-sea-svc-v2`.

The two sources also contain deliberate problems: some records describe systems that were shut down long ago, and
some facts contradict each other (one source says a service runs in Frankfurt, the other says Singapore). A fixed
rulebook says which source to trust for which kind of fact.

Two hypotheses are tested separately:

- **H1 (accuracy):** with two disagreeing sources, does an ontology that resolves the conflicts beat Python code that
  resolves the same conflicts?
- **H2 (maintenance):** when the business changes (a field is renamed in one source, and the definition of "lost" is
  changed), does the ontology need fewer edits and cause fewer silent errors than the code?

**What the practice round showed** (practice questions only; the exam has not been run yet):

| AI alone, reading both raw sources | AI + Python glue that resolves the conflicts | AI + ontology that resolves the conflicts |
|---|---|---|
| 0.64 | 1.00 | 0.95, then 1.00 after one documented wording fix |

- Reading two messy, conflicting sources directly is hard for the AI alone. Once the conflicts are resolved before
  the AI sees anything, it answers almost perfectly, whether the resolving was done by Python or by the ontology.
- Making the sources messier did not change that, because the resolving happens before the AI is involved.
- So H1 is expected to come out as a tie. The informative parts of Experiment 3 are the AI-alone comparison and H2,
  which tests whether ontologies pay off when things change. The exam set has been locked and is ready to run.
  Details: [Experiment 3](exp3/README.md), [pre-registration](exp3/PREREG_EXP3.md).

### All results at a glance

| | Question | Pre-registered result | Status |
|---|---|---|---|
| **[Experiment 1](exp1/README.md)** | Does an ontology (RDF + RDFS/OWL schema, queried with SPARQL) beat an LLM alone, and beat Python code given the same schema documentation? | C − B+ = **−0.005** [−0.055, +0.055]: **not supported**. Ontology and documented code tie; both beat the LLM alone (C − A = +0.163 [+0.083, +0.250]) | complete, tag `exp1-final` |
| **[Experiment 2](exp2/README.md)** | Do *executable* definitions encoded in an ontology (rule-defined classes, materialized before querying) beat the same definitions written as prose? | C2 − B+ = **+0.026** [0.000, +0.071]: **not supported**. Ontology rules and equivalent Python helpers tie exactly (C2 − B++ = 0.000, as predicted) | complete, tag `exp2-final` |
| **[Experiment 3](exp3/README.md)** | Do ontologies pay off with two sources that name the same entities differently (H1), and when definitions change over time (H2)? | TEST not run yet. DEV pilot: B3 1.00, C3 0.95 (1.00 after one clarity fix), LLM alone 0.64; H1 pre-registered as expected null on ceiling grounds | pre-registered and frozen |

All differences are mean paired F1 differences on the pre-registered exam questions, with 95% bootstrap confidence
intervals.

![Experiment 1: paired F1 differences with 95% confidence intervals](exp1/results/ci_differences.png)

The [research notebook](notebook/blast_radius.ipynb) walks through Experiments 1 and 2 with all figures, computed
directly from the committed results.

---

## What this means for ontologies

The usual pitch for ontologies in the age of AI goes like this: write down your business formally, in the standard
languages, and AI will reason about it more reliably. These experiments do not support that version of the claim.
In every head-to-head comparison where the same knowledge was available in another form, the formal ontology tied.

But three things clearly did matter, and they are all things an ontology is *supposed* to provide.

### 1. Sorting out what things are, before the AI sees anything

When two systems call the same service by different names, and some of their records are stale or contradictory, the
AI reading both raw sources scored 0.64 in Experiment 3's practice round. When the identities and conflicts were
resolved first, by a program applying a clear rulebook, it scored 0.95 to 1.00. The lesson: **an AI model is a poor
place to do data cleaning and matching. A layer in front of it that has already done that work is a very good one.**

### 2. Defining important ideas once, in a form a computer can execute

Ideas like "this service is down if any database it relies on is lost" caused most of the AI's mistakes when it had to
re-derive them from a written explanation every time. When those ideas were computed in advance and offered as a
simple lookup ("which services are down if Frankfurt fails?"), the mistakes disappeared, and the AI needed about a
fifth of the text and a quarter of the time to answer. **Definitions that are executable and shared beat definitions
that are only described.**

### 3. The format does not matter; the work does

Python code and an RDF/OWL ontology carrying the same resolved facts and the same executable definitions performed
identically. The ontology version also took more effort to build: in Experiment 3, 201 lines of conversion, rules and
schema against 83 lines of Python for exactly the same behaviour.

### The bottom line

The value of an ontology for AI is **operational, not logical**. What helps is a single, trusted layer that:

1. **resolves** what things are across every source system,
2. **computes** what they mean, using definitions written once and reused everywhere, and
3. **hands the AI a small, stable vocabulary** of things it can look up and act on.

Formal standards like RDF and OWL are one way to build that layer. On these tasks they were neither better nor cheaper
than ordinary code. The future of ontologies, on this evidence, is less about formal logic and more about building that
operational layer well.

---

## Where ontologies are heading: what this says about Palantir's approach

### What Palantir's Ontology is

Palantir is a data and AI software company whose platforms (Foundry, and AIP for AI applications) are built around
what it calls the **Ontology**. Despite the name, it is not a formal RDF/OWL ontology of the kind tested in
Experiment 1. It is an operational layer between a company's raw data and the people and AI systems that use it:

- **Objects.** Data from many source systems is mapped into business objects, such as a *Service*, a *Datacenter* or a
  *Customer contract*. One object can combine records from several systems that describe the same real-world thing.
- **Links.** Objects are connected by named relationships: a service *depends on* a database.
- **Logic.** Functions compute derived facts, and actions let users and AI make governed changes, with permissions and
  an audit trail.
- **AI on top.** AI assistants and agents work with these objects, links, functions and actions rather than with raw
  tables.

It is the best-known example of the "operational" kind of ontology that the previous section describes, so it is
worth asking what these experiments say about it: where they support the approach, and where they cut against it.

### Where the findings support it

- **Resolving data before the AI sees it is the right priority.** The biggest effect in this project came from
  reconciling conflicting sources up front (0.64 to 0.95-1.00 in Experiment 3's practice round). A layer whose main job
  is to merge many systems into one object per real-world thing targets exactly that.
- **Executable, shared definitions beat written explanations.** Computing "down" or "breached" once and exposing it as a
  lookup removed the errors that came from the AI re-deriving those ideas each time. Functions attached to objects do
  the same.
- **Not betting on formal logic is consistent with the evidence.** The formal RDF/OWL machinery added nothing
  measurable here, and Palantir's Ontology does not depend on it.

### Where the findings cut against it, or leave it unproven

- **The benefit is not specific to an "ontology" product.** In every comparison, ordinary, well-organized code carrying
  the same resolved data and the same definitions did as well as the ontology version, and it was cheaper to build (83
  lines of Python against 201 lines of conversion, rules and schema in Experiment 3). What helped was engineering
  discipline: resolve entities, define things once, expose simple lookups. A shared code library, a typed internal
  API or a well-maintained metrics layer can provide that too. On this evidence, the value lies in doing the
  integration work, not in the ontology as a category, and claims that the Ontology itself is what makes AI reliable
  go further than these results support.
- **Constraining the AI to predefined objects has a cost.** The pre-built vocabulary made anticipated questions easy,
  but questions the vocabulary did not cover got harder. In Experiment 1, on questions that needed calculations the
  ontology could not express (path lengths, path counts), the ontology setup scored 0.44 while the code setups scored
  0.89-1.00. An AI that can only act through predefined objects and actions is more reliable inside that boundary
  and less capable outside it.
- **Centralization also centralizes mistakes.** My experiments verified every resolution and every definition against a
  known answer key before any AI saw them. Real entity resolution is never perfect. In a single shared layer, one wrong
  merge or one wrong definition reaches every application and every AI agent at once, and the AI has no way to notice,
  because it trusts the layer. These experiments did not test imperfect resolution, so they cannot say how well any
  layer, Palantir's included, holds up when its own data is wrong.
- **Change is a double-edged sword.** Defining something in one place means a change only has to be made once. It also
  means one change can silently alter the answers of every consumer. Whether a central layer reduces or increases
  silent breakage is exactly what Experiment 3's maintenance test (H2) measures, and it has not been run yet.
- **Building and owning the layer is expensive, and it locks logic in.** The ontology versions here cost more to build
  than the code versions, even at small scale. In a commercial platform, modelling the business, mapping every source
  and keeping it current is substantial ongoing work, and business logic written inside one vendor's platform is
  harder to move than logic in open code or open standards.

### My conclusion

Palantir's approach aims at the right problem. These experiments suggest that grounding AI reliably is mostly a data
integration and definition problem, not a formal-logic problem, and an operational layer of resolved objects and
executable logic addresses that more directly than classic ontologies do. But the evidence also suggests the benefit
comes from engineering practices that are not unique to that product, that constraining AI to a predefined vocabulary
trades flexibility for reliability, and that centralizing definitions concentrates both their value and their errors.

These are inferences, not tests: I did not evaluate Palantir's software, and every experiment here uses synthetic data
and one AI model.

---

## What these experiments cannot tell you

- **The data is synthetic.** The companies are generated by a program. Real infrastructure is messier in ways a
  generator cannot fully imitate.
- **One AI model.** All results come from Haiku 4.5. A stronger or weaker model might behave differently.
- **One run per question** (Experiment 3 will use three). Small differences could be noise.
- **I built everything.** I wrote the generator, the questions, the answer key and every tool the AI setups used.
  That makes it easier to keep the comparisons fair, but it also means the questions fit the tools by construction.
- **Small numbers.** Each experiment has a few dozen exam questions, so breakdowns by size or question type are
  exploratory.
- **The cost of building an ontology is only partly measured** (lines of code, not people's time).

Each experiment's write-up lists its own limitations in full.

---

## Glossary

| Term | Meaning |
|---|---|
| **LLM** | Large language model: the kind of AI behind chat assistants |
| **Ontology** | A machine-readable dictionary and rulebook describing what exists in a domain and how it relates |
| **RDF / OWL** | Standard formats for writing ontologies |
| **SPARQL** | The query language used to ask questions of an RDF ontology |
| **Grounding** | Giving an AI real, structured information to work from |
| **Blast radius** | Everything that is affected when one part of a system fails |
| **Replica** | A backup copy of a service or database, often in another datacenter |
| **SLA** | Service-level agreement: a contract promising customers a level of availability |
| **CMDB** | Configuration management database: a company's inventory of its IT systems |
| **Entity resolution** | Working out that different names in different systems refer to the same real thing |
| **F1 score** | A 0-to-1 score for list answers that rewards finding all the right items and penalizes wrong ones |
| **DEV / TEST** | Practice questions (used to fix bugs) and exam questions (run once, at the end) |
| **Pre-registration** | Writing down and locking the analysis and success criteria before seeing the exam results |
| **Confidence interval** | A range of plausible values for a result; if it includes zero, the difference may be nothing |
| **Ceiling effect** | When scores are already near perfect, so no setup can show it is better |

---

## For technical readers

### Conditions, by experiment

- **Experiment 1:** A (LLM alone, graph in the prompt), B (Python sandbox over raw JSON), B+ (B plus prose schema
  documentation), C (SPARQL over an RDF graph with an RDFS/OWL schema, no reasoner).
- **Experiment 2:** B+ (prose definitions), B++ (prose plus Python helpers), C2 (ontology whose classes are
  materialized by SPARQL CONSTRUCT rules to a fixpoint before querying).
- **Experiment 3:** A3 (LLM alone, both exports in the prompt, two smaller graphs only), B3 (Python glue resolving
  entities, authority rules, stale records and definitions), C3 (the same resolution and definitions as an ontology
  with materialized rules). Primary test C3 − B3 with a cluster bootstrap by question text and graph seed, three
  repeats per question.

### Repository layout

```
exp1/                    Experiment 1 (frozen): ontology vs code vs LLM alone
  README.md              write-up        PREREG.md        pre-registration     PROMPT_LOG.md   tuning log
  ADDENDUM.md            post-freeze note on what the ontology was asked to do
  gen.py truth.py questions.py llm.py sandbox.py common.py run_*.py score.py plots.py schema.ttl
  data/ results/         graphs, questions, answer key; raw responses, scores, figures
exp2/                    Experiment 2 (frozen): executable definitions, ontology rules vs Python helpers vs prose
  README.md PREREG_EXP2.md LOG.md EFFORT.md
  gen2.py helpers.py rules.py ontology2.ttl docs.py questions2.py run2.py score2.py + checks
  data/ results/
exp3/                    Experiment 3 (frozen for TEST): two conflicting sources, changing definitions
  README.md PREREG_EXP3.md LOG3.md EFFORT3.md
  gen3.py truth3.py questions3.py glue.py to_rdf3.py rules3.py ontology3.ttl docs3.py run3.py score3.py + checks
  data/                  cmdb_*.json, monitoring_*.json, questions.json, rdf/
  data/hidden/           canonical graphs, entity-resolution keys, answer key (never shown to any condition)
notebook/                research notebook across experiments
tools/                   verify_frozen.py, run_exp2_check_docs.py
pyproject.toml           dependencies; makes exp1's shared modules importable everywhere
```

Experiments 2 and 3 reuse Experiment 1's modules (`truth`, `llm`, `sandbox`, `score`, ...) unmodified;
`pip install -e .` puts `exp1/` on the import path.

### Setup and reproduce

```
python -m venv .venv
.venv/Scripts/pip install -e ".[notebook]"      # Windows; use .venv/bin on Unix
export ANTHROPIC_API_KEY=...                     # only needed for new model calls

python tools/verify_frozen.py                    # every pre-registered file hash, exp1, exp2 and exp3
python exp1/test_score.py                        # exp1 scorer tests
python exp1/test_harness.py                      # exp1 offline harness tests (no API calls)
python exp2/verify_defs.py                       # exp2 helpers and rules reproduce ground truth
python tools/run_exp2_check_docs.py              # exp2 definitions present in every condition's docs
python exp2/test_run2.py                         # exp2 offline harness tests
python exp3/truth3.py                            # exp3 exports consistent with the hidden canonical graph
python exp3/verify3.py                           # exp3 glue and rules match the key and ground truth
python exp3/test_run3.py                         # exp3 docs check, hidden-data guard, offline reproduction

python exp1/score.py test                        # exp1 tables and the paired bootstrap
python exp2/score2.py test                       # exp2 cluster and per-question bootstraps
```

Every model call is cached on disk (`exp1/cache/`, git-ignored), keyed by condition, model, prompt and token limit,
so re-runs of completed experiments cost nothing. Raw responses for every question are in each experiment's
`results/`.

### Integrity

- **Pre-registration before TEST:** `exp1/PREREG.md`, `exp2/PREREG_EXP2.md` and `exp3/PREREG_EXP3.md` were committed
  before their TEST runs and list file hashes; `tools/verify_frozen.py` checks them. The hashes were taken on
  Windows, where Git may rewrite line endings on checkout, so the checker also accepts the LF and CRLF forms of each
  file and reports which matched.
- **Frozen tags:** `exp1-final` and `exp2-final` mark each experiment exactly as reported.
- **Logged changes:** every prompt, question, harness and post-run change is logged with its reason
  (`exp1/PROMPT_LOG.md`, `exp2/LOG.md`, `exp3/LOG3.md`, and [PROGRESS.md](PROGRESS.md) for every commit). Moving
  Experiment 1 into `exp1/` on 2026-10-19 changed no content and no result, number or decision rule.
- **Model and cost:** Haiku 4.5 at temperature 0 throughout. Spend so far: Experiment 1 $3.08, Experiment 2 $0.84,
  Experiment 3 $0.68 (DEV pilot).
