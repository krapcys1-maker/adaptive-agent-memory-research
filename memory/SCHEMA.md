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

## Changing this schema

The canonical log may never be rewritten. This is enforced, not merely
recommended: CI's canonical-store guard fails any pull request that removes a
line from `events.jsonl`, and changing a line counts as a removal plus an
addition. In-place migration is mechanically impossible.

Schema evolution therefore happens by **upcasting**, implemented in
`tools/project_memory/upcast.py`:

- events already written stay on disk exactly as written;
- the reader presents an older event in the shape of the current version;
- new events are written at the current version;
- a log holding several versions at once is the normal steady state.

Two alternatives were considered and rejected. Rewriting in place destroys the
record of what was actually written. Appending a translated copy of every event
doubles the log, creates two records of one observation, and makes `supersedes`
ambiguous, because a copy is not a revision of the original.

### Adding a version

1. Write a function taking an event at version N and returning it at N+1.
2. Register it in `UPCASTERS`.
3. Raise `SCHEMA_VERSION` in `memory_store.py`.
4. Add cases to `tests/test_upcast.py`.

An upcaster must be **total** — defined for every event the previous version
permitted — and must **never drop a field**. Both properties are tested against
the real canonical log, not against a fixture, so a migration cannot silently
skip records or lose data.

An upcaster must also not invent information. Where the older version genuinely
did not record something, the upcast records that it is unknown rather than
guessing, because a guess written into an upcast reads afterwards as recorded
evidence.

### Known limitation

The canonical-store guard runs on pull requests only. A direct push to the
default branch bypasses it. Anyone with push access can therefore rewrite the
log without CI objecting, and the protection is procedural at that point rather
than enforced.
