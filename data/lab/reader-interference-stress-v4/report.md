# Reader interference stress v4

Status: partial validity; condition names leaked through model-visible case IDs

V1 leaked expected labels. V2 removed labels but exposed chronology through numbered IDs and values. V3 made IDs opaque but reused record identities across cue conditions in the same batch. V4 salts every evidence ID and value per case and excludes all expected fields from model payloads. Earlier artifacts remain preserved but cannot support the v4 conclusions.

The 128-case factorial crossed stale counts `1,4,16,64`, full/weak/absent/contradictory validity cues, gold-first/gold-last order, high/low value similarity, and explicit/minimal instructions.

Results:

- full validity and weak version cues: 64/64 correct;
- absent cues: 32/32 correct abstention;
- contradictory cues with explicit instruction: 16/16 correct abstention;
- contradictory cues with minimal instruction: 12/16 correct;
- all four failures occurred at 64 stale competitors; order and value similarity did not change the pattern.

Thus record count alone did not produce reader interference when validity was resolvable. The observed failure is an interaction: high competition plus contradictory current markers plus an underspecified abstention policy caused confident selection of one unsupported branch.

This is one model and one case per full factorial cell, evaluated in batches. Replication needs independently salted cases, another model family, and separate calls or a proven cross-case-isolation protocol.

V4 cost USD 0.05249684. Cumulative conservative DeepSeek expenditure, including invalid runs retained for audit, is USD 0.27379880 of the USD 10 cap.
