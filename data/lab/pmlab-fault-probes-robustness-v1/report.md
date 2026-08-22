# Active-probe robustness and budget v1

Status: completed deterministic robustness instrument; authored noise schedules, not empirical failure rates

## Design

The run crossed 58 no-fault, single-, double-, and triple-fault states with 34 probe conditions, for 1,972 cases. Ten active probes cover six pipeline stages plus direct-ID, full-scan, raw-byte, and schema recovery evidence.

Noise conditions include a clean control; a first-call flip, first-call timeout, and persistent flip for every probe; a correlated false-loss recovery triad; a correlated false-healthy recovery triad; and a shared failure across all primary stage probes.

Four policies were compared:

- `single-naive`: one call to every probe;
- `repeat-all-naive`: three calls and majority vote for every probe;
- `adaptive-abnormal-naive`: repeat only a first failure or timeout;
- `adaptive-storage-diverse`: always repeat five storage/loss probes, repeat other abnormal results, require agreement across write, recovery, and schema paths, and return inconclusive on conflict.

Every scenario has equal weight for instrument diagnosis. The aggregate is not an estimate of production reliability.

## Aggregate results

| Policy | Mean probe units | Exact fault set | Root accuracy | Loss recall | False loss | False no-loss | Loss coverage | Accuracy when decided |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single naive | 10.00 | 0.548 | 0.827 | 0.706 | 0.029 | 0.206 | 0.976 | 0.920 |
| adaptive abnormal | 17.97 | 0.725 | 0.889 | 0.794 | 0.029 | 0.206 | 1.000 | 0.922 |
| adaptive storage-diverse | 24.16 | 0.741 | 0.901 | 0.824 | 0.000 | 0.000 | 0.909 | 1.000 |
| repeat all | 30.00 | 0.794 | 0.918 | 0.882 | 0.029 | 0.118 | 1.000 | 0.946 |

No policy dominates every objective. Full repetition has the best aggregate fault-set and root scores, but still makes false physical-loss and false no-loss declarations under common-mode or persistent faults. The diverse policy spends fewer probes, makes no wrong loss/no-loss declaration in this authored matrix, and abstains on 9.1% of loss decisions.

## Mechanism findings

- On transient timeouts, both adaptive policies were exact at about 18.24 and 24.26 probe units, versus 30 for repeat-all.
- On transient flips, repeat-all was exact. Repeating only abnormal results reached 0.764 exact accuracy because a faulty component can emit a false-healthy first result and escape retry. Always repeating critical storage evidence raised exact accuracy to 0.819 and loss recall to 1.000.
- On persistent flips, all four policies had exact fault-set accuracy 0.400. Repeating the same broken measurement three times added cost but no information.
- On correlated scenarios, repetition left exact accuracy at 0.667. Naive loss policies produced both false-loss and false-no-loss rates of 0.333. Diverse evidence changed those errors into abstentions: conditional loss accuracy 1.000 at coverage 0.667.

## Supported conclusion

Retries are useful only against plausibly independent transient failures. “Three identical checks” is not independent evidence. A safe data-loss decision requires probes from different failure domains and an explicit inconclusive state when they disagree. Adaptive retry must also sample or periodically audit healthy results; retrying only failures cannot detect false-health signals.

The existing F1 promotion threshold is not passed: no arm reaches 0.95 exact localization under the authored noise suite. Before architecture promotion, the next instrument must model real probe dependencies, latency and cost, add random success audits, and freeze a failure-domain graph that defines which checks count as independent.

## Boundaries

- Noise schedules are deterministic and equally weighted, not calibrated probabilities.
- Probe outcomes are Boolean/timeout; latency distributions and partial corruption are absent.
- “Diverse” means logically different paths in this fixture, not demonstrated infrastructure independence.
- The same author generated cases, policies, and labels.
- Results establish safety requirements and reject naive repetition; they do not validate a production diagnostic controller.
