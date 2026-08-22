# Preserved construction run v0 — instrument defect

Status: rejected instrument run; preserved before repair

The first uncommitted construction run exposed two scorer/arm defects:

1. `MAP-T22-EN` was counted as a critical omitted obligation even though the predicted operator and grounding were correct, because whole-query span overlap was 1/7 and the greedy matcher threshold was 0.15. This is a span-instrument false negative, not a decomposition miss.
2. `gold_obligations_predicted_links` inferred roles from gold span text without using operator/dependency type or sufficient query context. It consequently treated derived nodes as ordinary scoped leaves and misclassified short spans such as `approved`. The arm did not isolate linking as registered.

The recorded v0 headline values must not be used as mapper evidence. The repair may change only role/context handling, derived-node inheritance, and exact event-span construction; the frozen corpus and gold files remain unchanged. The repaired runner receives a new version and its artifacts remain separate.
