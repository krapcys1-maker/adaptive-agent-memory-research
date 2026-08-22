# Invalid for held-out confirmation — template leakage

Status: pre-run instrument defect discovered after corpus construction, before independent labels or backend execution

The registered split policy requires development and test histories to use different query templates. A label-free audit found high dev/test form similarity and direct repeated frames in several query families. The corpus and all prior commits remain preserved, but this split cannot support a held-out architecture decision.

Do not complete the v0 independent annotation forms and do not run B0/B1/B2. Build v0.1 by changing test query forms while keeping the evidence corpus and all backend results unseen. See `data/lab/pmlab-v0-split-audit/`.
