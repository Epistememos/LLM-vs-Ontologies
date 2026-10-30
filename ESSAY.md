# Essay: what these results suggest about operational ontologies

This essay is commentary and inference, not a tested result. I did not evaluate Palantir's software; it reads the
findings of the three experiments in this repository (see the [README](README.md), and the
[consolidated report](REPORT.md)) against one well-known operational ontology. Where it says "the previous section", it
refers to the README section "What this means for ontologies".

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
  reconciling conflicting sources up front (0.47 to 1.00 on Experiment 3's exam questions). A layer whose main job
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
  means one change can silently alter the answers of every consumer. Experiment 3's maintenance test (H2, two changes,
  tried once each) points both ways. The ontology, built before the AI was involved, failed loudly when a field was
  renamed, while the AI patched around the same failure in the code version and gave 18 silently wrong answers. But a
  changed definition raised no error in either setup: both kept computing the old meaning until they were edited. A
  central layer makes breakage visible only if it checks its inputs before anyone uses it, and nothing catches a
  definition that is wrong but valid.
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
