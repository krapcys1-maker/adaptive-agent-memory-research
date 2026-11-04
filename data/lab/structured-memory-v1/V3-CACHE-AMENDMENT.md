# Cache bug correction v3, before any primary answer scoring

Local v2 did improve extraction but stopped after 83 calls: 80 unmatched model
events, some cached events, no primary questions. Inspecting literal cache matches
revealed a code defect: a learned `{subject} is {object}.` shell competed with
every specific shell, including `The author of {subject} is {object}.`. The v1
cache declined whenever both matched, repeatedly calling the model. This was a
cache design error, not evidence that local models cannot do this extraction.

Two generic grammar rules now apply in a new runtime version: a reusable shell
must contain a fixed lexical word beyond function words; among matching shells,
prefer the largest fixed literal surface. Equally specific conflicting matches
still decline to the model. Do not resolve this by picking the latest template
or by adding a benchmark-specific relation list. No gold/question informs it.

The earlier v1/v2 modules, source logs and failures remain unchanged. Rebuild a
fresh v3 store with unchanged v2 prompts and native local schema. No hidden
reuse of successful proposals or model retries on a question. Existing local
phase bound is explicitly extended from four to six phases (205 calls/3600s
each), to include the failed extraction diagnosis and the full planner runs.
The cumulative paid ledger/cap from the v2 amendment is unchanged.
