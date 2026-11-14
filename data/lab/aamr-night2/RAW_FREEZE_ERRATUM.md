# Erratum to `raw-freeze.json` (AAMR-NIGHT-2)

Added 2026-11-14, when the experiment was imported into this repository, following the maintainer's ruling for the sibling
experiment AAMR-NIGHT-1 (publish the raw freeze with an erratum). **`raw-freeze.json` is published byte for byte as the
experiment wrote it** (SHA-256 `c693308d59e1275ce6b452538e3fb087112e44e761249ca1f414da64ada4a9f9`). No result, hash or number changes.

## The field

`raw_root` is the absolute path of the folder, **on the machine that ran the experiment**, that held the raw run (sessions,
attempts, ledgers). It is a Windows drive path, recorded by `scripts/aamr_night2.py` (`out = {"frozen_at": ..., "raw_root": str(RUN), ...}`). It is not
a path inside this repository and means nothing on any other machine.

## What this means for a reader

- The manifest is still readable and checkable: its `files` entries are paths **relative to the raw run folder** with the SHA-256 of
  19 raw files, and the sums do not depend on `raw_root`.
- **The raw run itself is not in this repository.** Nothing here lets a reader recompute those sums.
- The recorded drive path is not a secret and gives no access to anything, but it is a detail of one person's machine. It is kept
  because the file is a frozen artifact and no other file pins its hash.

## Nothing else changed

The specification, protocol, configuration, report and results were imported unchanged. The five commits were cherry-picked with `-x`
from the local branch `claude/aamr-night2-2026-11-13`; their content (checked by Git blob) is identical to that branch.

## Where the raw run is now, and the check (added 2026-11-14)

The old root folder, the old `GH_REVIVAL` folder and the run folder named by `raw_root` no longer exist under those names: the project's working root was reorganised on 2026-11-14.
The raw run of NIGHT-2 now lives **outside Git, in the private area of the working root**, at `private/gh-revival/aamr-night2-2026-11-13/run` (a path relative to the working root; the folder is not part of
this repository and is not published). **All 19 SHA-256 sums of `files` were recomputed on 2026-11-14 at that place and equal the sums in `raw-freeze.json`: 19 of 19 match, 0 missing, 0 different.**
`raw-freeze.json` itself was not changed (its bytes still carry the old `raw_root`). It is also still present in the Git history, in the pull-request refs and in any clone or fork; a later commit
cannot remove it, and the project does not rewrite history or force-push. What the old path reveals is the names of directories of the old layout; it contains no user name and no secret.

New manifests of this project use paths relative to the run folder and do not record an absolute `raw_root`; the export flow rejects a manifest that does (`docs/00-project/coordinator-export-flow.md`).
