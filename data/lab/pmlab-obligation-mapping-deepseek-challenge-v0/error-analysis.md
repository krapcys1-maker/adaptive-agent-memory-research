# PMLAB-MAP DeepSeek post-freeze challenge analysis

Status: completed post-arm challenge; same-process labels; not independently reviewed

## Result

The frozen optional model arm is rejected. On 28 paired English/Polish challenge cases it produced only 13 schema-valid predictions (0.464), obligation F1 0.325, critical full recall 0.292, and end-to-end exact 0.107. It made two false closures. F1 fell by 0.385 from the already-failing construction score of 0.710, far beyond the registered maximum degradation of 0.05 for unseen schema and 0.10 for unseen composition.

## Interface failures

Fifteen outputs were invalid and remain scored as failures:

- ten selected a span that was not an exact substring of the source query;
- five emitted an empty required entity field.

This fall in schema validity from 0.804 on construction to 0.464 on challenge is itself a generalization failure. It also shows that JSON-object mode does not guarantee compliance with a semantic response contract.

## Stage diagnosis

Among matched obligations, namespace mapping (0.923) and authorization (1.000) were stronger than entity (0.769), predicate (0.846), certificate (0.692), and full graph recovery. These conditional accuracies must not be read as whole-system reliability: invalid and omitted obligations are excluded from the link denominator but remain end-to-end failures.

Compared with frozen deterministic rules, the model had fewer false closures (2 versus 10) and three exact cases versus zero, but lower obligation F1 (0.325 versus 0.409) and nearly the same critical-omission count (17 versus 18). Neither arm is safe or general.

## Conclusion

The current bottleneck is not choosing between rules and a cloud parser. It is the absence of a robust, schema-conditioned obligation mapper with explicit unresolved-state handling. The next research step should factor the problem into independently challengeable stages: surface-span alignment, schema linking, entity linking/NIL detection, graph composition, temporal normalization, and certificate routing. Any repair must receive a new version and a new post-repair challenge.
