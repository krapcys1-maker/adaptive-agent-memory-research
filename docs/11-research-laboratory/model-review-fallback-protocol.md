# Model-review fallback protocol

Status: active governance fallback for exploratory progress

## Purpose

The project must not wait indefinitely for volunteer human review. A blind external API model may therefore fill reviewer roles for an explicitly model-reviewed exploratory track. This changes the evidence tier, not the facts about independence.

## Evidence tiers

| Tier | Reviewer | What it may unlock | What it cannot support |
| --- | --- | --- | --- |
| A | author or deterministic automated audit | instrument repair | backend execution or validation |
| M1 | one external model in a fresh blind context | leakage-screened model-review candidate | confirmatory claims or architecture promotion |
| M2 | role-separated blind model annotations plus disagreement adjudication | one exploratory baseline run with permanent model-reviewed label | independent replication or architecture promotion |
| H | external human or genuinely external operator/family review | confirmatory benchmark gate, subject to all other controls | automatic product promotion without replication |

`M1` and `M2` are operationally blind but not institutionally independent. Separate calls to one model family share training, provider, prompting, and systematic error. Agreement is not independent statistical confirmation.

## Blind boundary

The model reviewer may inspect only the registered blind packet. It must not receive:

- author labels or rationales;
- corpus builder source;
- backend outputs or scores;
- another reviewer role's form;
- later adjudication or project conclusions;
- hidden stratum labels or target thresholds.

Requests, prompts, model version, response IDs, raw responses, token counts, conservative costs, errors, and hashes are retained.

## Role separation

1. Leakage auditor sees query forms and split metadata, not evidence labels.
2. Annotator A sees corpus, questions, and annotation manual in canonical order.
3. Annotator B starts from a fresh context, sees the same blind evidence in a different deterministic order, and never sees A.
4. Adjudicator receives only disagreements, the blind evidence required for them, and both anonymous candidate labels. It receives no author labels.

The same model family may occupy the roles only under separate calls and prompts. This is recorded as common-mode dependence, not called human or cross-family independence.

## Decision policy

- An M1 leakage rejection invalidates the candidate before labels or backends.
- An M1 acceptance permits M2 annotation preparation only.
- M2 requires complete schema-valid forms, hash-bound attestations, and disagreement adjudication.
- M2 gold may unlock one exploratory execution of the already frozen B0/B1/B2 lexical baseline.
- Model-reviewed results remain permanently labelled exploratory and cannot admit embeddings, graph, salience, or another product mechanism without a new preregistered comparison.
- A later H-tier review must reproduce or replace the M2 labels before any confirmatory or architecture claim.

## Budget

Each role has a run-local cap and the project retains the global USD 10 hard cap. A role stops before a request whose conservative cache-miss estimate could exceed either cap. Technical retries are explicit resumptions and remain in the same ledger.

## Conflict disclosure

The attestation must state that the API is author-operated, identify the model/provider family, disclose earlier unrelated work by that family in the project, and state exactly which materials were hidden. This disclosure does not invalidate M-tier review; it prevents it from being misrepresented as H-tier evidence.
