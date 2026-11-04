# What is implemented, and what is still missing

This repository contains working research tools and experiments for agent memory. It does not yet demonstrate that a complete memory system improves a real agent's writing or reliably maintains its biography. Passing software tests is necessary evidence about implementation, not that broader result.

## What exists

| Part | Implemented capability | Limit of the evidence |
| --- | --- | --- |
| Project memory | Local append-only events, search, provenance and CLI integrity verification | Continuity tooling for this research; not validation of the proposed final agent architecture |
| Memory kernel | Frozen 0.1.0 and live 0.2.0; retrieval, limited injection, provenance, reference guard and logging | Both have mechanical tests and mutation checks; ranking and gate behavior vary across public suites |
| Persona battery | P1/P2/P3/P7 runs, a versioned v1 runner with safe resumption, execution identity and completeness checks | P4/P5/P6 are not delivered; the tested instruction to honor stored details did not achieve the P2 consistency threshold |
| LifeSim | Deterministic synthetic worlds, exact gold, baseline systems and sixteen validity gates | Four gates fail on the canonical twenty L1 development worlds; no X0 confirmation claim |
| Research comparisons | Public/offline probes, replay studies, cost measurements, judge controls and preserved negative results | Recall is not downstream usefulness; R1's failed judge control prevents its preregistered verdict |
| Integration counterpart | A separate NIE repository already contains persona/integration work | Its local configuration and the research repository do not establish live server behavior; see the dated coordination handoff |
| Offline journal bridge | [Read-only replay](nie-offline-bridge-2026-11-04.md) maps published improvised NIE details to the live kernel, with availability, provenance and a context word budget | Synthetic engineering demonstration only; no live prompt injection, generated-answer consistency or supersession support |
| Local typed-fact reader pilot | [Journal → reader → guarded answer](../../../data/lab/nie-local-reader-v1/README.md): supplied slot cues plus retrieved typed claims retain 48/48 values, including 12 corrections of raw answers | Eight authored fields, two repeated runs each, one local quantized reader; slot routing is supplied, free prose/canonical-card conflicts/revisions and actual NIE prompts remain unvalidated |

Use the [laboratory map](../11-research-laboratory/lab-map.md) for runnable commands, locations and all fourteen November experiment entry points. The [coordination handoff](coordination-handoff-2026-11-04.md) records the division of work and original snapshots; later delivery reports supersede its historical PR status.

## What the tests mean

The full engineering gate runs the software tests, append-only memory verification and claim audit. CI additionally checks kernels, mutations and LifeSim portability. These checks catch broken calculations, lost provenance, incompatible changes and code regressions. They cannot establish that a memory improves answers or that a benchmark has no shortcut.

Research gates ask separate questions. The [public kernel evaluation](../../../data/lab/lexical-gate-eval-v1/README.md) finds a concrete distinction: live BM25 improves H2 ranking at depth three, but its shipped evidence floor rejects every scored positive H2 query; on H1 it ranks fewer gold items than coverage. The [cost report](retrieval-cost-2026-11-04.md) makes retrieval volume visible without claiming that more recall is safe or useful. LifeSim's failures must remain failures until its instrument is repaired and rechecked.

## The next milestone

The typed-fact pilot supplies a narrow offline integration candidate and a controlled reader replay with known failure modes. The next milestone is validating typed capture and routing on actual writing prompts, then transferring the intervention to the main reader. Software tests and average retrieval recall alone do not establish that broader behavior.

1. Preserve the completed public ranking/cost results and the persona consistency failures. Do not repeat the already-executed P2 sentence experiment as if it were new.
2. Diagnose and then repair LifeSim's guessing/text shortcuts in separately versioned changes, retaining all canonical gate thresholds and historical digests. Only development seeds are available for this iteration; confirmation epochs remain sealed.
3. Evaluate any proposed kernel profile or consistency intervention against both useful recall and unwanted/stale injection. The current comparison selects no universal profile, and its easy negative controls do not establish realistic precision.
4. Continue the existing WMB question-bank/adapter/opportunity-set work and R1b judge repair. Promotion to stronger claims follows the [independence ladder](independence-ladder.md); an independent human panel cannot be replaced by another automated test.

NIE's canonical persona, prompts, filters and deployment remain its integration track. Research findings and explicit handoff records should reach that track before an intervention is treated as an established fix. Neither this status page nor a merged engineering PR is a production-readiness declaration.
