import json

from scripts.build_evidence_sufficiency_corpus import content_hash, make_cases, write_corpus


def test_corpus_is_deterministic_balanced_and_has_all_strata(tmp_path):
    first = make_cases()
    second = make_cases()

    assert first == second
    assert len(first) == 36
    assert len({case["case_id"] for case in first}) == 36
    assert sum(case["language"] == "en" for case in first) == 18
    assert sum(case["language"] == "pl" for case in first) == 18
    assert len({case["stratum"] for case in first}) == 18
    assert sum(case["critical"] for case in first) == 12

    manifest = write_corpus(tmp_path)
    written = [json.loads(line) for line in (tmp_path / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert written == first
    assert manifest["case_sha256"] == content_hash(first)


def test_retrieval_miss_is_not_converted_to_collection_absence():
    by_stratum = {case["stratum"]: case for case in make_cases() if case["language"] == "en"}

    recoverable = by_stratum["missing-facet-recoverable"]
    assert recoverable["truth"]["collection_answer_state"] == "full"
    assert recoverable["truth"]["current_evidence_sufficient"] is False
    assert recoverable["truth"]["expected_action"] == "RETRIEVE_MISSING"
    assert any(not row["retrieved"] for row in recoverable["evidence"])

    absent = by_stratum["absent-with-similar-distractor"]
    assert absent["truth"]["collection_answer_state"] == "none"
    assert absent["truth"]["expected_action"] == "ABSTAIN_NOT_FOUND"
    assert any(row["retrieved"] for row in absent["evidence"])


def test_incomplete_inventory_prohibits_not_found_claim():
    cases = [case for case in make_cases() if case["stratum"] == "incomplete-inventory-no-hit"]
    assert len(cases) == 2
    for case in cases:
        assert case["collection_scope"]["inventory_complete"] is False
        assert case["collection_scope"]["unsearched_domains"] == ["offline-replica"]
        assert case["truth"]["expected_action"] == "ABSTAIN_INCONCLUSIVE"


def test_every_obligation_and_evidence_reference_is_well_formed():
    for case in make_cases():
        obligations = {row["obligation_id"] for row in case["obligations"]}
        sources = {row["source_id"] for row in case["evidence"]}
        assert set(case["truth"]["required_obligation_ids"]) == obligations
        for row in case["evidence"]:
            assert set(row["supports"]) <= obligations
            assert set(row["contradicts"]) <= obligations
        for claim in case["reader_signals"]["proposed_claims"]:
            assert set(claim["obligation_ids"]) <= obligations
            assert set(claim["cited_source_ids"]) <= sources
