# Executable path options, same frozen capture

The first unscored v3 question traces show a routing defect: both models choose
relations that do not form a complete executable path. Relation names alone do
not explain their learned meanings (for example broad associated_with labels).
Complete and freeze both 100-question v3 runs; do not remove those negatives.

Before scoring/revising any individual answer, implement a generic constrained
planner: enumerate actual outgoing graph paths from literal scoped anchors,
up to six steps, 96 distinct relation schemas and 512 expansions. Present compact
option IDs, relation sequences and learned literal sentence shells. **Do not
show terminal values or gold**. The model chooses an option; code executes it
with provenance. No extra facts, world knowledge, answer rewriting or new capture.
This remains a system-computed answer, not a raw reader answer. Free-query v3
and constrained v5 are separate development mechanisms on spent questions.

Apply the same complete 100 questions to local and Flash selection. Local uses
a native enum schema; Flash uses JSON mode. Record search/input truncation and
missing options. These can cause real misses, and must not disappear from scores.
No model retries or question-specific rules. Freeze all raw outputs before score.

Extend the local phase bound by one full 103-call planner phase (seventh total);
the API cap remains cumulative 400 attempts/$2 from v2, including the failed
83-call capture and both Flash planner runs. A later transfer run needs its own
explicit source selection/amendment; this is not a universal-memory validation.
