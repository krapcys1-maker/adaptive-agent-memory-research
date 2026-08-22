# Query-normalization × history-scope diagnostic

Status: completed oracle-intervention diagnostic; not a deployable comparison

Using SQLite FTS5 on the 24-query challenge, raw/all-record retrieval reached Recall@5 `0.40`. Oracle-normalizing each answerable query to exact entity, topic, and ISO date raised recall to `1.00` even without history scoping. Oracle history scoping alone changed recall by `0.00`; combining it with normalization added nothing beyond normalization.

All FTS5 arms retained forbidden-version intrusion `1.00` and unanswerable abstention `0.25`. Therefore query interpretation explains target discovery in this fixture, while validity/context selection remains unresolved after discovery.

Both interventions consume registered gold metadata. The result identifies a potential bottleneck and ceiling; it does not validate a parser.
