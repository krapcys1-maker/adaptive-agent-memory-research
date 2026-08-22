# Reader interference stress v5

Status: completed exploratory single-model; first run with audited gold, chronology, cross-case, and condition-name leakage controls

Audit lineage: v0/v1 leaked expected fields; v2 exposed chronology through IDs and values; v3 reused identities across cue conditions; v4 named conditions in model-visible case IDs. V5 uses label-free payloads, opaque per-case IDs and values, no cross-case identity reuse, and opaque case IDs.

Across 128 factorial cases:

- full dates and weak version numbers: 64/64 correct through 64 stale records;
- explicit policy (“absent or conflicting cues ⇒ abstain”): 64/64 correct;
- minimal policy with absent cues: 8/16 correct;
- minimal policy with contradictory current markers: 4/16 correct;
- presentation order and value similarity had no aggregate effect.

Failures under minimal instructions were overconfident selections rather than abstentions. In absent-cue failures the model commonly selected the final presented record; with contradictions it selected one of two `current` branches. The count pattern was non-monotonic and has only one case per full cell, so no smooth dose-response claim is allowed.

The supported conclusion is conditional: stale count alone did not hurt when validity was resolvable. Ambiguous validity plus an underspecified decision policy caused selection failures. A memory controller should resolve or surface validity conflicts before context assembly and enforce abstention when no unique authorized/current record exists.

V5 cost USD 0.05218136. Cumulative conservative cost including all invalid audit runs is USD 0.32598016 of the USD 10 cap.
