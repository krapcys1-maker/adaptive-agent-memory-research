from scripts.run_diverse_cue_retrieval import expand_bilingual, filter_candidates, valid_on


def record(evidence_id, valid_from, valid_to=None, trust="reviewed"):
    return {
        "evidence_id": evidence_id,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "trust": trust,
    }


def test_bilingual_expansion_is_fixed_and_bidirectional():
    assert "emergency" in expand_bilingual("awaryjny pakiet")
    assert "package" in expand_bilingual("awaryjny pakiet")
    assert "kopii zapasowej" in expand_bilingual("backup encryption key")
    assert "klucz" in expand_bilingual("backup encryption key")


def test_validity_interval_is_inclusive():
    item = record("A", "2026-01-01", "2026-02-28")
    assert valid_on(item, "2026-01-01T00:00:00Z")
    assert valid_on(item, "2026-02-28T23:59:00Z")
    assert not valid_on(item, "2026-03-01T00:00:00Z")


def test_filters_preserve_rank_and_remove_future_stale_or_untrusted():
    records = {
        "CURRENT": record("CURRENT", "2026-02-01"),
        "FUTURE": record("FUTURE", "2026-04-01"),
        "STALE": record("STALE", "2025-01-01", "2026-01-31"),
        "POISON": record("POISON", "2026-01-01", trust="untrusted"),
    }
    assert filter_candidates(
        ["FUTURE", "CURRENT", "POISON", "STALE"],
        records,
        "2026-02-15T00:00:00Z",
        use_time=True,
        use_trust=True,
    ) == ["CURRENT"]
