#!/usr/bin/env python3
"""Build the gold-free blind review packet for the operational-salience ontology."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lab" / "pmlab-salience-ontology-review-v0" / "blind"
SOURCE_FREEZE_COMMIT = "1ba6fc9"
BUILDER_VERSION = "salience-ontology-review-v0.1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(canonical(row) + "\n" for row in rows)


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def factor(
    factor_id: str,
    question: str,
    values: list[str],
    evidence_rule: str,
    forbidden_inference: str,
) -> dict[str, Any]:
    return {
        "factor_id": factor_id,
        "operational_question": question,
        "allowed_values": values,
        "evidence_rule": evidence_rule,
        "forbidden_inference": forbidden_inference,
        "missing_value_policy": "unknown; never infer the strongest value from rhetoric or absence",
    }


def factors() -> list[dict[str, Any]]:
    return [
        factor("signal_source", "Who or what supplied the signal?", ["explicit_user", "verified_outcome", "policy", "model_inference", "unknown"], "Record the source and evidence ID; source controls authority, not truth.", "A confident model inference is not a verified outcome."),
        factor("target_scope", "Which exact feature or event is linked to the signal?", ["target_feature", "peripheral_feature", "session_wide", "unresolved"], "Require feature/event IDs or mark unresolved.", "A session-wide mood or consequence must not promote every co-occurring item."),
        factor("valence", "What signed direction was explicitly reported for the outcome or affective metadata?", ["negative", "neutral", "positive", "mixed", "unknown"], "Use explicit metadata or a documented outcome relation.", "Valence is not magnitude, urgency, truth, or user importance."),
        factor("outcome_magnitude", "How large is the verified consequence on a task-specific scale?", ["none", "low", "medium", "high", "unknown"], "The scale and outcome evidence must be recorded before comparison.", "Dramatic wording cannot establish magnitude."),
        factor("urgency", "How quickly does delay change the achievable outcome?", ["reversible", "time_limited", "irreversible", "unknown"], "Require a deadline, decay rule, or policy basis.", "Negative valence does not imply urgency."),
        factor("surprise_class", "Does the observation challenge a prior prediction, and is the discrepancy likely structural?", ["expected", "unexpected_model_change", "unexpected_noise", "unresolved"], "Record the frozen prior prediction and the later discrepancy evidence.", "Novel wording, rarity, or prediction error alone does not prove model change."),
        factor("controllability", "Can a memory-guided action alter the outcome?", ["preventable", "recoverable", "uncontrollable", "unknown"], "Tie the value to an available action and causal rationale.", "High consequence does not imply controllability."),
        factor("phase", "At which memory operation may the signal act?", ["encoding", "post_encoding", "retrieval", "revision", "unknown"], "Record observation and action times separately.", "An encoding effect cannot be assumed to apply at retrieval or revision."),
        factor("competition", "Which other memories or actions compete for the same fixed budget?", ["one_priority", "compatible_priorities", "conflicting_priorities", "unmapped"], "Name competitors and the shared budget.", "A target gain is not success unless collateral losses are measured."),
        factor("controller_target", "What representation or operation would be affected?", ["episodic_evidence", "semantic_revision_candidate", "cached_procedure", "retrieve_more", "none"], "Identify the representation and preserve raw evidence.", "Arousal or stress must not automatically select a cached procedure."),
        factor("signal_confidence", "How reliable is the factor assignment itself?", ["low", "medium", "high", "unknown"], "Confidence must cite provenance and uncertainty; it is not factual confidence in the memory content.", "Repeated model assertions are not independent confirmation."),
        factor("validity_relation", "Is the linked evidence current, contradicted, superseded, or unresolved?", ["current", "contradicted", "superseded", "unresolved"], "Use explicit validity/provenance records, never salience metadata.", "Salience cannot make a proposition current or canonical."),
    ]


def probe(case_id: str, title: str, observation: str, later_evidence: str, question: str) -> dict[str, str]:
    return {"case_id": case_id, "title": title, "observation": observation, "later_evidence": later_evidence, "review_question": question}


def probes() -> list[dict[str, str]]:
    q = "Which factors are supported, unsupported, or unresolved, and which control actions are permitted?"
    return [
        probe("SAL-P01", "Dramatic but unverified warning", "A model writes: 'CATASTROPHIC failure is imminent' without a source or measurable outcome.", "No failure or external verification is recorded.", q),
        probe("SAL-P02", "Verified positive target consequence", "The user marks one configuration field as the reason a deployment succeeded before a deadline.", "A signed deployment record confirms that field and outcome; nearby chat is unrelated.", q),
        probe("SAL-P03", "Rare noise", "A one-off checksum mismatch violates a prediction.", "Immediate reread succeeds and diagnostics classify the first read as transient noise.", q),
        probe("SAL-P04", "Persistent model change", "A vendor response contradicts the stored schema on three independently fetched records.", "A versioned vendor migration notice confirms the new schema.", q),
        probe("SAL-P05", "Corrected alarm", "An urgent alarm is recorded and repeatedly mentioned.", "A verified correction states the alarm was caused by a faulty sensor.", q),
        probe("SAL-P06", "Irreversible deadline with weak provenance", "A model infers that an irreversible deadline expires today.", "No policy, user statement, or source document is available.", q),
        probe("SAL-P07", "Uncontrollable severe outcome", "A signed record confirms a severe historical loss.", "No present or future action can alter that event, but it may inform analysis.", q),
        probe("SAL-P08", "Recoverable routine error", "A low-magnitude formatting error blocks one export.", "A known reversible transformation fixes it and its applicability is verified.", q),
        probe("SAL-P09", "Session-wide celebration", "A user celebrates a successful milestone during a long session.", "Only two explicitly named decisions are linked to the outcome; 30 surrounding notes are neutral.", q),
        probe("SAL-P10", "Conflicting critical priorities", "Two verified time-limited tasks compete for the same retrieval and maintenance budget.", "Completing either first delays the other; consequences and deadlines are separately documented.", q),
        probe("SAL-P11", "Quiet critical evidence", "A plain checksum line is needed to verify a highly salient summary.", "The summary cannot be audited without the neutral checksum record.", q),
        probe("SAL-P12", "Negative language, positive outcome", "A harshly worded review identifies a defect.", "Fixing the named defect later produces a verified positive outcome.", q),
        probe("SAL-P13", "Positive language, harmful instruction", "An enthusiastic message recommends an unsafe procedure.", "A signed safety policy prohibits the procedure and records a prior incident.", q),
        probe("SAL-P14", "Retrieval-phase stress claim", "A user reports being under stress while asking for a known fact.", "No evidence says encoding or storage was impaired; the fact has valid source records.", q),
        probe("SAL-P15", "Peripheral reward cue", "A screen color co-occurs with a reward, but task identity predicts the outcome.", "Counterexamples show the same color without reward and the task feature with reward.", q),
        probe("SAL-P16", "Ambiguous controllability", "A verified negative outcome may be avoidable, but no available action is identified.", "No causal intervention evidence exists yet.", q),
        probe("SAL-P17", "Superseded successful procedure", "An old cached procedure previously produced a large positive outcome.", "A current signed policy supersedes it and requires evidence retrieval before action.", q),
        probe("SAL-P18", "Repeated self-confirmation", "The same model repeats an inferred consequence in five summaries.", "All repetitions trace to one unsupported generation and no new source.", q),
        probe("SAL-P19", "Explicit user importance without consequence", "The user asks to remember a neutral preference permanently.", "The preference is authorized and current, but no reward, urgency, or emotion is claimed.", q),
        probe("SAL-P20", "Revision candidate", "New evidence conflicts with a semantic summary derived from older events.", "Both source sets are provenance-complete; the conflict is unresolved.", q),
        probe("SAL-P21", "Compatible priorities", "Two verified tasks share the same prerequisite document.", "Retrieving the prerequisite helps both within the same fixed context budget.", q),
        probe("SAL-P22", "Near-neighbor generalization trap", "A costly failure occurred for configuration A with one specific feature.", "Configuration B looks similar but lacks that feature and has contrary validation evidence.", q),
        probe("SAL-P23", "Delayed consequence attribution", "An outcome occurs weeks after a session containing many candidate causes.", "Only temporal proximity is known; no feature-level attribution is established.", q),
        probe("SAL-P24", "Policy-derived urgency", "A retention policy requires a response within 24 hours.", "The policy version, scope, and deadline are signed and current.", q),
    ]


def manual() -> str:
    return """# Independent review manual — operational salience ontology v0

