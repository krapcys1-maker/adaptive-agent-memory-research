"""The arms must be comparable, distinct, and unable to see the future.

An arm comparison is only a comparison if the arms differ in *what they keep*
and in nothing else. Three things would silently void it, and each has a test:

**Unequal budgets.** An arm handed more context answers more and has
demonstrated nothing. The budget is the control, so it is asserted rather than
assumed.

**Arms that are secretly the same policy.** ``recency`` and ``frequency``
reported identical numbers on the stub — 0.000 gold retrieved, 0.143 leaked, to
the digit. That is exactly the pattern that should be checked rather than
explained away. They turned out to select different events (0 of 84 selections
identical) and to fail for the same reason, which is a result. Had they been
identical, one arm would have been decoration.

**Future leakage.** An arm that keeps an event recorded after the probe was
asked is answering with information nobody had. This is the failure the whole
bitemporal apparatus exists to prevent, and it is one ``<=`` away at all times.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.arms import ARM_NOTES, ARMS, DEFAULT_TOKEN_BUDGET, _fill  # noqa: E402
from corpus.history_family_spec import _lcg  # noqa: E402

CORPUS = ROOT / "data" / "lab" / "corpus-h1"


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture(scope="module")
def corpus() -> dict:
    if not (CORPUS / "prefix-v0" / "history.jsonl").is_file():
        pytest.skip("corpus not generated")
    return {
        "events": load(CORPUS / "prefix-v0" / "history.jsonl"),
        "queries": load(CORPUS / "reveal-v0" / "queries.jsonl"),
    }


def _select(name: str, corpus: dict, query: dict, budget: int = DEFAULT_TOKEN_BUDGET) -> list[dict]:
    return ARMS[name](corpus["events"], query["question"], query["asked_on_day"],
                      budget, _lcg(1234))


# --------------------------------------------------------------- the budget is the control


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_no_arm_exceeds_the_shared_budget(arm: str, corpus: dict) -> None:
    for query in corpus["queries"]:
        kept = _select(arm, corpus, query)
        spent = sum(len(event["text"].split()) for event in kept)
        assert spent <= DEFAULT_TOKEN_BUDGET, f"{arm} spent {spent} on {query['query_id']}"


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_every_arm_actually_uses_most_of_the_budget(arm: str, corpus: dict) -> None:
    """An arm that leaves the budget unspent is handicapped, not thrifty.

    Without this, an arm could look worse purely because its ordering wasted the
    allowance, and the comparison would measure packing rather than retention.
    """
    used = []
    for query in corpus["queries"]:
        used.append(sum(len(e["text"].split()) for e in _select(arm, corpus, query)))
    mean = sum(used) / len(used)
    assert mean > DEFAULT_TOKEN_BUDGET * 0.85, f"{arm} used only {mean:.0f} of {DEFAULT_TOKEN_BUDGET}"


def test_a_long_event_is_skipped_rather_than_ending_the_fill() -> None:
    """Otherwise an arm is punished for ranking one long event highly."""
    events = [
        {"text": "x " * 300, "day": 1, "position": 0, "event_id": "long"},
        {"text": "short one", "day": 1, "position": 1, "event_id": "short"},
    ]
    kept = _fill(events, 50)
    assert [event["event_id"] for event in kept] == ["short"]


# --------------------------------------------------------------- no arm sees the future


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_no_arm_keeps_an_event_recorded_after_the_probe(arm: str, corpus: dict) -> None:
    for query in corpus["queries"]:
        for event in _select(arm, corpus, query):
            assert event["day"] <= query["asked_on_day"], (
                f"{arm} kept an event from day {event['day']} for a probe asked on "
                f"day {query['asked_on_day']}"
            )


# --------------------------------------------------------------- the arms are distinct


def test_recency_and_frequency_are_not_the_same_policy(corpus: dict) -> None:
    """They reported identical stub numbers, so this is checked, not assumed."""
    identical = 0
    for query in corpus["queries"]:
        recent = {e["event_id"] for e in _select("recency", corpus, query)}
        frequent = {e["event_id"] for e in _select("frequency", corpus, query)}
        identical += recent == frequent
    assert identical == 0, f"{identical} of {len(corpus['queries'])} selections were identical"


def test_recency_keeps_material_far_newer_than_the_floor_does(corpus: dict) -> None:
    """The claim is a bias toward recent events, not an exclusive window.

    A first version of this test asserted that every kept event came from the
    two newest days, and it failed: recency reached back to day 18 to spend the
    last of its budget on a short event. That is the implementation being right
    and the test being wrong. ``_fill`` skips an event that would overshoot and
    keeps going, deliberately, so an arm is not punished for ranking one long
    event highly — and a compactor that left budget unspent would be handicapped
    rather than thrifty, which the budget-usage test above forbids.

    So the property that actually holds is comparative: recency's material is
    much newer than the seeded floor's. That is what the arm claims and all it
    claims.
    """
    gaps_recency, gaps_random = [], []
    for query in corpus["queries"]:
        for name, bucket in (("recency", gaps_recency), ("random", gaps_random)):
            kept = _select(name, corpus, query)
            bucket.append(sum(e["day"] for e in kept) / len(kept))

    mean_recency = sum(gaps_recency) / len(gaps_recency)
    mean_random = sum(gaps_random) / len(gaps_random)
    assert mean_recency > mean_random + 5, (
        f"recency's mean kept day is {mean_recency:.1f} against the floor's "
        f"{mean_random:.1f}; it is not behaving as a recency policy"
    )


def test_the_random_arm_is_seeded_and_reproducible(corpus: dict) -> None:
    """An unseeded floor is a different floor every run and cannot be compared."""
    query = corpus["queries"][0]
    first = [e["event_id"] for e in _select("random", corpus, query)]
    second = [e["event_id"] for e in _select("random", corpus, query)]
    assert first == second


def test_every_arm_has_a_note_explaining_what_it_models(corpus: dict) -> None:
    for arm in {*ARMS, "fts5"}:
        assert ARM_NOTES.get(arm), f"{arm} has no note"


# --------------------------------------------------------------- the table refuses bad input


def test_the_comparison_refuses_arms_run_under_different_budgets() -> None:
    """A table mixing a 250-token arm with a 500-token one looks like a finding.

    It is worth refusing rather than warning: by the time a table is being read,
    nobody re-checks the conditions each row was produced under.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import compare_corpus_h1_arms as compare

    runs = [
        {"arm": "a", "token_budget": 250, "reader": "m", "probes": 84},
        {"arm": "b", "token_budget": 500, "reader": "m", "probes": 84},
    ]
    with pytest.raises(SystemExit, match="token budget"):
        compare.guard(runs)


def test_the_comparison_refuses_arms_read_by_different_models() -> None:
    import compare_corpus_h1_arms as compare

    runs = [
        {"arm": "a", "token_budget": 250, "reader": "one", "probes": 84},
        {"arm": "b", "token_budget": 250, "reader": "two", "probes": 84},
    ]
    with pytest.raises(SystemExit, match="reader"):
        compare.guard(runs)


def test_the_comparison_accepts_arms_that_do_share_conditions() -> None:
    import compare_corpus_h1_arms as compare

    runs = [
        {"arm": "a", "token_budget": 250, "reader": "m", "probes": 84},
        {"arm": "b", "token_budget": 250, "reader": "m", "probes": 84},
    ]
    compare.guard(runs)
