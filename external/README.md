# External Repository Cache

`external/repos/` contains shallow local clones created from `data/catalogs/repositories-seed.csv`.

The clones are intentionally ignored by Git. They retain their original licenses and are not part of this repository's licensed content. Exact downloaded revisions are recorded in `data/catalogs/repository-revisions.csv`.

`external/datasets/` contains ignored public-dataset snapshots. A snapshot enters an experiment only through a Git-tracked manifest that records its repository revision, byte size, SHA-256, declared license, selection rule, and redistribution boundary. Dataset content is never silently copied into this repository.