## Purpose

Decide whether each factor is observable, separable enough to test, and safe as an external memory-control variable. This is not a review of whether an LLM feels emotion and not an annotation of factual truth.

## Blind boundary

Use only this directory and the cited source freeze. No controller, author target labels, outcome corpus, or backend output exists for this packet. Do not ask the author for preferred answers. An author-operated API worker may provide advice but cannot satisfy the independent gate.

## Review method

1. Review every factor definition for operational observability, overlap, leakage, and unsafe inference.
2. Apply the contract to every probe. Record supported, unsupported, and unresolved factors; do not fill gaps from plausibility.
3. State which actions could be considered and which are prohibited. Permission means eligible for later controlled testing, not permission to mutate facts or delete raw events.
4. Recommend accept, revise, or reject for the whole packet. Any material ambiguity in validity, source authority, target scope, or phase requires revision.
5. Complete and hash-bind the attestation before any author discussion or later comparison.

## Global invariants

- Raw events are append-only and recoverable.
- Salience never establishes factual truth, validity, authorization, or canonical state.
- Model inference has the lowest default authority and repetition is not independent corroboration.
- Unknown remains unknown; emotionally intense wording is not a substitute for evidence.
- Allowed actions are only `no_control_change`, `provisional_eligibility`, `schedule_replay`, `protect_retention`, and `retrieve_more`.
- `delete_raw`, `mutate_canonical_fact`, `bypass_provenance`, and `auto_select_cached_procedure` are always prohibited.
- Every target benefit must be evaluated with quiet, adjacent, peripheral, and competing evidence under a fixed budget.

