# Literal case grounding, no regeneration

During v2 capture, exact-case validation rejected `test suite` when the original
source says `Test suite`. The entity exists literally with different case. Other
rejections such as an invented `clean_modules` entity remain real errors. This
is a validator boundary, not grounds for retrying the model or accepting aliases.

After both complete v2 captures are frozen, derive a **new metadata file** from
the same raw proposals. Accept only a whole source span with case-insensitive
matching, require its casefolded spelling to equal the proposed spelling, and
store the actual source spelling. No fuzzy alias, deleted words, accent removal,
property change, extra fact, model call or old artifact rewrite. Retain all raw
strict-case failures and count rescued versus still quarantined sources.

The v2 reader has not been run. Use the v3 projected metadata for the complete
dev/valid matched readers, with unchanged v2 source roles, prompt and ranking.
Do not call this a v2 reader score. It remains development, with all v1 negative
reader results preserved. Freeze outputs before separate scoring. The cumulative
local ledger retains every prior call. The completed dev capture made 431 model
calls because rejected duplicate notes were not memoized. Validation may have
the same cost; those failed calls cannot be discarded from accounting. Before
the v3 reader, explicitly extend the **same cumulative local cap to 2600**,
keeping <=600/3600s per phase. This covers both full matched reader runs and the
optional oracle controls even at the observed rejection rate. Old v1/v2 caps
and failures remain frozen. No further API calls occur. The projection itself
still makes zero generations. No wrong-answer retry or discarded reservation.
