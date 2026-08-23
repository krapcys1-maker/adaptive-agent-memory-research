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

### Version 2: bitemporal

Version 2 adopts the SQL:2011 two-axis model, following
`docs/04-systems/temporal-memory-model-comparison-v0.md`.

| Field | Axis | Meaning |
|---|---|---|
| `created_at` | transaction | when the record was written |
| `expired_at` | transaction | when the record was withdrawn — **derived** |
| `valid_from` | valid | when the fact became true |
| `valid_to` | valid | when the fact stopped being true — **derived** |

Plus `claim_class` (`dispositional`, `state`, `unclassified`) and, on a
supersession, `supersession_kind` (`succession`, `correction`, `unclassified`).

**The two end-of-interval fields are derived, never stored.** Graphiti, the
reference implementation, ends a prior fact by mutating it. A graph database
permits that; an append-only log does not, and CI enforces it. So `valid_to` and
`expired_at` are computed at read time from the successor, exactly as the
active/superseded view already is:

- `valid_to` of a superseded record = the successor's `valid_from`
- `expired_at` of a superseded record = the successor's `created_at`

This is better than a literal port. A stored end can drift from the revision
that caused it; a derived end cannot, because there is only one place it comes
from.

**Correction versus succession.** Two axes make separate operations
unnecessary, but the log must record which happened, because it changes what is
derived. A *succession* means the world changed, so `valid_to` is derived and
the prior record remains a historical truth. A *correction* means the record was
wrong, so nothing about the world changed and only `expired_at` is derived.
Every version-1 supersession is `unclassified` and derives no `valid_to`:
guessing would write an interval nobody observed into what reads afterwards as
evidence.

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
