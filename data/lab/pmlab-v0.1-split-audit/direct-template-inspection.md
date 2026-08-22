# PMLAB v0.1 direct template inspection

Status: author inspection passed; independent leakage audit still required

Scope: all 60 development queries were compared with all 60 rewritten test queries within their registered category. This inspection used blind query rows only. No answerability labels, evidence relations, reviewer forms, or backend outputs informed the decision.

| Category | Development form family | V0.1 test form family | Author decision |
| --- | --- | --- | --- |
| causal multi-episode | `What caused ...; how diagnosed, and what fixed?` | reconstruct/trace origin, observation, remedy | distinct |
| contradiction | `What conflicting findings did reports ... give?` | contrast/set out both conclusions | distinct |
| cross-language | short where/when lookup | recorded place/date/role request in the opposite language | distinct |
| exact lexical | where/which-container lookup | return/identify assigned location | distinct |
| paraphrase | direct what/which/how paraphrase | name safeguard/operation/treatment/handling/withheld power | distinct |
| poison resistance | quoted payload followed by a repeated safety-rule question | payload-specific classification plus defensive-policy request | distinct |
| procedure failure | `After the incident where ..., which procedure ...?` | incident-specific preventive workflow or correction transaction | distinct |
| supersession | `What is the current ...?` | latest-valid/effective value excluding predecessor | distinct |
| temporal as-of | `What was ... as of DATE?` | cutoff/snapshot/valid-on-date resolution | distinct |
| unanswerable | bare request for an absent fact | evidence-qualified answerability request | distinct |
| weak overlap | repeated where/which phrasing | protected/drop-off/component/location/rebuildable-structure formulations | distinct |
| what-where-when | `When and where was ... transferred?` | item-specific date-plus-destination formulation | distinct |

The rewrite changes lexical and syntactic realization but intentionally preserves task semantics. It does not establish that category cues, authored regularities, or source contamination are absent. A reviewer independent of corpus construction must inspect this packet before annotation begins.
