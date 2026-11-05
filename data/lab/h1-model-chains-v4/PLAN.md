# Automatic question routing across captured property names

The complete v3 result still fails: dev OBSOLETE leaks12/12 with zero gold notes
retrieved; valid changes9/12 to8/12 but overall answering67->66. Preserve every
v3 output/score. Post-hoc source inspection shows the correction **was indexed**
under e.g. staging_url, while lexical candidates use deploy_url, staging_target
or deploy_staging_url, sometimes with an overlong entity span. Literal-span
validity did not earn a canonical entity/property chain. No success claim.

Execute the missing query-routing boundary: extract literal entity candidates
from **visible captured metadata**, then let the local model choose the subject
and all property labels semantically relevant to the natural question. No gold,
hand-supplied route cue, fixed service grammar or answer value. Synonymous labels
are selected from the actual catalog; no property is invented. Retrieve source
notes bearing those properties and a whole-word mention of the selected subject,
newest first as a retrieval prior. The reader still interprets raw notes, dates
and roles. This co-occurrence retrieval does not assert a new graph relationship.

Run all84 queries on both existing dev/valid captures. Same native local reader,
seed7, source-role prompt, three-note/4500-byte context and matched base. One
extra local routing call per query. Failed/empty routing visibly falls back to
base; it never generates a missing fact. Freeze complete outputs before scoring.
Report every family and no answering/leakage trade-off hidden in an aggregate.

Unchanged cumulative H1 cap2600 actual local attempts, <=600/3600s per phase;
two phases <=255 calls each. This continues the same ledger and preserves all
earlier failures. No additional API call, model judge, project-planning request,
NIE/production change or sealed data. The optional oracle control runs only if
the same ledger has remaining room. Development evidence only, no I1 promotion.
