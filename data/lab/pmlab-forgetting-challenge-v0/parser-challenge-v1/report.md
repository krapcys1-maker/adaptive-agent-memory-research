# Frozen parser v0 perturbation challenge

Status: completed post-freeze authored challenge; parser implementation frozen at commit `1a43b7a`; not independently designed

## Design

Twenty-eight new cases were authored only after parser v0 was committed: 21 answerable and 7 unanswerable. They cover topic paraphrases, alternate date formats, relative-time expressions, Polish wording, ambiguous entities, missing entities, dates outside stored history, and underspecified time. Parser v0 was not changed during evaluation.

## Result

- exact parse accuracy overall: 0.393;
- answerable exact history-plus-date accuracy: 0.238;
- strict-parser Recall@5: 0.238;
- strict-parser unanswerable abstention: 0.857;
- raw FTS5 Recall@5: 0.381;
- raw FTS5 abstention: 0.143.

By category, relative time scored 0/4, multilingual 0/1, new date formats 1/8, paraphrases 1/4, and topic disambiguation 3/4. Parser v0 answered an underspecified request containing “before now” as if it meant current, causing the single unsafe non-abstention among seven unanswerable cases.

Unconditional raw fallback increased Recall@5 to 0.619 but reduced abstention to 0.143. A post-hoc fallback only when the parser emitted `unresolved-time` reached Recall@5 0.619 while retaining abstention 0.857 because all 15 answerable `unresolved-time` failures and no unanswerable abstentions occupied that reason in this small set. This policy was invented after inspecting failures and has no evidential status until frozen and tested on new data.

## Conclusion

Parser v0 is rejected as a general query interpreter. Its 1.0 development result was template fit. Binary “parse or abstain” also creates a recall/safety tradeoff: strict parsing can discard answerable queries, while unconditional raw fallback defeats abstention. Typed failure reasons may support a selective fallback controller, but reason calibration itself must become a measured component.

The next parser benchmark must freeze parser v1 and fallback policy before testing, separate entity resolution from temporal interpretation, include confidence calibration, and reserve independently authored paraphrase/date families.
