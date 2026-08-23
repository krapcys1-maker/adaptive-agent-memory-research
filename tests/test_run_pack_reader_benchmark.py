import importlib.util
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pack_reader", ROOT / "scripts" / "run_pack_reader_benchmark.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_serializer_changes_only_locator_or_order_not_identity():
    case = load_jsonl(MODULE.BASE / "cases.jsonl")[0]
    records = MODULE.records_for_case(case, load_jsonl(MODULE.BASE / "corpus.jsonl"))
    identities = []
    for format_arm in ("F0_FULL", "F1_COMPACT"):
        for order_arm in ("O0_RETRIEVAL", "O1_GOVERNED"):
            text, identity = MODULE.serialize_evidence(case, records, format_arm, order_arm)
            assert text.startswith("EVIDENCE\n")
            assert all(local_id in text for local_id in case["all_local_ids"])
            identities.append(sorted(identity, key=lambda row: row["record_id"]))
    assert all(identity == identities[0] for identity in identities[1:])


def test_governed_order_is_stable_bucket_order():
    case = load_jsonl(MODULE.BASE / "cases.jsonl")[0]
    records = MODULE.records_for_case(case, load_jsonl(MODULE.BASE / "corpus.jsonl"))
    ids = MODULE.ordered_ids(case, records, "O1_GOVERNED")
    ranks = {"current": 0, "supporting": 1, "stale_conflicting": 2, "distractor": 3}
    assert [ranks[records[local_id]["bucket"]] for local_id in ids] == sorted(ranks[records[local_id]["bucket"]] for local_id in ids)


def test_exact_response_validator():
    valid = '{"answer_atoms":["G01-ACTIVE-A"],"citations":["R01"],"abstain":false}'
    assert MODULE.validate_response(valid)["citations"] == ["R01"]
    for invalid in (
        '{"answer_atoms":[],"citations":[],"abstain":false,"reason":"x"}',
        '{"answer_atoms":[],"citations":["current"],"abstain":false}',
        '{"answer_atoms":"x","citations":[],"abstain":false}',
    ):
        try:
            MODULE.validate_response(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid response passed")


def test_prompt_packets_are_blinded_and_identity_matched():
    packets, audit = MODULE.build_packets()
    assert len(packets) == 128
    assert audit["passed"] is True
    serialized = json.dumps(packets, ensure_ascii=False)
    for forbidden in ("F0_FULL", "F1_COMPACT", "O0_RETRIEVAL", "O1_GOVERNED", "expected_answer", "stale_atoms", "required_local_ids"):
        assert forbidden not in serialized


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def score_synthetic_run(tmp_path, monkeypatch, perfect: bool):
    monkeypatch.setattr(MODULE, "RUN_DIR", tmp_path)
    packets, audit = MODULE.build_packets()
    write_jsonl(tmp_path / "prompt-packets.jsonl", packets)
    (tmp_path / "prompt-audit.json").write_text(json.dumps(audit) + "\n", encoding="utf-8")
    (tmp_path / "system-prompt.txt").write_text(MODULE.SYSTEM_PROMPT + "\n", encoding="utf-8")
    mappings = load_jsonl(MODULE.BASE / "internal" / "condition-map.jsonl")
    gold = {row["case_id"]: row for row in load_jsonl(MODULE.BASE / "internal" / "gold.jsonl")}
    responses = []
    for mapping in mappings:
        truth = gold[mapping["case_id"]]
        value = {
            "answer_atoms": truth["answer_atoms"] if perfect else [],
            "citations": truth["required_local_ids"] if perfect else [],
            "abstain": False,
        }
        responses.append({"condition_id": mapping["condition_id"], "schema_valid": True, "value": value, "errors": []})
    write_jsonl(tmp_path / "responses.jsonl", responses)
    write_jsonl(tmp_path / "raw-responses.jsonl", [])
    write_jsonl(tmp_path / "calls.jsonl", [])
    input_names = ("prompt-packets.jsonl", "prompt-audit.json", "system-prompt.txt")
    raw_names = ("responses.jsonl", "raw-responses.jsonl", "calls.jsonl")
    digest = lambda name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
    manifest = {
        "status": "raw-responses-frozen", "prompt_freeze_commit": "test-commit", "run_cost_usd": 0,
        "hashes": {name: digest(name) for name in input_names},
        "raw_hashes": {name: digest(name) for name in raw_names},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    return MODULE.score()


def test_scorer_passes_perfect_synthetic_run(tmp_path, monkeypatch):
    summary = score_synthetic_run(tmp_path, monkeypatch, perfect=True)
    assert summary["all_compatibility_gates_passed"] is True
    assert all(row["group_exact_answer_count"] == 16 for row in summary["arms"])


def test_absolute_competence_rejects_equal_total_failure(tmp_path, monkeypatch):
    summary = score_synthetic_run(tmp_path, monkeypatch, perfect=False)
    gates = {row["gate"]: row["passed"] for row in summary["gates"]}
    assert gates["absolute_reader_competence"] is False
    assert summary["all_compatibility_gates_passed"] is False
