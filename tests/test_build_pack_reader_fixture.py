import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_reader_fixture_shape_and_bilingual_groups():
    groups = load_jsonl(BASE / "internal" / "groups.jsonl")
    cases = load_jsonl(BASE / "cases.jsonl")
    corpus = load_jsonl(BASE / "corpus.jsonl")
    assert len(groups) == 16
    assert len(cases) == 32
    assert len(corpus) == 256
    assert Counter(case["group_id"] for case in cases) == {group["group_id"]: 2 for group in groups}
    assert all({case["language"] for case in cases if case["group_id"] == group["group_id"]} == {"en", "pl"} for group in groups)


def test_reader_source_spans_are_exact():
    for record in load_jsonl(BASE / "corpus.jsonl"):
        lines = (ROOT / record["source_path"]).read_text(encoding="utf-8").splitlines()
        assert lines[record["line_start"] - 1] == record["text"]


def test_reader_conditions_are_opaque_unique_and_complete():
    conditions = load_jsonl(BASE / "internal" / "condition-map.jsonl")
    schedule = load_jsonl(BASE / "blind" / "schedule.jsonl")
    assert len(conditions) == len(schedule) == 128
    assert len({row["condition_id"] for row in conditions}) == 128
    assert all(re.fullmatch(r"C[0-9a-f]{16}", row["condition_id"]) for row in conditions)
    assert {row["condition_id"] for row in conditions} == {row["condition_id"] for row in schedule}
    assert all(set(row) == {"sequence", "condition_id", "case_id"} for row in schedule)


def test_reader_prompt_safe_cases_do_not_contain_gold():
    forbidden = {"answer_atoms", "stale_atoms", "required_local_ids", "format_arm", "order_arm"}
    for row in load_jsonl(BASE / "cases.jsonl"):
        assert forbidden.isdisjoint(row)


def test_reader_gold_is_group_consistent_and_stale_disjoint():
    gold = load_jsonl(BASE / "internal" / "gold.jsonl")
    by_group = {}
    for row in gold:
        assert set(row["answer_atoms"]).isdisjoint(row["stale_atoms"])
        assert set(row["required_local_ids"]) <= {"R01", "R02", "R03"}
        assert len(row["answer_atoms"]) == len(row["required_local_ids"])
        signature = (row["answer_atoms"], row["stale_atoms"], row["required_local_ids"])
        by_group.setdefault(row["group_id"], signature)
        assert by_group[row["group_id"]] == signature


def test_reader_record_bucket_shape_matches_protocol():
    corpus = load_jsonl(BASE / "corpus.jsonl")
    for case_id in {f"{row['group_id']}-{row['language'].upper()}" for row in corpus}:
        group_id, language = case_id.rsplit("-", 1)
        rows = [row for row in corpus if row["group_id"] == group_id and row["language"] == language.lower()]
        assert Counter(row["bucket"] for row in rows) == {
            "current": 2,
            "supporting": 2,
            "stale_conflicting": 2,
            "distractor": 2,
        }
