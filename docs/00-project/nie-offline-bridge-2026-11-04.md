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

## Opt-in typed claims and local reader follow-up (2026-11-04)

The [local reader pilot](../../data/lab/nie-local-reader-v1/README.md) now executes the pending boundary on authored closed fields. Replay schema v2 optionally preserves `typed_claim: {slot, value}` in fictional item metadata and records its contract dependency digest. Validate the slot syntax and a whole-phrase value occurrence in source text; this does not establish semantic entailment or extract facts from free prose. Legacy rows keep their item IDs and receive no invented typed claim.

`scripts/nie_memory_contract.py` can check a supplied slot against **shown** typed evidence. It accepts/corrects from one unambiguous fictional claim and abstains on conflict, absence or unsupported task. Actual NIE producers/prompts remain unchanged. The local pilot's 48/48 delivered answers include 12 code corrections; the raw reader achieved 36/48. Fixture-supplied routing, structured writing and the local reader limit the result; the original P2 verdict still stands.

The pilot's `UNKNOWN` is a recall-controller signal, not a blanket personality refusal policy. Genuine new details may still enter the authorized improvisation/write-back flow; the integration layer must first distinguish missing data from failed retrieval and avoid overwriting an existing fact. This bridge/guard does not implement that dispatcher or revision policy.
