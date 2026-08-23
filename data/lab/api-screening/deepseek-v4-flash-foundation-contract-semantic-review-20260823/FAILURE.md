# Foundation semantic review worker v1 pre-freeze failure

Status: invalidated before input freeze and before API

Runner commit: `e452f96`

The safety test rejected the prepared job because the canonical contract prose
mentions the path name `invalid-mutations.json`. The mutation artifact and its case
contents were not included in `subject_artifacts`; the assertion incorrectly treated
a referenced filename as equivalent to sending its contents.

The v1 job and prompt are preserved but must never be frozen or executed. No API
request occurred and cost was USD 0. The v2 repair changes the run ID and narrows
the test to actual subject paths, registered mutation case IDs, result status text,
and current-state content. Subject packet, questions, output schema, model, prompt,
temperature, and budget remain unchanged.

