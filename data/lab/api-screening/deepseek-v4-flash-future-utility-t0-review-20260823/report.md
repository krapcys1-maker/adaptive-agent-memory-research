# DeepSeek advisory review of future-utility telemetry T0

Status: finalized M1 author-operated model review

This review is adversarial advice, not human, institutional, privacy, or statistical independence. It cannot unlock T1-T4.

## measurement-and-causal-integrity

Verdict: `accept_t0_with_limits` (confidence 0.85).

Next test: T1 natural capture with synthetic user-approved allowlist and full privacy review

### Major issues

- No explicit check that correction events cannot target other correction events or that corrected values are not used in downstream joins without versioning.
- No validation that outcome_observed occurs within the preregistered observation window or that window closure is not earlier than outcome timestamps.
- No check for interference or spillover across tasks sharing memory or candidate sets; exposure assignment assumes unit-level independence.
- No explicit handling of missing propensity for natural observation beyond allowing null; no check that propensity is in (0,1) for randomized assignments.
- No validation that retrieval scores or assignment propensities are not used to infer utility or that U0-U4 labels are not misinterpreted as causal.

### Required before T1

- Add explicit checks for correction targeting correction events and for corrected value versioning in downstream joins.
- Add validation that outcome_observed occurs within the preregistered observation window and that closure is not earlier than outcomes.
- Add checks for interference or spillover across tasks sharing memory or candidate sets.
- Add validation that propensity is in (0,1) for randomized assignments and that natural observation uses null propensity consistently.
- Add checks that external_processing_allowed is false for all non-none sensitivity levels.
- Add checks that correction reasons and assessor identifiers do not contain raw content or prohibited patterns.
- Add checks that observation_window_closed does not censor based on exposure or outcome values.

### Unsupported claims

- No claim that the instrument is ready for natural capture (T1) or any causal utility measurement.
- No claim that privacy review is complete or that deletion semantics are solved.
- No claim that the instrument can detect all forms of privacy leakage or causal confounding.

## privacy-and-governance

Verdict: `accept_t0_with_limits` (confidence 0.90).

Next test: T1 natural capture with synthetic user consent and controlled environment, after implementing required privacy controls

### Major issues

- No explicit retention or deletion mechanism; privacy policy acknowledges but does not implement tombstone/export contract, leaving unresolved conflict between audit retention and erasure.
- No access control or authentication mechanism for telemetry stream; no role-based access or authorization checks for reading or writing events.
- No data minimization review for allowed fields; some fields like assessor identity or pseudonym may be unnecessary for T0 and could be omitted.
- No explicit consent or legal basis for processing synthetic data; policy mentions user-approved allowlist but no mechanism to record consent or basis.
- No data protection impact assessment or independent privacy review; policy states independent review not completed.

### Required before T1

- Implement access control and authentication for telemetry stream
- Define and implement retention and deletion mechanisms with tombstone/export contract
- Conduct independent privacy review and DPIA
- Implement consent and legal basis recording for natural capture
- Implement data subject rights (access, export, erasure)
- Minimize data collection to only necessary fields for T1
- Establish secure storage for raw artifacts with access controls
- Implement audit logging for privacy events

### Unsupported claims

- No claim of privacy compliance or minimization beyond T0 synthetic data
- No claim of causal utility or effectiveness
- No claim of production readiness for natural capture
- No claim of deletion or erasure capability
- No claim of access control or security
