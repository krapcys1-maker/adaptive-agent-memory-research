# Compression source-code reproducibility audit

Status: in-progress

Audit date: 2026-08-22. This checks public artifact availability and immediate executability. It is not a scientific reproduction.

## Jakob and Gershman rate-distortion working memory

- Repository: https://github.com/amvjakob/wm-rate-distortion
- Audited revision: `ac3210ae90fb28ef9edc97f0651b3ff3b136eef2` on `main`
- Last commit in the audited history: 2022-02-26
- Repository metadata at audit: public, not archived, no detected license, no tags, two commits
- Paper locator: Source code section, article PDF p. 27 / extracted full-PDF page 46

### Present

- Seven Julia/Jupyter notebooks corresponding to paper Figures 2–8.
- Julia source for the population model, circular statistics, serial-dependence analysis, plotting, and bootstrap helpers.
- Fixed simulation seed machinery in `src/model.jl` and `src/utils.jl`.
- Pre-rendered PDF figures.
- README links to the seven original data publications.

### Missing or unresolved

- No `Project.toml` or `Manifest.toml`; package names are discoverable but exact dependency versions are not pinned.
- No license file or GitHub-detected license. Inspection is possible, but reuse rights are not established.
- The README describes a repository-local simulation `data/` directory and a sibling experimental-data directory; neither is present at the audited revision.
- Notebooks reference `.jld2`, MATLAB, XLSX, and pickle files that are not bundled, including neural data.
- No automated clean-environment runner or tests.
- The paper reports Julia 1.6.2; Julia is not installed in the current project environment.
- A notebook and figure path exist for Figures 2–8, but the exact Table 1 random-effects Bayesian model-comparison pipeline is not clearly packaged as a standalone reproducible script in this first audit.

### Reproduction status

`blocked-artifacts`, not `failed-result`. The result has not been contradicted; the public repository as audited is insufficient for a clean reproduction without reconstructing dependencies and obtaining source datasets.

### Next safe actions

1. Build a disposable Julia 1.6.2 environment and infer the minimum package set without changing the project runtime.
2. Resolve each dataset from the original publication/repository and record license and checksum.
3. Identify whether eLife supplementary artifacts contain the missing environment, data, or later code revision.
4. Reproduce one synthetic figure first; only then attempt human/monkey reanalyses.
5. Compare numerical outputs and source-selection/exclusion rules, not only rendered plot similarity.

## DeMem

- Paper: https://arxiv.org/abs/2605.10870v1
- Paper version audited: 11 May 2026

The paper describes algorithms, prompts, hyperparameters, baseline asset use, and repeated-run scoring, but the full-text search found no project-code URL. GitHub repository search by title/method on 2026-08-22 returned no matching public repository, and direct checks of plausible author/repository paths did not resolve.

Reproduction status: `blocked-no-public-code-found`. This is a time-stamped search result, not a claim that code does not exist or will never be released. Recheck arXiv versions, author pages, and archival supplements before a reproduction attempt.

## Compaction survey reference experiment

The full paper describes its benchmark/reference experiment, but the read version did not expose a directly identified code artifact in the source-code search. Reproduction status: `artifact-search-pending`. Its Figure 6 numbers remain illustrative reported evidence.

## Gate consequence

None of the three computational result families audited here currently satisfies the project's independent-reproduction gate. The correct response is to retain them as mechanism candidates, implement only a minimal independent benchmark from the written protocol, and avoid treating paper scores as a baseline reproduced by this project.
