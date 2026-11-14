# Resolver variants of the T39 mutation check (task 11): the code

**Status: reproduction material, added on 2026-11-14 to what [the task-11 record](../response.md) already published.** The mutation check of mission T39-REVISION ran the unmodified REV-V0 runner and three variants of its resolver. The raw output of every run was
published, but the code of the variants was not: it existed only in the coordinator's sandbox. The three diffs here are that code, cut from the sandbox copies in which task 11 (a reproduction task run in isolation) executed the variants; nothing in them is new.

Each diff changes one or two lines of [`scripts/run_revision_v0.py`](../../../../../../scripts/run_revision_v0.py) of this repository (SHA-256 `d34f90ab1550b78f9ddcb15d3562df256807d83731de231273b83f4bc8cd3113`). Line endings were normalised when the diffs were cut.

| Diff | Change | Output it reproduces | SHA-256 (first 16) |
|---|---|---|---|
| `M1.diff` | mutant M1: the filter `created_at <= T` is removed from the `as_known_at` branch | [`../variant-M1-cmd-0.txt`](../variant-M1-cmd-0.txt) | `eb2dee65ee51bdf3` |
| `NOFALLBACK.diff` | the fallback `or live` is removed from the `valid_at` branch; an empty set returns nothing | [`../variant-NOFALLBACK-cmd-0.txt`](../variant-NOFALLBACK-cmd-0.txt) | `ae32cda10d86f74b` |
| `M1_NOFALLBACK.diff` | both changes together | [`../variant-M1_NOFALLBACK-cmd-0.txt`](../variant-M1_NOFALLBACK-cmd-0.txt) | `7708a1e08047378b` |

## How the reproduction was checked

On 2026-11-14 each diff was applied to a scratch copy of `scripts/run_revision_v0.py` placed next to a copy of `data/lab/pmlab-revision-v0/`, and the script was run there (`python scripts/run_revision_v0.py`).
The standard output of all three variants, and of the unmodified script, is **byte-identical** (line endings aside) to the published files `variant-*-cmd-0.txt` and `cmd-0.txt`.

To repeat it, copy the script and the data folder to a scratch directory (the script reads and writes under its own directory), run `patch -p1 < <name>.diff` there, then run the script and compare its output with the file named above.
Do not apply a diff inside this repository: the REV-V0 package is frozen.
