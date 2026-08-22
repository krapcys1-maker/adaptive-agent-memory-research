import json

from scripts.build_collection_closure_corpus import content_hash, make_corpus, write_corpus


def test_corpus_has_48_opaque_balanced_cases():
    bundle = make_corpus()
    cases = bundle["cases"]
    assert len(cases) == 48
    assert sum(row["language"] == "en" for row in cases) == 24
    assert sum(row["language"] == "pl" for row in cases) == 24
    assert len({row["case_id"] for row in cases}) == 48
    assert all(row["case_id"].startswith("CLOS-") for row in cases)
    assert not any(row["gold"]["stratum"].upper() in row["case_id"] for row in cases)


def test_artifact_links_are_total_and_unique():
    bundle = make_corpus()
    for artifact_name, observed_key in (
        ("inventories", "inventory_id"),
        ("probes", "probe_set_id"),
        ("certificates", "certificate_id"),
        ("insertions", "insertion_set_id"),
    ):
        ids = {row[observed_key] for row in bundle[artifact_name]}
        assert len(ids) == 48
        assert {case["observed"][observed_key] for case in bundle["cases"]} == ids


def test_expired_and_mutated_certificates_are_not_current():
    cases = {row["gold"]["stratum"]: row for row in make_corpus()["cases"] if row["language"] == "en"}
    assert not cases["expired-exact-certificate"]["gold"]["certificate_current"]
    assert not cases["scope-mutated-after-certificate"]["gold"]["certificate_current"]
    assert cases["globally-incomplete-query-complete-entity-slice"]["gold"]["certificate_current"]


def test_retrieval_miss_never_implies_n3_without_explicit_negative_record():
    bundle = make_corpus()
    inventories = {row["inventory_id"]: row for row in bundle["inventories"]}
    n3 = [row for row in bundle["cases"] if row["gold"]["expected_negative_tier"] == "N3_PROPOSITION_FALSE"]
    assert len(n3) == 2
    for case in n3:
        records = inventories[case["observed"]["inventory_id"]]["records"]
        assert any(record["polarity"] == "negative" and record["current"] and record["authorized"] for record in records)


def test_n2_requires_applicable_current_certificate_and_available_domains():
    for case in make_corpus()["cases"]:
        if case["gold"]["expected_negative_tier"] == "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE":
            assert case["gold"]["certificate_applicable"]
            assert case["gold"]["certificate_current"]
            assert case["gold"]["all_required_domains_available"]
            assert not case["gold"]["admissible_insertion_changes_answer"]


def test_query_scope_mismatch_is_explicit():
    rows = [row for row in make_corpus()["cases"] if row["gold"]["stratum"] == "query-mapped-to-wrong-certificate-scope"]
    assert len(rows) == 2
    assert all(row["observed"]["mapped_query_shape"] != row["gold"]["query_shape"] for row in rows)
    assert all(row["gold"]["expected_action"] == "REMAP_SCOPE" for row in rows)


def test_pairs_must_not_cross_random_split():
    cases = make_corpus()["cases"]
    groups = {}
    for row in cases:
        groups.setdefault(row["pair_group"], set()).add(row["language"])
    assert len(groups) == 24
    assert all(languages == {"en", "pl"} for languages in groups.values())


def test_manifest_hashes_reproduce(tmp_path):
    manifest = write_corpus(tmp_path)
    bundle = make_corpus()
    assert manifest["corpus_sha256"] == content_hash(bundle)
    assert manifest["case_count"] == 48
    for key, rows in bundle.items():
        assert manifest["artifact_sha256"][key] == content_hash(rows)
        loaded = [json.loads(line) for line in (tmp_path / f"{key}.jsonl").read_text(encoding="utf-8").splitlines()]
        assert loaded == rows
