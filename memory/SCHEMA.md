# Memory event schema

Each line of `events.jsonl` is one independent JSON object.

Required fields:

- `schema_version`: integer schema version;
- `id`: stable `PM-YYYYMMDD-xxxxxxxx` identifier;
- `operation`: `create` or `supersede`;
- `kind`: `candidate`, `constraint`, `decision`, `failure`, `finding`, `hypothesis`, `procedure`, `question`, or `session`;
- `title`, `summary`, `created_at`, `confidence`, and `status`.

Provenance and relationships:

- `source_refs`: URLs, DOI/arXiv identifiers, repository paths, commits, or experiment artifacts;
- `supersedes`: the prior event ID when a conclusion is revised;
- `supersession_reason`: why the revision was required;
- `related_ids`: related memory IDs;
- `tags`: retrieval facets, not substitutes for evidence.

The active view is derived by replaying events in order. A superseded record remains queryable by exact ID and visible in the timeline but is removed from ordinary search results.
