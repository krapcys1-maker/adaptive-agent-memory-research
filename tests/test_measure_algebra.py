"""Aggregation properties, because aggregation is where this kept breaking.

Three separate defects in this session came from combining measurements: a
boolean that could never be False, a rule pair that rejected a legitimate
partial sum, and a fix that dropped the very flag it existed to add. All three
were in the same operation.

So the operation gets property tests rather than examples.

The three states, and the one transition that matters
------------------------------------------------------
    EXACT         value = 12,   lower_bound = False
    LOWER BOUND   value = 12,   lower_bound = True
    UNKNOWN       value = None, lower_bound = False

    UNKNOWN + EXACT(12)  →  LOWER_BOUND(12)      never EXACT(12)

That last line is the whole correction. Observability is a separate axis, so
``value=12, lower_bound=True, observability=unobservable`` is coherent and
useful: *we established at least twelve; the system will not show the rest.*

Why associativity is not pedantry
----------------------------------
The arena sums ``ingest + query_1 + … + query_N``. If the result depended on
grouping, two runs over identical data would produce different cost tables, and
the difference would look like a property of the system rather than of the
summation order.
"""

from __future__ import annotations

import sys
from itertools import permutations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import Cost, Measure  # noqa: E402

EXACT = Measure(12, "native")
EXACT_OTHER = Measure(30, "native")
FLOOR = Measure(12, "unobservable", lower_bound=True)
UNKNOWN = Measure(None, "unobservable")
ZERO = Measure(0, "native")


def state(m: Measure) -> str:
    if m.value is None:
        return "unknown"
    return "lower_bound" if m.lower_bound else "exact"


# --------------------------------------------------------------- the state table


@pytest.mark.parametrize("a,b,expected", [
    (EXACT, EXACT_OTHER, "exact"),
    (EXACT, UNKNOWN, "lower_bound"),
    (UNKNOWN, EXACT, "lower_bound"),
    (FLOOR, EXACT, "lower_bound"),
    (EXACT, FLOOR, "lower_bound"),
    (FLOOR, UNKNOWN, "lower_bound"),
    (UNKNOWN, UNKNOWN, "unknown"),
    (FLOOR, FLOOR, "lower_bound"),
])
def test_the_state_transition_table(a: Measure, b: Measure, expected: str) -> None:
    assert state(a + b) == expected


def test_unknown_plus_exact_is_never_exact() -> None:
    """The single correction this whole model exists for."""
    total = UNKNOWN + EXACT
    assert total.value == 12
    assert total.lower_bound is True
    assert total.known is False


# --------------------------------------------------------------- forbidden transitions


def test_none_never_becomes_a_real_zero() -> None:
    """Unknown cost read as free would make the blindest system look cheapest."""
    assert (UNKNOWN + UNKNOWN).value is None
    assert (UNKNOWN + Measure(None, "instrumented")).value is None


def test_a_floor_never_becomes_exact() -> None:
    for other in (EXACT, ZERO, FLOOR, UNKNOWN):
        assert (FLOOR + other).lower_bound is True, other


def test_a_measured_number_is_never_discarded() -> None:
    """Keeping the known part is why a partial sum is representable at all."""
    assert (EXACT + UNKNOWN).value == 12
    assert (Measure(40_000) + UNKNOWN).value == 40_000


# --------------------------------------------------------------- algebra


PAIRS = [EXACT, EXACT_OTHER, FLOOR, UNKNOWN, ZERO]


@pytest.mark.parametrize("a", PAIRS)
@pytest.mark.parametrize("b", PAIRS)
def test_addition_is_commutative(a: Measure, b: Measure) -> None:
    left, right = a + b, b + a
    assert (left.value, left.lower_bound, left.observability) == \
           (right.value, right.lower_bound, right.observability)


@pytest.mark.parametrize("a", PAIRS)
@pytest.mark.parametrize("b", PAIRS)
@pytest.mark.parametrize("c", PAIRS)
def test_addition_is_associative(a: Measure, b: Measure, c: Measure) -> None:
    left, right = (a + b) + c, a + (b + c)
    assert (left.value, left.lower_bound, left.observability) == \
           (right.value, right.lower_bound, right.observability)


