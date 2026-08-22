# Working Definitions

Status: in-progress

These are operational project definitions, not claims that all research communities use the terms identically.

| Term | Working definition |
|---|---|
| Context window | Tokens currently supplied to the model for one inference or interaction cycle. |
| Working set | The subset of task state and retrieved memory made immediately available to the agent. |
| Memory event | An immutable observation of something that happened, with time, source, actor, and provenance. |
| Memory object | A durable record used by the memory system: episode, fact, belief, rule, decision, intention, relation, or artifact reference. |
| Episode | A bounded event or sequence tied to a particular context and time. |
| Semantic memory | Generalized facts, concepts, relations, and beliefs that need not preserve full event detail in their working form. |
| Procedural memory | Knowledge about how to perform an action or solve a class of problems. |
| Decision memory | A decision, alternatives considered, reason, evidence, and conditions for revisiting it. |
| Failure memory | A failed attempt, observed symptoms, costs, root cause if known, recovery, and lesson status. |
| Prospective memory | An intention to act when a future time, event, or condition occurs. |
| Provenance | Traceable links from a derived memory to its source events and transformations. |
| Consolidation | Creating or updating a generalized representation from one or more episodes. |
| Reconsolidation | Updating a memory after reactivation; an empirical concept in neuroscience and a proposed design operation in AI. |
| Retrieval | Selecting stored information in response to a cue or predicted need. |
| Context construction | Choosing, ordering, compressing, and formatting information supplied to the model. |
| Retention | Maintaining a memory or its retrieval accessibility over time. |
| Forgetting | Reduced availability or accessibility; may mean suppression, archival, index removal, corruption, or deletion and must be qualified. |
| Salience | A signal that an event deserves processing priority; not identical to usefulness. |
| Future utility | Improvement attributable to a memory on later objectives, net of retrieval and processing cost. |
| Retrieval frequency | Number of retrievals; an exposure measure, not proof of utility. |
| Counterfactual utility | Difference between outcomes with and without access to a memory, under comparable conditions. |
| Memory strength | A model-specific variable affecting retention or retrieval probability; not assumed to be a literal biological quantity. |
| Stale memory | A memory whose validity conditions no longer hold. |
| Contradiction | Two records that cannot both be valid under the same entity, time, scope, and interpretation. |
| Supersession | A newer state replaces an older state for current use without erasing historical truth. |
| Operational affect | Project shorthand for outcome-derived signals such as surprise, reward, effort, severity, or rollback cost; not machine emotion. |
