from scripts.build_collection_closure_corpus import make_corpus
from scripts.build_collection_closure_corpus_v1 import PARENT_CORPUS_SHA256, make_corpus_v1, write_corpus


def by_id(rows, id_key):
    return {row[id_key]: row for row in rows}


def test_v1_preserves_case_and_artifact_counts():
    bundle = make_corpus_v1()
    assert {key: len(rows) for key, rows in bundle.items()} == {
        "cases": 48,
        "inventories": 48,
        "probes": 48,
        "certificates": 48,
        "insertions": 48,
    }


def test_only_counterexample_certificate_status_changes_from_v0():
    v0 = make_corpus()
    v1 = make_corpus_v1()
    for artifact in ("inventories", "probes", "insertions"):
        assert v1[artifact] == v0[artifact]

    c0 = by_id(v0["certificates"], "certificate_id")
    c1 = by_id(v1["certificates"], "certificate_id")
    changed = []
    for certificate_id in c0:
        if c0[certificate_id] != c1[certificate_id]:
            changed.append(certificate_id)
            before = dict(c0[certificate_id])
            after = dict(c1[certificate_id])
            assert before.pop("status") == "partial"
            assert after.pop("status") == "complete"
            assert before == after
    assert len(changed) == 2


def test_v1_case_change_is_only_adversarial_flag():
    v0 = by_id(make_corpus()["cases"], "case_id")
    v1 = by_id(make_corpus_v1()["cases"], "case_id")
    for case_id in v0:
        after = v1[case_id]
        before = v0[case_id]
        flag = after["gold"]["adversarial_certificate_claim"]
        stripped = {**after, "gold": {k: v for k, v in after["gold"].items() if k != "adversarial_certificate_claim"}}
        assert stripped == before
        assert flag == (before["gold"]["stratum"] == "admissible-insertion-changes-negative-answer")


def test_counterexample_claim_is_complete_but_unsound():
    bundle = make_corpus_v1()
    certs = by_id(bundle["certificates"], "certificate_id")
    inserts = by_id(bundle["insertions"], "insertion_set_id")
    targets = [row for row in bundle["cases"] if row["gold"]["adversarial_certificate_claim"]]
    assert len(targets) == 2
    for case in targets:
        assert certs[case["observed"]["certificate_id"]]["status"] == "complete"
        assert any(update["admissible"] and update["changes_query_answer"] for update in inserts[case["observed"]["insertion_set_id"]]["allowed_insertions"])
        assert case["gold"]["expected_negative_tier"] == "N1_NOT_FOUND_IN_SEARCHED_SCOPE"


def test_manifest_records_parent_and_repair(tmp_path):
    manifest = write_corpus(tmp_path)
    assert manifest["parent_corpus_sha256"] == PARENT_CORPUS_SHA256
    assert manifest["adversarial_certificate_claims"] == 2
    assert manifest["case_count"] == 48
