# Persona battery v1: execution integrity successor

**Use `scripts/persona_battery_v1.py` for new executions.** This is an engineering correction of PR 90 R1–R3, dated 2026-11-04. It is not a new model experiment and supplies no new evidence for persona quality. The frozen v0 script, configuration, preregistration and results remain unchanged. V1 imports the v0 task builders, controls, scorers and registered readings; its configuration preserves the same thresholds, seeds, input declarations, model limits and budget.

## Corrections

1. `prepare` records a digest-protected execution manifest in `baseline.json`. It binds the effective kernel/profile, prompt switches, inputs, scripts, configuration, proxy URLs and free controls. Every paid resume and analysis validates it. Existing records must have unique known keys, matching metadata and matching prompt digests. Re-running `prepare` cannot adopt old answers under changed settings.
2. `provenance` is copied from saved execution identity. `analysis_provenance` records the analysis tool and verification level separately. Different current settings cause refusal before analysis or any model/proxy access, rather than relabelling old answers.
3. `coverage` reports expected, actual and missing observations, a `not_started`/`partial`/`complete` status and stage-specific `readings_ready`. Incomplete data retain descriptive summaries, but their registered readings are null. P1 automatic fact readings require complete P1 observations. P2 requires all three steps. P3 additionally requires complete blind labels. P7 requires complete answers, judge labels and headline hand labels. Unrequested stages do not prevent completed P1-only or P2-only amendments from being read.

P2 later steps require complete predecessors; P7 labelling requires complete answers. Judge prompts also receive a recorded digest. Analysis exports require a new destination outside the execution folder, protecting historical artifacts from accidental replacement.

## New executions

Use a new private folder for every experimental identity. Existing model/proxy, budget and decision requirements from [v0](../aam-p-persona-v0/README.md) still apply. No new paid run is authorized by this engineering correction.

```text
python scripts/persona_battery_v1.py prepare --items PRIVATE/items.json --notes PRIVATE/notes.jsonl --card PRIVATE/card.md --workdir PRIVATE/new-run
python scripts/persona_battery_v1.py run-p1 --items PRIVATE/items.json --notes PRIVATE/notes.jsonl --card PRIVATE/card.md --workdir PRIVATE/new-run --ledger PRIVATE/ledger.jsonl
python scripts/persona_battery_v1.py analyse --items PRIVATE/items.json --notes PRIVATE/notes.jsonl --card PRIVATE/card.md --workdir PRIVATE/new-run --json PRIVATE/new-export.json
```

The new configuration pins both the immutable predecessor and this new runner. After `prepare`, use the identical configuration, inputs, code and `PERSONA_BATTERY_*` environment values. Moving to another version requires a new execution or an explicitly declared legacy analysis; never re-prepare an old folder to bypass a mismatch.

`PERSONA_BATTERY_KERNEL`, `PERSONA_BATTERY_HONOUR` and `PERSONA_BATTERY_PROFILE` retain the predecessor's meanings. The kernel is loaded at process import, so set these variables before starting the command. Overrides are labelled exploratory settings, not changes to the original preregistration. Example 0.2.0 profile: kernel `scripts/wmb/kernel/memory_kernel.py`, profile JSON `{"min_evidence": 1.0}`. An honour variant additionally uses `PERSONA_BATTERY_HONOUR=1`. Keep each variant in its own folder.

## Historical executions

V1 refuses paid resume and `prepare` for legacy folders without a v1 manifest. To analyse one, explicitly provide the saved aggregate JSON that declares its historical execution provenance, and use its original kernel/profile/prompt settings:

```text
python scripts/persona_battery_v1.py analyse --items PRIVATE/items.json --notes PRIVATE/notes.jsonl --card PRIVATE/card.md --workdir PRIVATE/old-run --legacy-provenance SAVED/results.json --json PRIVATE/new-legacy-export.json
```

Legacy analysis is read-only with respect to the execution folder, including label sheets and maps. It validates available baseline fields and reconstructed record prompts. It preserves the supplied execution provenance and labels its status `legacy-declared`, not `manifest-verified`. The original runner did not save judge prompt digests, which is reported explicitly. A legacy declaration is not retroactive cryptographic proof of its historical execution code. V1 does not invent a missing historical runner digest from the current shell.

The original published aggregate JSON is the declaration for the original frozen run. Later amendments have their own saved per-run JSON. Never pass the original run's declaration for a different variant. V1 does not edit, supersede or overwrite those declarations.

## Validation

`tests/test_persona_battery_v1.py` uses only synthetic inputs and fake models, with the freeze enabled. It covers settings drift, stale/duplicate/unknown records, manifest/control corruption, interrupted resume, provenance, incomplete data, dependent steps, single-stage amendments, legacy read-only behavior and export protection. Completed synthetic data are compared to predecessor summaries/readings. See [the implementation handoff](../../../docs/00-project/pr90-integrity-fix-2026-11-04.md) for final gate results and real saved-data checks.
