# Passive telemetry versus isolated active probes v0

Status: completed deterministic observability-instrument test; authored and not held out

## Question

Can a memory system distinguish physical loss of canonical data from loss of access, and can it localize multiple component faults, using only one cascading production trace?

## Design

The generator crossed 58 no-fault, single-fault, two-fault, and three-fault specifications with three telemetry regimes, producing 174 cases over stages `F0` capture through `F5` action.

- Passive telemetry observes one end-to-end execution. Once an upstream stage fails, downstream stages also fail and therefore cannot be interpreted as independent component tests.
- Active diagnosis supplies a controlled known-good input independently to every stage. Storage probes also check direct-ID recovery, a full scan, raw-byte recovery, and schema reparsing.
- Storage faults include both physical loss and recoverable schema failure. They have the same failed stage but different data-loss labels.

## Results

| Measure | Passive | Ideal active |
|---|---:|---:|
| Exact fault-set accuracy | 0.075 | 1.000 |
| Root-fault accuracy | 0.511 | 1.000 |
| Macro stage F1 | 0.371 | 1.000 |
| Masked downstream-fault recall | 0.146 | 1.000 |
| Data-loss decision coverage | 0.414 | 1.000 |
| Data-loss accuracy when decided | 0.861 | 1.000 |
| Mean stages left unknown | 3.994 | 0.000 |
| Incremental probe units | 0 | 10 |

With complete passive telemetry, root-fault accuracy was 1.000 but exact fault-set accuracy was only 0.138 and masked downstream-fault recall was 0.000. Thus even perfect observation of a single cascade identifies the first boundary but cannot reveal independent downstream faults. Root accuracy fell to 0.517 with operationally sparse telemetry and 0.017 when the actual fault stage was silent.

For two- and three-fault cases, passive exact-set accuracy was 0.000. The active arm was exact by construction because every probe is assumed truthful and receives a controlled input; its perfect score is a ceiling and a validation of the instrument, not empirical evidence that real probes will be perfect.

## Supported conclusion

An end-to-end miss is not evidence that a memory was deleted. Passive traces can identify a causal frontier when the failing stage emits telemetry, but cannot in general distinguish recoverable storage problems from physical loss or expose faults hidden behind an earlier failure. A serious memory laboratory needs active direct-ID/full-scan/checksum probes and controlled retrieval, context, reader, and action probes.

The next falsification step is to add probe noise, false health signals, timeouts, and selective probe budgets. The useful engineering target is the smallest adaptive probe set that preserves root localization and data-loss safety, not the ideal arm's tautological 100% score.

## Boundaries

- Cases and labels are authored by the same deterministic generator.
- Faults are isolatable; shared-resource and timing faults are absent.
- Active probes are assumed independent and truthful.
- Probe unit counts are abstract costs, not latency or money.
- This run establishes observability requirements only and does not promote an architecture.
