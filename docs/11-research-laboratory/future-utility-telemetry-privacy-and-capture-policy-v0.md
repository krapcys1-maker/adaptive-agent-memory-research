# Future-utility telemetry privacy and capture policy v0

Status: T0 construction policy; independent privacy review not completed

Applies to: `PMLAB-UTILITY-001`

## Default

Telemetry capture is denied unless the event is synthetic or the source belongs to an explicit project-artifact/user-approved allowlist. The system records hashes, opaque identifiers, typed decisions, outcomes, costs, and provenance metadata. It does not record a conversation transcript merely because it is available.

## Allowed fields

- opaque task, memory, event, assignment, model, prompt, and policy-version identifiers;
- SHA-256 hashes of canonical content, outputs, packets, and candidate sets;
- timestamps, validity state, authorization state, and reviewed provenance class;
- rank, retrieval scores, assignment propensities, exposure state, and context position;
- explicit evidence-event references and coarse explicit-feedback enum;
- preregistered outcome values, harm flags, latency, token counts, cache counts, local compute, and USD;
- assessor identity or pseudonym and blindness status;
- correction pointers, corrected scalar fields, and a non-sensitive reason;
- observation-window closure and censoring reason.

## Prohibited fields

- raw conversation, prompt, source document, memory body, model output, or user content;
- passwords, API keys, bearer tokens, cookies, private repository credentials, or `.env` values;
- private chain-of-thought, hidden reasoning, scratchpad, or inferred psychological state;
- unredacted email, phone, address, legal identity, financial identifier, or health record;
- a universal `utility` label derived only from retrieval, exposure, citation, use, or task success;
- raw external-worker request/response bodies in the canonical telemetry stream.

Raw artifacts needed for an independently approved benchmark belong in access-controlled, separately governed storage. The public telemetry stream may reference them only by opaque ID and hash.

## Sensitivity rules

| Sensitivity | Canonical telemetry | External model processing |
| --- | --- | --- |
| `none` | allowed under a capture basis | only when the experiment manifest explicitly permits it |
| `internal` | hashed/typed metadata only | denied by default |
| `personal` | denied until a separate minimization and deletion review | denied |
| `secret` | denied | denied |
| `private_reasoning` | denied | denied |

An event marked `personal`, `secret`, or `private_reasoning` cannot set `external_processing_allowed=true`. T0 fixtures use only `synthetic` plus sensitivity `none`.

## Corrections and deletion

Corrections append a new `correction` event that targets an earlier event and supplies scalar replacement fields. The original bytes remain auditable. A production deletion mechanism will require a separate tombstone/export contract and an analysis of the conflict between audit retention and legal/user erasure. T0 does not claim that this problem is solved.

## Retry and deduplication

Each delivery has both `event_id` and `idempotency_key`. A byte-equivalent repeated delivery is counted as a retry and produces one logical event. Reuse of either identity with different content is an integrity failure. Outcome denominators are calculated from logical events, not deliveries.

## Causal-language constraint

- U0-U4 fields retain observational names.
- A `causal_effect_estimated` event is prohibited before T4 and requires a registered design, estimand, estimator, contrast, population, interval, and sample size.
- `not_referenced`, `withheld`, `window_closed`, and missing outcome are never converted automatically into zero utility.

## T0 acceptance conditions

The synthetic instrument must demonstrate:

- zero raw-content or prohibited-key fields;
- exact retry collapse and rejection of conflicting duplicates;
- referential and temporal joins across memory, task, candidate, retrieval, assignment, exposure, behavior, outcome, cost, correction, and closure;
- correction without mutation of the target event;
- explicit censoring rather than imputed failure;
- rejection of U5 claims during T0;
- deterministic byte-identical reports across fresh processes.

Passing T0 authorizes neither natural capture (T1), randomized exposure (T3), nor adaptive ranking (T4).
