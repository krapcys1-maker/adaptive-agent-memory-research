# DeepSeek V4 Flash PMLAB-MAP post-freeze challenge

Status: optional replaceable model comparator; post-arm challenge; labels not independently reviewed

- valid predictions: 13/28;
- conservative challenge cost: USD 0.01164504;
- cumulative project API cost: USD 0.37780424;
- obligation F1: 0.325 (construction 0.710, drop 0.385);
- critical full recall: 0.292;
- end-to-end exact: 0.107;
- entity/predicate/time: 0.769 / 0.846 / 0.846;
- false closure: 2;
- critical unresolved safe handling: 0.800.

The model received the exact frozen construction system prompt with only the challenge's public schema, entity catalog, clock, and model-facing queries substituted. It received no gold graph, split label, criticality, or evaluation metadata. Invalid/missing outputs remain failures and are not repaired.

Any critical omission, false closure, failure of 0.90 obligation F1 or 0.95 entity/predicate accuracy, or a construction-to-challenge F1 drop above 0.05 rejects promotion. The model remains optional and never supplies gold labels.
