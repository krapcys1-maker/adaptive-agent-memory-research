# PMLAB-MAP stage blind advisory review

Status: DeepSeek advisory disagreement queue; not independent corpus review

- valid predictions: 44/44;
- exact agreement with authored gold: 40/44 (0.909);
- critical exact agreement: 30/34 (0.882);
- bilingual advisory parity: 22/22 groups;
- disagreement rows: 4.

The model saw no gold labels, criticality, strata, scores, author rationale, or candidate implementation. Agreement is not proof of label validity, and disagreement does not automatically replace gold. Every disagreement remains an adjudication target; human or otherwise genuinely independent review is still required by the frozen protocol.

The worker's `case_validity` field is excluded from evidence. The prompt failed to distinguish benchmark-case validity from the deliberately defective payload under review; all eight `material_issue` flags landed on correctly typed-rejected negative fixtures. Raw values are preserved as a prompt-design failure.

## Disagreement queue

- `ST-C03-EN` (contract_span, critical): exact label — Payload is valid JSON with required fields, span 'device that stopped working yesterday' is a valid source span, entity type:sensor is a valid type reference, and query_status is resolved.
- `ST-C03-PL` (contract_span, critical): exact label — Payload is valid JSON with required fields, span 'urządzenie które przestało działać wczoraj' is a valid source span, entity type:sensor is a valid type reference, and query_status is resolved.
- `ST-C07-EN` (contract_span, critical): exact label — Payload is valid JSON with required fields, spans match source text, obligation IDs are unique and sequential, dependency O2->O1 is backward, catalog ID project:aurora exists, and query_status is resolved.
- `ST-C07-PL` (contract_span, critical): exact label — Payload is valid JSON with required fields, spans match source text, obligation IDs are unique and sequential, dependency O2->O1 is backward, catalog ID project:aurora exists, and query_status is resolved.
