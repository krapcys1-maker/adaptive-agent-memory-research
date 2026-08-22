# Healthy-result audit curve v0

Status: completed exact-expectation instrument under one specified transient-flip condition

## Question

How often must an adaptive diagnostic recheck a first-pass `healthy` result to detect false-health signals while retaining a cost advantage over repeating every probe?

## Design

The experiment uses all 58 fault states and exhaustively places one transient flip on each of ten probes, producing 580 contributions. Five storage/loss evidence paths remain always triplicated and use the diverse, conflict-to-inconclusive policy from robustness v1. For other probes, failures and timeouts are always retried; first-pass healthy results are audited with mixture weight 0%, 5%, 10%, 25%, 50%, 75%, or 100%.

These are exact expected mixtures of the audited and unaudited outcome for each contribution, not Monte Carlo samples.

## Curve

| Healthy audit rate | Expected probe units | Exact fault set | Root accuracy | Macro stage F1 |
|---:|---:|---:|---:|---:|
| 0.00 | 23.897 | 0.819 | 0.940 | 0.956 |
| 0.10 | 24.507 | 0.837 | 0.946 | 0.961 |
| 0.25 | 25.422 | 0.864 | 0.955 | 0.968 |
| 0.50 | 26.948 | 0.909 | 0.970 | 0.979 |
| 0.75 | 28.474 | 0.955 | 0.985 | 0.989 |
| 1.00 | 30.000 | 1.000 | 1.000 | 1.000 |

Under the linear one-flip mixture, the exact audit rate needed to reach the existing 0.95 localization threshold is 0.72381, at 28.314 expected probe units. That saves only 1.686 units, or 5.6%, relative to repeating all ten probes three times.

The storage-diverse policy retained physical-data-loss recall 1.0, zero false-loss and false-no-loss declarations, and decision coverage 1.0 at every point in this transient-only curve.

## Supported conclusion

Failure-only retry is cheap because it assumes first-pass success is trustworthy. Under uniformly placed transient flips, meeting a 0.95 exact-localization threshold requires auditing most healthy results and removes most cost savings. A cheaper policy needs empirical probe-specific false-health rates, consequence-sensitive risk limits, or genuinely independent measurement paths; it cannot be justified from retry logic alone.

## Boundaries

- Exactly one transient flip is enumerated per contribution; persistent and correlated failures are covered by robustness v1, not this curve.
- Audit rates are expectation weights, not observed frequencies.
- Probe units have equal abstract cost.
- The 0.95 threshold predates this curve, but the noise distribution is authored rather than empirical.
- Consequence-sensitive auditing refers to operational risk, not subjective emotion.
