# Invalid run — label leakage

Status: invalid; excluded from scientific interpretation

The API payload included `expected_answer`, `expected_evidence_id`, and `expected_abstain`. The model could read the gold labels directly. The 128/128 result is therefore unusable. Artifacts and cost remain preserved for audit. Corrected execution is `reader-interference-stress-v2`.
