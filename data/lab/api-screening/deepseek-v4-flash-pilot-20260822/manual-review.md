# Manual admission review

Reviewer: Codex (single reviewer; not independent)

Status: failed-policy-check

## Results

- 25/25 jobs returned schema-valid JSON with exact job IDs.
- Source identity and DOI were attached deterministically from frozen jobs rather than trusted from model output.
- The include/maybe/exclude mix correctly exposed substantial query drift, especially in semantic compression and durable storage.
- 24/25 screening decisions were plausible from the supplied title and abstract for triage purposes.
- `cls_replay-005` had no abstract but was marked `include` based on its title. This is overconfident under the preregistered rule that insufficient metadata must preserve uncertainty.

## Decision

Do not expand screening-v1. Revise the prompt so a missing or non-informative abstract can never receive `include`, freeze the same deterministic selection under screening-v2, and rerun the admission pilot. Preserve this failed pilot and its cost.
