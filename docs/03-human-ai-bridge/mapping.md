# Human-to-AI Memory Mapping

Status: in-progress

| Human-memory finding or construct | Abstract problem | Candidate AI mechanism | Important mismatch | Test |
|---|---|---|---|---|
| Limited working memory | scarce active capacity | token-budgeted working set | context tokens are passive input, not a full executive system | dynamic builder vs fixed top-k |
| Rapid episodic learning | retain individual experience quickly | append-only event log | digital events can be copied exactly | raw episode ablation |
| Slow semantic learning | extract regularities without overwriting specifics | evidence-linked consolidation | LLM summaries can fabricate or overgeneralize | reversible vs destructive consolidation |
| Complementary learning systems | balance specificity and generalization | separate episodic and semantic/procedural stores | no direct anatomical equivalence | dual store vs homogeneous store |
| Pattern separation | reduce interference among similar events | entity/time/task scoped indexes | embeddings often collapse similar cases | scoped retrieval vs flat vector search |
| Pattern completion | recover an episode from partial cues | graph and multi-hop cue expansion | completion can introduce hallucinations | evidence recall under weak cues |
| Encoding specificity | retrieval depends on contextual match | preserve source context and multiple indexes | future queries may use different vocabulary | context metadata ablation |
| Replay | revisit experiences offline | background consolidation and evaluation | replay consumes compute and can reinforce errors | scheduled replay vs none |
| Emotional modulation | consequential events receive priority | outcome-conditioned salience | signals are not emotions; extreme salience can distort | salience features vs relevance/recency |
| Prediction error | unexpected outcomes drive updating | surprise score and belief revision | prediction quality may be poorly calibrated | calibrated PE feature ablation |
| Reconsolidation | recalled memories may update | versioned revision after use | digital systems need not overwrite the original | immutable history vs in-place rewrite |
| Interference | similar memories compete | diversity, scope, and contradiction-aware ranking | storage is cheap but attention remains scarce | distractor scaling curves |
| Retrieval practice | successful recall can strengthen access | utility-weight update after verified use | frequency can create popularity bias | verified utility vs access frequency |
| Adaptive forgetting | reduced access may aid behavior | archive or suppress low-value memories | deletion creates irreversible risk | suppression vs deletion vs full retention |
| Metamemory | know whether one knows | search trigger and confidence model | LLM verbal confidence is often miscalibrated | trigger calibration and miss cost |
| Prospective memory | remember to act later | condition-based intentions | requires reliable external triggers | delayed-intention benchmark |

## Rule

The mapping table generates hypotheses. It is not evidence that an AI component reproduces a biological mechanism.
