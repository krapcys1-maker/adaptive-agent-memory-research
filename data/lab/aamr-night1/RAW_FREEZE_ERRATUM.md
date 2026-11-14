# Erratum to `raw-freeze.json` (AAMR-NIGHT-1)

Added 2026-11-14, when the experiment was imported into this repository, on the maintainer's decision to publish the raw
freeze with an erratum. **`raw-freeze.json` is published byte for byte as the experiment wrote it** (SHA-256
`4190413d8c543c68fca428c1f55d8a41cbf0a99e4c2ca0a760e6dfaf3a30afdd`). No result, hash or number changes.

## The field

`raw_root` is the absolute path of the folder, **on the machine that ran the experiment**, that held the raw run
(sessions, attempts, ledgers). It is a Windows drive path. It is not a path inside this repository and means nothing on any
other machine. It was recorded by `scripts/aamr_night1.py` (`out = {"frozen_at": ..., "raw_root": str(RUN), ...}`), which
writes the run folder as the program saw it.

## What this means for a reader

- The manifest is still readable and checkable. The `files` entries are paths **relative to the raw run folder** with the
  SHA-256 of 17 raw files, and the sums do not depend on `raw_root`.
- **The raw run itself is not in this repository.** Nothing here lets a reader recompute those sums. The author's re-check
  after the run (0 mismatches of the 17 sums) is reported in `WNIOSKI.md`, section 0; it was not independently repeated.
- `scripts/aamr_night1_followup.py` reads `raw_root` from this file to find the raw run, so it cannot be rerun from a
  clean clone: the run folder is absent and the recorded path points to a different machine. Making the script accept a
  path from the command line would be a new version of the script; it was not done here, because the script is part of
  the experiment as it ran.
- The recorded drive path is not a secret and gives no access to anything, but it is a detail of one person's machine.
  It is kept because the file is a frozen artifact and no other file pins its hash.

## Nothing else changed

The experiment's protocol, configuration, results and report were imported unchanged in substance. The only edits made on
import, in the test file, are described in the commit messages of this branch.

## Where the raw run is now, and the check (added 2026-11-14)

The old root folder, the old `GH_REVIVAL` folder and the run folder named by `raw_root` no longer exist under those names: the project's working root was reorganised on 2026-11-14.
The raw run of NIGHT-1 now lives **outside Git, in the private area of the working root**, at `private/gh-revival/aamr-night1-2026-11-12/run` (a path relative to the working root; the folder is not part of
this repository and is not published). **All 17 SHA-256 sums of `files` were recomputed on 2026-11-14 at that place and equal the sums in `raw-freeze.json`: 17 of 17 match, 0 missing, 0 different.**
`raw-freeze.json` itself was not changed (its bytes still carry the old `raw_root`). It is also still present in the Git history, in the pull-request refs and in any clone or fork; a later commit
cannot remove it, and the project does not rewrite history or force-push. What the old path reveals is the names of directories of the old layout; it contains no user name and no secret.

New manifests of this project use paths relative to the run folder and do not record an absolute `raw_root`; the export flow rejects a manifest that does (`docs/00-project/coordinator-export-flow.md`).
