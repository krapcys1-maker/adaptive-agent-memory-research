"""The preregistration must stay byte-identical to what was registered.

A preregistration that can be edited after results exist is a postregistration
wearing its clothes. This is the mechanical check: the declared digest must
match the file, and the file must still contain every gate and definition it was
frozen with.

The specific loopholes it closes, each of which was open until it was pointed
out, are worth naming because they are the ones that reappear:

**A metric listed but not gated.** Fragmentation was reported and had no
threshold. Three addresses for one entity gives collision 0%, wrong-entity 0%,
and a memory whose version history has split into three chains.

**An unfrozen denominator.** ``catastrophic wrong entity < 1%`` means two very
different things over all probes and over non-abstained probes. The second lets
a system improve the metric by refusing to answer.

**An overall gate with no per-family floor.** Overall coverage of 0.96 with
OBSOLETE at 0.72 passes every global threshold while failing the family
addressing was introduced for.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "data" / "lab" / "corpus-h1" / "preregistration-addr-e2"


@pytest.fixture(scope="module")
def registered() -> dict:
    path = PREREG / "preregistration.json"
    if not path.is_file():
        pytest.skip("preregistration not present")
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_declared_digest_matches_the_file() -> None:
    body = (PREREG / "preregistration.json").read_bytes()
    declared = (PREREG / "preregistration.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(body).hexdigest() == declared, (
        "the preregistration was modified after it was frozen"
    )


def test_every_reported_metric_has_a_definition(registered: dict) -> None:
    """A metric without a written denominator can mean whatever the result needs."""
    gated = set(registered["overall_gates"])
    defined = set(registered["metric_definitions"])
    assert gated <= defined, f"gated without a definition: {sorted(gated - defined)}"


def test_fragmentation_is_gated_and_not_merely_reported(registered: dict) -> None:
    assert "fragmentation_rate" in registered["overall_gates"]
    assert "fragmentation_rate" in registered["metric_definitions"]


def test_no_rate_divides_by_the_non_abstained_subset(registered: dict) -> None:
    """Abstention must never flatter a rate."""
    definitions = registered["metric_definitions"]
    assert "NOT over non-abstained" in definitions["catastrophic_wrong_entity_rate"]
    assert "never a denominator" in definitions["abstention_rate"]
    for name, text in definitions.items():
        if name in {"eligible_probes", "abstention_rate"}:
            continue
        assert "non-abstained" not in text or "NOT over" in text, name


def test_there_is_a_per_family_floor_for_the_family_this_targets(registered: dict) -> None:
    family = registered["per_family_gate"]
    assert "OBSOLETE_stale_context_rate" in family
    assert "OBSOLETE_gold_coverage" in family
    assert len(family["report_required_for"]) == 7


def test_the_tautological_bound_is_labelled_as_such(registered: dict) -> None:
    """The oracle's 1.000 must never become the target it is not."""
    assert "TAUTOLOGICAL" in registered["bounds_from_ADDR_E1"]["note"]


def test_the_corpus_it_was_registered_against_is_unchanged(registered: dict) -> None:
    corpus = ROOT / "data" / "lab" / "corpus-h1"
    for field, name in (("history_sha256", "prefix-v0/history.jsonl"),
                        ("gold_sha256", "reveal-v0/gold.jsonl"),
                        ("queries_sha256", "reveal-v0/queries.jsonl")):
        actual = hashlib.sha256((corpus / name).read_bytes()).hexdigest()
        assert registered["corpus"][field] == actual, (
            f"{name} changed since registration; the thresholds were chosen against different data"
        )


def test_no_extractor_existed_when_this_was_frozen() -> None:
    """The claim that implementation followed registration has to be checkable."""
    candidates = list((ROOT / "scripts").glob("*address_extract*")) + \
                 list((ROOT / "scripts" / "corpus").glob("*extract*"))
    if candidates:
        pytest.skip("an extractor now exists; registration precedence is a git-history question")
