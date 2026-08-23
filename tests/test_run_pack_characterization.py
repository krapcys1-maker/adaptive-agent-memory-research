from scripts.run_pack_characterization import FIXTURE, build_pack, load_jsonl, serialize
from scripts.analyze_pack_characterization import analyze


def fixture():
    corpus = load_jsonl(FIXTURE / "corpus.jsonl")
    cases = load_jsonl(FIXTURE / "cases.jsonl")
    return {row["record_id"]: row for row in corpus}, cases


def test_compact_source_footer_reuses_one_path_handle():
    records, _ = fixture()
    text, source_map = serialize("C1_SOURCE_FOOTER", ["C01", "C05"], records)
    assert len(source_map) == 1
    assert text.count("[S01:") == 2
    assert text.count("[S01]=") == 1
    assert records["C01"]["source_path"] == records["C05"]["source_path"]


def test_pack_filters_untrusted_and_reports_every_omission():
    records, cases = fixture()
    result = build_pack(cases[0], records, "C1_SOURCE_FOOTER", "O0_RETRIEVAL", 512)
    assert result["untrusted_exposed"] is False
    assert result["omission_ledger_complete"] is True
    assert result["budget_compliant"] is True
    assert not result["citation_errors"]
    assert not result["evidence_errors"]


def test_governed_order_places_stale_after_current_and_supporting():
    records, cases = fixture()
    result = build_pack(cases[0], records, "T0_TEXT_ONLY", "O1_GOVERNED", 1536)
    buckets = [records[record_id]["bucket"] for record_id in result["included_ids"]]
    assert buckets == sorted(buckets, key={"current": 0, "supporting": 1, "stale_conflicting": 2}.get)


def test_committed_pack_analysis_has_no_integrity_failures():
    result = analyze()
    assert result["integrity_failures"] == []
    assert result["complete_pack_mean_bytes"]["compact_minus_full"] < 0
    primary = next(
        row
        for row in result["paired_format_deltas"]
        if row["budget_utf8"] == 768 and row["order_arm"] == "O0_RETRIEVAL"
    )
    assert primary["mean_compact_minus_full"] > 0
