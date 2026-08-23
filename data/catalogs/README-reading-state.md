# Reading state

`papers-curated.csv` carries two separate columns that are easy to confuse.

| Column | Answers | Example values |
|---|---|---|
| `status` | what kind of publication is it | `peer-reviewed-primary`, `preprint`, `review` |
| `reading_state` | how far have *we* engaged with it | `unknown`, `discovered`, `screened`, `abstract-read`, `full-read` |

Before this column existed the catalog could say a paper was peer-reviewed and
could not say whether anyone had opened it, while `CONTRIBUTING.md` required a
reading note to follow reading the source rather than its abstract. Nothing
recorded which had happened.

## Vocabulary

- **`unknown`** — engagement was never recorded. Every row carried this when the
  column was introduced. It is not a synonym for unread; it means the record
  does not say.
- **`discovered`** — found by search or citation. Nobody has looked at it.
- **`screened`** — title and abstract judged for relevance; an include or
  exclude decision exists.
- **`abstract-read`** — a claim was extracted from the abstract. The ledger
  marks such claims `abstract-extracted`.
- **`full-read`** — the source was read in full and a note exists under
  `docs/07-literature/full-read-notes/`.

## Why the existing rows were not backfilled

The audit found 18 catalogued sources whose URL appears in a full-read note, and
that number is a **lower bound**: a note naming a work by title alone is missed.
It is not a basis for assigning a state to 174 rows.

Assigning a reading state is a judgement about what was actually read, and a
guess written here reads afterwards as a record. So every row starts at
`unknown` and is corrected only by whoever actually knows.

## Raising a state

Move a row to `full-read` in the same change that adds its note. Move it to
`abstract-read` in the same change that adds an abstract-level claim. A state
raised without the corresponding artifact is a claim about work that left no
trace.
