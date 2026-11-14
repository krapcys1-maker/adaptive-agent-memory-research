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