@pytest.mark.parametrize("a", PAIRS)
def test_zero_is_an_identity(a: Measure) -> None:
    """Adding a known zero must tell you nothing new.

    A floor of zero carries no information, so unknown plus zero stays unknown
    rather than degenerating into lower_bound(0) — otherwise identity fails and
    the aggregate depends on how many zero-cost operations happened to be summed.
    """
    total = a + ZERO
    assert (total.value, total.lower_bound) == (a.value, a.lower_bound)


@pytest.mark.parametrize("order", list(permutations([EXACT, FLOOR, UNKNOWN, ZERO])))
def test_a_run_total_does_not_depend_on_summation_order(order) -> None:
    """ingest + query_1 + … + query_N must not vary with grouping.

    EXACT(12) and FLOOR(12) sum to 24; the unknown makes it a floor and the zero
    contributes nothing. Every ordering must reach the same pair.
    """
    total = order[0]
    for measure in order[1:]:
        total = total + measure
    assert (total.value, total.lower_bound) == (24, True)


def test_adding_a_known_zero_to_an_unknown_leaves_it_unknown() -> None:
    """A floor of zero is not information, and treating it as one breaks identity.

    Found by the identity property rather than by an example: UNKNOWN + ZERO
    returned LOWER_BOUND(0), so a total would have depended on how many
    zero-cost operations were summed.
    """
    assert (UNKNOWN + ZERO).value is None
    assert (UNKNOWN + ZERO).lower_bound is False


# --------------------------------------------------------------- observability is a separate axis


def test_observability_takes_the_weakest_component() -> None:
    assert (Measure(1, "native") + Measure(1, "instrumented")).observability == "instrumented"
    assert (Measure(1, "instrumented") + Measure(1, "unobservable")).observability == "unobservable"
    assert (Measure(1, "native") + Measure(1, "native")).observability == "native"


def test_a_floor_with_unobservable_provenance_is_coherent() -> None:
    """We established at least twelve; the system will not show the rest."""
    total = Measure(12, "native") + Measure(None, "unobservable")
    assert (total.value, total.lower_bound, total.observability) == (12, True, "unobservable")


# --------------------------------------------------------------- and the same at Cost level


def test_cost_addition_inherits_the_properties() -> None:
    exact = Cost(Measure(12), Measure(40_000), Measure(500), Measure(1_800_000))
    blind = Cost(UNKNOWN, UNKNOWN, UNKNOWN, Measure(400_000, "instrumented"))

    assert (exact + exact).fully_known is True
    assert (exact + blind).fully_known is False
    assert (exact + blind).is_lower_bound is True
    assert (blind + blind).fully_known is False


def test_durations_are_integers_so_addition_is_exactly_associative() -> None:
    """Rounding each float sum was tried first and is not a guarantee.

    A targeted search near the half-microsecond boundary found 17,338
    associativity violations in 54,872 triples, while 400,000 random triples
    found none — random values almost never land on the boundary, so the
    property test passed while the property did not hold. Integers are exact by
    construction.
    """
    a, b, c = Measure(123457), Measure(250000), Measure(1)
    assert ((a + b) + c).value == (a + (b + c)).value == 373458


def test_a_cost_reports_seconds_from_integer_microseconds() -> None:
    """Presentation converts; storage never does."""
    cost = Cost(wall_microseconds=Measure(1_500_000))
    assert cost.wall_microseconds.value == 1_500_000
    assert cost.wall_seconds == 1.5


def test_an_unknown_duration_presents_as_none_not_zero_seconds() -> None:
    assert Cost(wall_microseconds=Measure(None, "unobservable")).wall_seconds is None


def test_cost_addition_is_order_independent() -> None:
    a = Cost(Measure(1), Measure(10), Measure(2), Measure(100_000))
    b = Cost(UNKNOWN, Measure(5), UNKNOWN, Measure(200_000))
    c = Cost(Measure(3), UNKNOWN, Measure(1), Measure(300_000))
    assert ((a + b) + c).summary() == (a + (b + c)).summary()
    assert ((a + b) + c).summary() == ((c + b) + a).summary()