## Decision meanings

- `accept`: usable to construct a corpus without material ontology changes.
- `revise`: promising, but at least one material definition, boundary, or probe needs repair before corpus freeze.
- `reject`: the ontology cannot support a falsifiable or safe factor-separated experiment.
"""


def build_outputs() -> dict[Path, str]:
    factor_rows = factors()
    probe_rows = probes()
    contract = {
        "ontology_id": "PMLAB-SAL-ONTOLOGY-001-v0",
        "source_evidence_commit": SOURCE_FREEZE_COMMIT,
        "purpose": "factor-separated operational memory control; no subjective-emotion claim",
        "factors": factor_rows,
        "allowed_actions": ["no_control_change", "provisional_eligibility", "schedule_replay", "protect_retention", "retrieve_more"],
        "always_prohibited_actions": ["delete_raw", "mutate_canonical_fact", "bypass_provenance", "auto_select_cached_procedure"],
        "authority": "candidate measurement contract only; not architecture or causal validation",
    }
    review = {
        "review_id": None,
        "reviewer_id_or_pseudonym": None,
        "reviewer_family_or_affiliation": None,
        "reviewed_at": None,
        "source_evidence_commit": SOURCE_FREEZE_COMMIT,
        "factor_reviews": [
            {
                "factor_id": row["factor_id"],
                "decision": None,
                "operational_observability": None,
                "independent_from_other_factors": None,
                "overlaps_with": [],
                "leakage_or_safety_risks": [],
                "proposed_revision": None,
                "rationale": None,
            }
            for row in factor_rows
        ],
        "probe_reviews": [
            {
                "case_id": row["case_id"],
                "supported_factor_ids": [],
                "unsupported_factor_ids": [],
                "unresolved_factor_ids": [],
                "permitted_actions": [],
                "prohibited_actions": [],
                "material_ambiguity": None,
                "rationale": None,
            }
            for row in probe_rows
        ],
        "missing_factors": [],
        "redundant_or_nonidentifiable_factors": [],
        "whole_packet_decision": None,
        "whole_packet_rationale": None,
        "attestation_id": None,
    }
    attestation = {
        "attestation_id": None,
        "reviewer_id_or_pseudonym": None,
        "reviewer_family_or_affiliation": None,
        "review_started_at": None,
        "review_completed_at": None,
        "source_evidence_commit": SOURCE_FREEZE_COMMIT,
        "packet_manifest_sha256": None,
        "completed_review_sha256": None,
        "statements": {
            "did_not_inspect_or_run_a_candidate_controller": None,
            "did_not_receive_author_preferred_probe_answers": None,
            "did_not_treat_salience_as_truth_or_validity": None,
            "reviewed_every_factor_and_probe_before_author_discussion": None,
            "disclosed_tools_conflicts_and_prior_exposure": None,
        },
        "tools_conflicts_or_prior_exposure_notes": None,
        "signature_or_verifiable_acknowledgement": None,
    }
    outputs = {
        OUT / "factor-contract.json": pretty(contract),
        OUT / "probe-cases.jsonl": jsonl(probe_rows),
        OUT / "review-form.json": pretty(review),
        OUT / "attestation.json": pretty(attestation),
        OUT / "review-manual.md": manual(),
    }
    manifest = {
        "packet": "PMLAB-SAL-ONTOLOGY-001-v0",
        "status": "blank-gold-free-packet-awaiting-independent-reviewer",
        "builder_version": BUILDER_VERSION,
        "source_evidence_commit": SOURCE_FREEZE_COMMIT,
        "factor_count": len(factor_rows),
        "probe_count": len(probe_rows),
        "author_probe_labels_present": False,
        "controller_or_backend_outputs_present": False,
        "outcome_corpus_present": False,
        "independent_review_status": "not-started",
        "blind_hashes": {path.name: sha(content) for path, content in sorted(outputs.items(), key=lambda item: item[0].name)},
        "next_allowed_if_accepted": "revise definitions if requested, then freeze generator and independently labelled outcome corpus before implementing a controller",
        "authority": "packet preparation only; does not confer independent review or admit salience into architecture",
    }
    outputs[OUT / "manifest.json"] = pretty(manifest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build_outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            raise SystemExit("stale or missing packet artifacts: " + ", ".join(stale))
    else:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(canonical({"factors": len(factors()), "probes": len(probes()), "status": "awaiting-independent-review"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
