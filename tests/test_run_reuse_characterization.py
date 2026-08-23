from pathlib import Path

from scripts.run_reuse_characterization import (
    FTS5Retriever,
    PACK_BUDGET,
    SOURCE,
    build_pack,
    load_jsonl,
    rrf,
    validate_inputs,
)
from scripts.analyze_reuse_characterization import analyze


def fixture():
    corpus = load_jsonl(SOURCE / "corpus.jsonl")
    queries = load_jsonl(SOURCE / "queries.jsonl")
    return corpus, queries


def test_frozen_fixture_and_citations_are_exact():
    corpus, queries = fixture()
    result = validate_inputs(corpus, queries, SOURCE / "evidence.md")
    assert len(result["citation_hashes"]) == 36
    assert len(queries) == 20


def test_fts5_returns_exact_identifier_record(tmp_path: Path):
    corpus, _ = fixture()
    backend = FTS5Retriever(corpus, tmp_path / "fts.sqlite3")
    try:
        assert backend.retrieve("PMLAB-REUSE-CHAR-001", 1) == ["E31"]
    finally:
        backend.close()


def test_rrf_uses_rank_and_deterministic_id_tie_break():
    assert rrf([["A", "B"], ["B", "C"]], 3) == ["B", "A", "C"]
    assert rrf([["B"], ["A"]], 2) == ["A", "B"]


def test_bucketed_pack_separates_stale_and_omits_untrusted():
    corpus, _ = fixture()
    records = {row["record_id"]: row for row in corpus}
    pack = build_pack("bucketed", ["E09", "E10", "E11"], records)
    assert pack["placements"]["E09"] == "current"
    assert pack["placements"]["E10"] == "stale_conflicting"
    assert "E11" not in pack["included"]
    assert {row["reason"] for row in pack["omitted"]} == {"untrusted"}
    assert len(pack["text"].encode("utf-8")) <= PACK_BUDGET


def test_all_pack_modes_report_budget_omissions():
    corpus, _ = fixture()
    records = {row["record_id"]: row for row in corpus}
    for mode in ("raw", "cited", "bucketed"):
        pack = build_pack(mode, [row["record_id"] for row in corpus[:10]], records, budget=80)
        assert pack["omitted"]
        assert pack["utf8_bytes"] <= 80


def test_posthoc_failure_analysis_is_derived_from_committed_outputs():
    result = analyze()
    assert result["rrf_forbidden_subset_of_dense"] is True
    assert result["forbidden_query_sets"]["C0_FASTEMBED"] == ["Q04", "Q06", "Q07", "Q08"]
    assert result["forbidden_query_sets"]["C2_RRF"] == ["Q04", "Q06", "Q07"]
    assert result["unanswerable_candidates"]["B2_FTS5"][0]["ranked"]
    dense = result["packaging_by_arm"]["C0_FASTEMBED"]
    assert dense["bucketed"]["required_retained"] == dense["raw"]["required_retained"]
