# DeepSeek V4 Flash PMLAB-MAP construction arm

Status: optional replaceable model comparator on inspectable construction data; not held out

- valid predictions: 45/56;
- conservative run cost: USD 0.01999580;
- cumulative project API cost: USD 0.36615920;
- obligation F1: 0.710;
- critical full recall: 0.607;
- end-to-end exact: 0.143;
- entity/predicate/time: 0.873 / 0.836 / 0.673;
- false closure: 2;
- critical unresolved safe handling: 0.833.

The model saw only model-facing queries plus the frozen public fixture catalogs, not gold graphs or evaluation metadata. The corpus itself was inspectable before the run, so these values only establish construction behavior. Any invalid/missing batch remains a failure; model output never edits gold.

The arm fails the registered obligation-F1, critical-recall, entity, predicate, false-closure, and critical-safe-handling gates. See `error-analysis.md` for the stage-separated diagnosis and validity boundary.
