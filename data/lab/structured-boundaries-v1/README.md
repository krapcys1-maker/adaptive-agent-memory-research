# Boundary repair v1 — engineering result

Follows [the preregistered plan](PLAN.md), frozen at `0c99959`, and issues [106](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/106)/[107](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/107). Original modules/results are unchanged; this is the implementing agent's development evidence, not independent review or an end-to-end memory improvement.

## New entry points

- `tools/structured_memory_v3.py`: exact whole-text reuse of prior model interpretations within scope/source policy and available recording time, rejecting disagreement; persisted exact derivations record source IDs. Unseen text delegates to fresh caller/model interpretation. Plans validate against visible scope/time predicates.
- `tools/structured_paths_v1.py`: read-only query view, provenance-indexed/time-bounded shells, options and packets with mandatory query clocks. No provider imports/global controller hooks. Query result copies prevent callers poisoning memoized state.
- `tools/structured_memory_cli_v2.py`: offline `source`, `extract`, `cache`, `replay`, `resolve`, `query`, `packet`, `status`. No model/key. `extract` accepts an externally supplied interpretation, not a semantic certificate. The caller owns authentication, clock and source authority.

Tests: 347 focused checks including old-version regressions, exact positive replay/reopen, rejected conditional/compound/negated/quoted/Unicode variants, conflicting derivations, forged template writes, actual CLI round trip and 288 counterfactual scope/time/order fixtures. All passed before the final full-suite check. These are engineering cases, not 347 independent memory tasks.

## Compatibility and cost

Offline [MAB compatibility](mab-compatibility.json) compares all 100 model-visible path packets and re-executes 200 saved local/Flash plans. No differences/failures, no model calls or gold read, original source hash unchanged. Only this already-spent all-sources-available snapshot is covered. Legacy accepted claims are preserved, not revalidated or retroactively repaired.

**Exact-only cache has zero reuse opportunities for the 18,223 sources previously served by learned shells, using the existing model interpretations.** This is a substantial cost/coverage loss, not a free improvement. Recapture would require additional extraction decisions; that recapture was not performed. Do not adopt this policy as an efficient general solution on the strength of green tests. It is a conservative fallback and explicit baseline for a future justified generalization mechanism.

An initial offline diagnostic was stopped before completion because repeated per-plan anchor/catalog scans made packet validation costly. Its source bytes and incomplete-run receipt were retained privately. The query view now memoizes immutable scope/time catalogs and question anchors; outputs are copied to callers. The completed rerun uses the same fixed questions/conditions. No benchmark metric or frozen v5 code was changed.

## Decision and next work

Accept the demonstrated packet/time/scope boundary behavior and exact-replay guard as an engineering successor, with original semantic correctness and efficient generalization still open. Do not describe A01 as solving arbitrary extraction, nor A02/A03 as caller authentication or constant-time security. Whole-source supersession granularity and broad evidence attribution remain as audited.

Next execute the separately frozen [whole-family reader controls](../h1-obsolete-controls-v1/PLAN.md) for #108. They address evidence use/interference, not this cache policy. A changed reader mechanism must later face all H1 families and fresh data at disclosed inference/context cost. No general readiness, vendor superiority, deployment or independent confirmation follows here.
