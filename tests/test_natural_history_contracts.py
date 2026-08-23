import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-natural-history-v0"


def schema(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_revised_json_schemas_are_valid_draft_2020_12():
    jsonschema.Draft202012Validator.check_schema(schema("source-unit-contract-v0.schema.json"))
    jsonschema.Draft202012Validator.check_schema(schema("query-log-contract-v0.schema.json"))


def test_source_unit_accepts_declared_git_and_portable_hashes():
    value = {
        "contract_version": "0.2.0",
        "unit_id": "U-0123456789abcdef",
        "snapshot_commit": "a" * 40,
        "git_object_format": "sha1",
        "source_type": "markdown_section",
        "path": "docs/example.md",
        "locator": {"kind": "heading_path_and_occurrence", "value": "Title > Result#1"},
        "search_text": "Title\nResult\nExact body.",
        "search_text_sha256": "b" * 64,
        "source_blob_sha256": "c" * 64,
        "source_git_object": {"algorithm": "sha1", "object_id": "d" * 40},
        "eligibility_class": "canonical_research",
        "backend_visible_fields": ["unit_id", "search_text"],
    }
    jsonschema.Draft202012Validator(schema("source-unit-contract-v0.schema.json")).validate(value)


def test_source_unit_rejects_hash_length_algorithm_mismatch():
    value = {
        "contract_version": "0.2.0", "unit_id": "U-0123456789abcdef",
        "snapshot_commit": "a" * 64, "git_object_format": "sha1",
        "source_type": "markdown_section", "path": "docs/example.md",
        "locator": {"kind": "heading_path_and_occurrence", "value": "Title#1"},
        "search_text": "Title\nBody", "search_text_sha256": "b" * 64,
        "source_blob_sha256": "c" * 64,
        "source_git_object": {"algorithm": "sha1", "object_id": "d" * 64},
        "eligibility_class": "canonical_research",
        "backend_visible_fields": ["unit_id", "search_text"],
    }
    assert list(jsonschema.Draft202012Validator(schema("source-unit-contract-v0.schema.json")).iter_errors(value))


def test_query_contract_rejects_legacy_unkeyed_origin_hash():
    value = {
        "query_id": "Q-0123456789abcdef",
        "recorded_at": "2026-08-23T00:00:00Z",
        "query_text": "What was frozen before the run?",
        "language": "en",
        "origin_type": "pre-investigation_issue",
        "origin_ref_hash": "a" * 64,
        "query_cutoff_commit": "b" * 40,
        "git_object_format": "sha1",
        "pre_output_attestation": "No candidate backend output or gold evidence search was viewed before this query was frozen.",
        "collection_phase": "retrospective_development",
        "recorded_by_role": "research_agent",
        "storage_class": "git_public",
    }
    errors = list(jsonschema.Draft202012Validator(schema("query-log-contract-v0.schema.json")).iter_errors(value))
    assert errors


def test_query_contract_accepts_private_random_receipt():
    value = {
        "query_id": "Q-0123456789abcdef",
        "recorded_at": "2026-08-23T00:00:00Z",
        "query_text": "What was frozen before the run?",
        "language": "en",
        "origin_type": "verbatim_user_question",
        "origin_receipt": {
            "mode": "private_random_receipt", "value": "OR-89abcdef0123456789abcdef01234567",
            "generation": "csprng-128",
        },
        "query_cutoff_commit": "b" * 40,
        "git_object_format": "sha1",
        "pre_output_attestation": "No candidate backend output or gold evidence search was viewed before this query was frozen.",
        "collection_phase": "retrospective_development",
        "recorded_by_role": "user",
        "storage_class": "local_restricted",
        "capture_sequence": 1,
    }
    jsonschema.Draft202012Validator(schema("query-log-contract-v0.schema.json")).validate(value)


def test_query_contract_rejects_short_or_mislabeled_random_receipt():
    value = {
        "query_id": "Q-0123456789abcdef", "recorded_at": "2026-08-23T00:00:00Z",
        "query_text": "What was frozen?", "language": "en", "origin_type": "verbatim_user_question",
        "origin_receipt": {"mode": "private_random_receipt", "value": "OR-deadbeef", "generation": "hmac-sha256"},
        "query_cutoff_commit": "b" * 40, "git_object_format": "sha1",
        "pre_output_attestation": "No candidate backend output or gold evidence search was viewed before this query was frozen.",
        "collection_phase": "retrospective_development", "recorded_by_role": "user",
        "storage_class": "local_restricted", "capture_sequence": 1,
    }
    assert list(jsonschema.Draft202012Validator(schema("query-log-contract-v0.schema.json")).iter_errors(value))


def test_source_unit_rejects_duplicate_aliases_and_unsafe_control():
    value = {
        "contract_version": "0.2.0", "unit_id": "U-0123456789abcdef",
        "snapshot_commit": "a" * 40, "git_object_format": "sha1",
        "source_type": "markdown_section", "path": "docs/example.md",
        "locator": {"kind": "heading_path_and_occurrence", "value": "Title#1"},
        "search_text": "Title\u0000Body", "search_text_sha256": "b" * 64,
        "source_blob_sha256": "c" * 64,
        "source_git_object": {"algorithm": "sha1", "object_id": "d" * 40},
        "eligibility_class": "canonical_research", "backend_visible_fields": ["unit_id", "search_text"],
        "source_aliases": [
            {"path": "docs/alias.md", "locator": "Title#1"},
            {"path": "docs/alias.md", "locator": "Title#1"},
        ],
    }
    messages = [error.message for error in jsonschema.Draft202012Validator(schema("source-unit-contract-v0.schema.json")).iter_errors(value)]
    assert len(messages) >= 2
