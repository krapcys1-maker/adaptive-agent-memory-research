# Erratum: machine-local paths in the published K1 files (AAMR-K1)

Added 2026-11-14, when the K1 executor folder was imported into this repository.

## What is published byte for byte, and why

The following carry the **absolute Windows paths of the machine that ran K1** (a drive letter, the executor folder, the maintainer's
other local folders and the user profile folder) and are published **exactly as they ran**, because their bytes are pinned and
editing them would silently change a frozen artifact:

- `spec/SPEC_K1_PLACEBO_v1.0.1.md` and `spec/FREEZE.json` (the specification is pinned by `FREEZE.json`, which also lists external
  references by their absolute paths);
- `executor/code/k1_config.json`, `executor/code/k1_lib.py`, `executor/code/prepare.py` and `stim/k1_l6a_allow.json`
  (pinned by the L8 manifest: 29 of 29 pinned files are published unchanged, see `meta/manifest-L8-files.json`);
- the executor's tests and tools (`executor/tests/*`, `executor/tools/*`), which are the code that was run and were not edited to remove paths.

The paths are not secrets and give access to nothing, but they are details of one person's machine and they mean nothing on any other.
Making the code path-independent would be a new version of the executor; it was not done, because the code is part of the experiment as it ran.

## What was edited, and how to see it

Five documents that no manifest pins had their machine-local paths replaced by `[machine-local path omitted]`; nothing else in them changed.
They are listed in `PUBLISHED_FILES.json` with `sha256_original` (the hash of the file before the replacement), `sha256` (as published) and the
number of replaced paths: `decisions/DZIENNIK_DECYZJI_K1_v1.0.1.md`, `decisions/T1_T12_I_ZGODY.md`, `decisions/RAPORT_GO_NOGO_K1.md`,
`decisions/CHECKLISTA_STARTOWA_K1.md` and `executor/EXECUTOR_README.pl.md`. Every other file is byte-identical to its source.

## What the L8 manifest looked like

The executor's manifest `MANIFEST.json` was kept private because, besides the 29 file hashes, it lists the Python start-up files installed on the
machine (they name unrelated projects). `meta/manifest-L8-files.json` keeps its `files` mapping with the hashes unchanged and the paths made relative.

## Where the named folders and the raw run are now, and the check (added 2026-11-14)

The folders that the absolute paths in the frozen files name were moved on 2026-11-14 into the private area of the working root (outside Git, not published):
the K1 executor folder is now `private/k1-executor` and the 2026-11-13 audit folder `private/legacy/aamr-audit-2026-11-13`. The coordinator's own folder was not moved.
The raw run (`private/k1-executor/base/run`) was checked on 2026-11-14 against `out/raw-freeze.json`, whose paths are relative to the run folder:
**21 of 21 SHA-256 sums equal, 0 missing, 0 different.** The frozen files were not edited; the old absolute paths remain in them (and in Git history) as explained above.
