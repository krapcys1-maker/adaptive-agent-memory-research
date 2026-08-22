import json

from scripts.build_metamemory_dev_corpus import content_hash, make_cases, write_corpus


def test_corpus_is_deterministic_and_balanced_across_core_counterexamples(tmp_path):
    first = make_cases()
    second = make_cases()

    assert first == second
    assert len(first) == 26
    assert len({case["case_id"] for case in first}) == len(first)
    assert {case["language"] for case in first} == {"en", "pl"}
    assert sum(case["critical"] for case in first) == 12
    assert {case["stratum"] for case in first} == {
        "healthy-initial",
        "alternate-cue-only",
        "direct-id-only",
        "familiar-poison",
        "stale-version",
        "consistent-unsupported",
        "disagreement-with-evidence",
        "not-stored",
        "query-ambiguous",
        "conflicting-current",
    }

    manifest = write_corpus(tmp_path)
    written = [json.loads(line) for line in (tmp_path / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert written == first
    assert manifest["case_sha256"] == content_hash(first)


def test_every_recoverable_noninitial_case_has_a_non_storage_recovery_operation():
    for case in make_cases():
        truth = case["truth"]
        if truth["answerable"] and case["initial"]["candidate"] is None:
            recovery_operations = set(case["operations"]) - {"STORAGE_PROBE"}
            assert recovery_operations
            assert any(
                case["operations"][name].get("candidate", {}).get("value")
                == truth["expected_value"]
                for name in recovery_operations
            )
