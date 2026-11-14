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
