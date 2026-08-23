import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-characterization-v0"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_pack_fixture_has_frozen_shape_and_strata():
    corpus = load_jsonl(BASE / "corpus.jsonl")
    cases = load_jsonl(BASE / "cases.jsonl")
    assert len(corpus) == 36
    assert len(cases) == 24
    assert Counter(case["required_position"] for case in cases) == {"early": 6, "middle": 6, "late": 12}
    assert Counter(case["required_count"] for case in cases) == {2: 18, 3: 6}
    assert sum(case["required_source_reuse"] for case in cases) == 6
    assert sum(case["required_locator_class"] == "long" for case in cases) == 6


def test_pack_fixture_source_spans_are_exact():
    for record in load_jsonl(BASE / "corpus.jsonl"):
        lines = (ROOT / record["source_path"]).read_text(encoding="utf-8").splitlines()
        resolved = "\n".join(lines[record["line_start"] - 1 : record["line_end"]])
        assert resolved == record["text"]


def test_pack_cases_have_unique_candidates_and_safe_required_records():
    records = {row["record_id"]: row for row in load_jsonl(BASE / "corpus.jsonl")}
    for case in load_jsonl(BASE / "cases.jsonl"):
        assert len(case["candidate_ids"]) == len(set(case["candidate_ids"])) == 7
        assert 1 <= len(case["required_ids"]) <= 3
        assert set(case["required_ids"]) <= set(case["candidate_ids"])
        for record_id in case["required_ids"]:
            assert records[record_id]["trust"] == "reviewed"
            assert records[record_id]["bucket"] in {"current", "supporting"}
