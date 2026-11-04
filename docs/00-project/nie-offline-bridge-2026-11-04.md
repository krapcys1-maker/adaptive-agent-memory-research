# NIE persona journal: read-only offline bridge

## Observed integration gap and scope

At NIE commit `5cb731e65844cc6e9c3f8bcdc0a8220a1a6eb2dd`, [`persona.po_publikacji`](https://github.com/krapcys1-maker/nothing-is-accidental-agent/blob/5cb731e65844cc6e9c3f8bcdc0a8220a1a6eb2dd/agent-v2/persona.py#L280) appends published improvised details to a JSONL journal. [`persona.blok`](https://github.com/krapcys1-maker/nothing-is-accidental-agent/blob/5cb731e65844cc6e9c3f8bcdc0a8220a1a6eb2dd/agent-v2/persona.py#L167) renders the card and an instruction; the inspected Python tree has no kernel import or read path for that detail journal. This is a local source snapshot, not a claim about the server.

Implement an additive research-side bridge, with no change to NIE, its prompts or deployment. It reads an explicitly supplied journal, maps it to the existing live 0.2.0 kernel and emits a local replay artifact. No model calls or embeddings. A synthetic public fixture demonstrates the data path; it cannot establish generated-answer consistency or repair the negative P2 result.

## Contract fixed before the demonstration

- Input uses the existing fields `kiedy`, `typ_zadania=notka_zycie`, `id_notki`, `tekst`, `zrodlo=improwizacja`, and nullable `supersedes`. Require a timezone-aware timestamp and nonempty text/publication ID. Reject unsupported sources and non-null supersession rather than guessing semantics.
- `kiedy` is availability/recording time. Dates mentioned inside invented text never backdate availability. Filter future rows **before indexing**, so even their vocabulary statistics cannot affect an earlier replay.
- Preserve improvised provenance as kernel `fiction_autobio`, kind `event`, with the original publication/run metadata. An identical row is deduplicated; conflicting rows for the same publication ID fail explicitly. Do not promote these details to canonical biography or world knowledge.
- Use the shipped lexical profile with an explicit infinite offline deadline and timezone requirement; no embedder is loaded. Any diagnostic profile override is recorded, is lexical-only, and does not change kernel defaults. The existing persona task-type restriction remains effective.
- Enforce a separate **word** budget over the complete rendered context, including the fictional-provenance heading and date labels. Take a ranked prefix that fits. This is not a tokenizer budget; preserve the kernel's distinct characters/4 estimate in the artifact. No partial biography sentence is fabricated to fill a budget.
- Require query and as-of time explicitly; refuse output overwrite. Record input and kernel/source hashes and deterministic selected IDs/context. Read-only replay does not write back, choose a universal profile or generate answers.

The next behavioral measurement is an end-to-end replay with a reader and consistency scoring. This bridge supplies its data boundary; it is not that measurement. Real journals and replay text remain private local artifacts. The public demonstration contains only authored synthetic details.
