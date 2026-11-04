# November laboratory map

Snapshot: 2026-11-04. Read the linked README's latest results/amendments as well as its original preregistration header. This map describes the research instruments and recorded status; a passing software test is not a successful research result.

The [delivery-state page](../00-project/delivery-state-2026-11-04.md) explains what is implemented and what a complete agent still needs. Later evidence: [public ranking/gate evaluation](../../data/lab/lexical-gate-eval-v1/README.md), [retrieval costs](../../data/lab/retrieval-cost-v1/README.md), [LifeSim development diagnosis](../../data/lab/lifesim-development-diagnosis-v1/README.md), the [local typed-fact reader pilot](../../data/lab/nie-local-reader-v1/README.md), and [matched Qwen 14B/Flash comparison](../../data/lab/reader-model-compare-v1/README.md). Further evidence: [hard external diagnostic](../../data/lab/hard-memory-external-v1/README.md) and [project delivery audit](../00-project/project-delivery-audit-2026-11-04.md). These additions do not change the clean-clone timing snapshot below.

## Tracks

| Track and purpose | Code | Data and privacy | Tests / measured time | README of record and status |
| --- | --- | --- | --- | --- |
| AAM: offline tests of memory for a writing agent | [writer simulation](../../scripts/writer_memory_sim.py), [follow-up](../../scripts/followup_memory_sim.py), [replay](../../scripts/replay_memory_sim.py), [engagement](../../scripts/engagement_signal.py) | `data/lab/aam-*`; synthetic fixtures public where released, real-account text/judgments private and aggregates public | A below, 29.5 s; full project gate covers the other runners | Experiment index below. Results exist; exploratory findings retain their stated limits and errata. |
| Persona battery: facts, consistency, leakage and account-nature probes | [new entry point](../../scripts/persona_battery_v1.py), preserved [v0](../../scripts/persona_battery.py) | [v0 aggregates](../../data/lab/aam-p-persona-v0/results.json); editorial card, items, answers and labels private | A below, 29.5 s | [v0 results](../../data/lab/aam-p-persona-v0/README.md#results-2026-11-02); [v1 integrity successor](../../data/lab/aam-p-persona-v1/README.md) implemented, with no new model experiment. Use v1 for new runs. |
| WMB: measurement validity, retrieval comparisons and contracts | [statistics](../../scripts/wmb/stats.py), [contract](../../scripts/wmb/contract.py), [retrieval benchmark](../../scripts/wmb/retrieval_bench.py) | [slice 0](../../data/lab/wmb-v0/slice0/), [R1](../../data/lab/wmb-r1-retrieval/); live texts/pair labels private, aggregates public | W below, 24.234 s | [slice 0](../../data/lab/wmb-v0/slice0/README.md), [R1 results](../../data/lab/wmb-r1-retrieval/README.md#results-2026-11-02). Completed measurements; R1 issued no preregistered verdict after a judge-control failure. Further tracks remain planned in the [specification](memory-benchmark-spec-v0.md). |
| Memory kernel: thresholded injection, no-future filtering, provenance log and reference guard | Frozen [0.1.0](../../scripts/wmb/memory_kernel.py), live [0.2.0](../../scripts/wmb/kernel/memory_kernel.py), [mutation runner](../../scripts/wmb/mutate_kernel.py) | Synthetic tests; production inputs/logs stay outside research artifacts | K below, 23.062 s; M1/M2, 21.86 / 40.609 s | [interface/version policy](../../scripts/wmb/kernel/README.md); implemented. [Mutation evidence](../00-project/kernel-mutation-check-2026-11-04.md) checks finite catalogues, not production usefulness. |
| LifeSim: deterministic synthetic lives and an instrument for retention experiments | [generator](../../scripts/corpus/lifesim/), [systems/gates](../../scripts/lifesim/) | [registration/config](../../data/lab/aam-lifesim/); synthetic data, development seeds 0–999; confirmation/sealed epochs are not debugging data | L below, 67.016 s; portability CI uses pytest only | [registration](../../data/lab/aam-lifesim/README.md): D1 implemented; X0/X1 registered, confirmation results not run. [Portability evidence](../00-project/lifesim-portability-2026-11-04.md) does not resolve the development validity failures tracked by [80](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/80) and [81](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/81). |

## Experiment index

Every current `aam-*/README.md` and `wmb-*/README.md` is linked here; the historical August registry is not the inventory of these November slices.

| Experiment | README / recorded status |
| --- | --- |
| E0 delayed relevance | [Exploratory, unsealed results and limits](../../data/lab/aam-e0-delayed-relevance/README.md) |
| E1-SIM writer pilot | [Synthetic exploratory run and addenda](../../data/lab/aam-e1-writer-memory-sim/README.md) |
| E1-DS stronger writer | [Fresh-stream replication and later correction](../../data/lab/aam-e1ds-writer-memory-sim/README.md) |
| E2-FU follow-up memory | [Synthetic exploratory results](../../data/lab/aam-e2-followup-memory-sim/README.md) |
| E3A threshold calibration | [Live-note aggregate results and failed controls](../../data/lab/aam-e3a-retrieval-calibration/README.md) |
| E5 replay | [Live-history feasibility results](../../data/lab/aam-e5-replay/README.md) |
| F1 engagement | [Feasibility results and erratum](../../data/lab/aam-f1-engagement-signal/README.md) |
| E6 persona | [Results and erratum](../../data/lab/aam-e6-persona/README.md) |
| E6E account-nature probes | [Results, amendments and erratum](../../data/lab/aam-e6e-botness/README.md) |
| Persona battery v0 | [Frozen result and exploratory amendments](../../data/lab/aam-p-persona-v0/README.md) |
| Persona battery v1 | [Engineering successor and legacy-analysis policy](../../data/lab/aam-p-persona-v1/README.md) |
| LifeSim X0/X1 | [Registered experiments, instrument assumptions and epochs](../../data/lab/aam-lifesim/README.md) |
| WMB slice 0 | [Judge-validity result](../../data/lab/wmb-v0/slice0/README.md) |
| WMB R1 | [Retrieval result and amendments](../../data/lab/wmb-r1-retrieval/README.md) |

The local [metering proxy](../../scripts/metered_proxy.py) and [flash-only proxy](../../scripts/flash_only_proxy.py) enforce a run's declared limits. Their availability is not permission to run a new experiment. No command on this page calls a model, starts a proxy or opens a confirmation epoch.

## How an experiment moves

1. A README defines the question, arms, measures, decision rule and limits before results; `config.json` records parameters and input/script digests.
2. Commit the freeze before execution. Preserve the code/input version that generated each result.
3. Store raw data under its privacy contract. Publish the allowed aggregates, result and resulting decision, including failed controls or null findings.
4. Corrections are explicit amendments/errata or versioned successors. Keep the original result and its provenance; a newer runner digest does not become the historical execution digest.
5. The claim audit checks declarations and references. `SUPERSEDED.json` marks replaced packets; `.DRIFT.json` explains particular declared drift. They are documented history, not permission to change a freeze silently. A newly broken freeze blocks CI.

## Executed commands

Run from the repository root with the documented development dependencies already installed. These exact commands were executed in a clean, full-history local clone at `617e084d1dac62cbd82e30a2a26af1797053e6d6`, Python 3.12.10 on Windows AMD64. Times are wall-clock observations, not performance guarantees. [Command outputs](lab-map-validation-2026-11-04.json) and the PR preserve results, status and the final clean Git state.

**A — AAM/persona regression suites**
```text
python -m pytest -q tests/test_persona_sim.py tests/test_botness_probe.py tests/test_persona_battery.py tests/test_persona_battery_v1.py
```

**W — WMB core statistics, judge battery and retrieval harness**
```text
python -m pytest -q tests/test_wmb_stats.py tests/test_wmb_t0_battery.py tests/test_wmb_retrieval_bench.py
```

**K — both kernel lines and additive boundary tests**
```text
python -m pytest -q tests/test_wmb_memory_kernel.py tests/test_wmb_kernel_v2.py tests/test_wmb_memory_kernel_mutants.py
```

**L — ten dependency-light LifeSim suites**
```text
python -m pytest -q tests/test_lifesim_rng.py tests/test_lifesim_world.py tests/test_lifesim_schema.py tests/test_lifesim_vocab.py tests/test_lifesim_scorers.py tests/test_lifesim_queries.py tests/test_lifesim_verbalise.py tests/test_lifesim_channel.py tests/test_lifesim_appraisal.py tests/test_lifesim_integration.py
```

**M1 / M2 — inspectable mutation catalogues, temporary copies only**
```text
python scripts/wmb/mutate_kernel.py --workers 4
python scripts/wmb/mutate_kernel.py --module scripts/wmb/kernel/memory_kernel.py --workers 4
```

## Cheap checks and complete gate

| Executed command | What it establishes | Measured time |
| --- | --- | --- |
| `python tools/project_memory/cli.py verify --format json` | Canonical-log invariants for the selected project root; no index writes | 0.125 s |
| `python scripts/verify_memory_integrity.py --format text` | Same shared verifier through its direct entry point | 0.093 s |
| `python scripts/audit_repository_claims.py --format text` | Declared hashes, paths and references; exit 0 does not mean medium/low findings disappeared | 8.766 s |
| `python tasks.py check` | Full tests, memory integrity and claim audit; optional/private dependencies can skip tests | 323.921 s |

The first three checks are cheap. The full gate includes all repository suites, not only the focused commands above. CI adds the append-only diff guard, kernel Python 3.14, both mutation catalogues, and LifeSim's Windows/macOS Python 3.13/3.14 matrix. See [CI](../../.github/workflows/ci.yml).

## Read status chronologically

The persona-v0 header still says no call has occurred and its freeze hash is not yet committed; later Results/Amendments and Git record the completed run. R1 likewise keeps a preregistration header above its later results. These are preserved historical sections, not current execution status. The kernel README calls the original tests frozen, whereas issue 73 says new assertions may be added separately; the mutation correction preserves both original suites and adds a separate file. No ambiguity here is resolved by silently changing an experimental result.
