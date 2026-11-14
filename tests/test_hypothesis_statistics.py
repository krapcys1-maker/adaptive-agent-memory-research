"""Tests of the pure hypothesis-ledger statistics (scripts/hypothesis_statistics.py, hypothesis_conditions.py,
hypothesis_textsim.py).

The first four tests are the simulation checks of the coordinator's ledger (coordinator commit 799c356, decision D8),
translated into English and run against the extracted functions; seeds are fixed. The tests that exercised the whole
ledger (gate G1 to results to gate G2) need the coordinator's database and stay there; their reported outcome is in the
methodology document. The remaining tests are new: hand-computed Holm cases, the minimum-sample rule, the closed
condition language, canonical hashing and the text-similarity module.
"""
import itertools
import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from hypothesis_conditions import ConditionError, evaluate, metrics_of  # noqa: E402
from hypothesis_statistics import canonical, fingerprint, holm, mcnemar_one_sided, min_discordant  # noqa: E402
from hypothesis_textsim import cosine, features, most_similar, tokens  # noqa: E402

ALPHA = 0.05


def closed_testing_bonferroni(p: dict, alpha: float) -> set:
    """H_i is rejected when every intersection containing i is rejected by local Bonferroni (min p <= a/|S|)."""
    keys = list(p)
    pv = {k: (1.0 if p[k] is None else p[k]) for k in keys}
    rejected = set()
    for i in keys:
        others = [k for k in keys if k != i]
        if all(min(pv[k] for k in (i, *s)) <= alpha / (len(s) + 1)
               for r in range(len(others) + 1) for s in itertools.combinations(others, r)):
            rejected.add(i)
    return rejected


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


# --------------------------------------------------------------------- simulation checks (coordinator D8)
def test_holm_equals_closed_testing_reference():
    rng = random.Random(20261113)
    for _ in range(3000):
        m = rng.randint(1, 6)
        p = {}
        for j in range(m):
            u = rng.random()
            p[f"t{j}"] = None if u < 0.15 else round(rng.choice([rng.random() * 0.06, rng.random()]), rng.choice([2, 6]))
        got = {k for k, v in holm(p, ALPHA).items() if v["reject"]}
        assert got == closed_testing_bonferroni(p, ALPHA), p


@pytest.mark.parametrize("rho", [0.0, 0.7, -0.2])
def test_holm_fwer_under_global_null(rho):
    """A family of 5 tests, all H0 true: P(at least one rejection) <= alpha (+ Monte Carlo error)."""
    rng = random.Random(7 + int(rho * 10))
    m, n_sim, hits = 5, 20000, 0
    for _ in range(n_sim):
        g = rng.gauss(0, 1)
        zs = [math.sqrt(abs(rho)) * (g if rho >= 0 or j % 2 == 0 else -g) + math.sqrt(1 - abs(rho)) * rng.gauss(0, 1)
              for j in range(m)]
        p = {f"t{j}": 1 - phi(z) for j, z in enumerate(zs)}
        hits += any(v["reject"] for v in holm(p, ALPHA).values())
    fwer = hits / n_sim
    se = math.sqrt(ALPHA * (1 - ALPHA) / n_sim)
    assert fwer <= ALPHA + 3 * se, fwer


def test_holm_fwer_with_unexecuted_tests_and_partial_nulls():
    """Some tests not run (p = 1), some with a true effect: rejections of true nulls stay <= alpha."""
    rng = random.Random(11)
    n_sim, false_rej = 20000, 0
    for _ in range(n_sim):
        p = {"null1": rng.random(), "null2": rng.random(), "null3": None, "alt1": 1 - phi(rng.gauss(3, 1)),
             "alt2": None}
        r = holm(p, ALPHA)
        false_rej += r["null1"]["reject"] or r["null2"]["reject"]
    assert false_rej / n_sim <= ALPHA + 3 * math.sqrt(ALPHA * (1 - ALPHA) / n_sim)


def test_discrete_mcnemar_null_is_conservative():
    """Exact McNemar with no effect: P(p <= alpha) <= alpha for every number of discordant pairs."""
    rng = random.Random(5)
    for n_disc in (5, 8, 12, 20, 33):
        hits = sum(mcnemar_one_sided(g, n_disc - g) <= ALPHA
                   for g in (sum(rng.random() < 0.5 for _ in range(n_disc)) for _ in range(20000)))
        assert hits / 20000 <= ALPHA + 0.005, (n_disc, hits)


# ------------------------------------------------------------------------------------------ new tests
def test_holm_hand_computed_case():
    r = holm({"a": 0.01, "b": 0.02, "c": 0.04}, 0.05)
    assert [r[k]["rank"] for k in "abc"] == [1, 2, 3]
    assert r["a"]["threshold"] == pytest.approx(0.05 / 3)
    assert r["b"]["threshold"] == pytest.approx(0.05 / 2)
    assert r["c"]["threshold"] == pytest.approx(0.05)
    assert all(r[k]["reject"] for k in "abc")
    assert r["a"]["p_holm"] == pytest.approx(0.03)      # 3 * 0.01
    assert r["b"]["p_holm"] == pytest.approx(0.04)      # max(0.03, 2 * 0.02)
    assert r["c"]["p_holm"] == pytest.approx(0.04)      # max(0.04, 1 * 0.04)


def test_holm_stops_at_the_first_failure_even_if_a_later_p_would_pass():
    r = holm({"a": 0.04, "b": 0.045, "c": 0.0001}, 0.05)
    assert r["c"]["reject"] is True and r["a"]["reject"] is False and r["b"]["reject"] is False


def test_holm_unexecuted_test_counts_as_one_and_makes_the_correction_stricter():
    with_missing = holm({"a": 0.02, "b": None}, 0.05)
    assert with_missing["b"]["p"] == 1.0 and with_missing["b"]["executed"] is False
    assert with_missing["a"]["reject"] is True and with_missing["a"]["threshold"] == pytest.approx(0.025)
    assert holm({"a": 0.02, "b": None, "c": None}, 0.05)["a"]["reject"] is False   # threshold 0.05 / 3 < 0.02


def test_holm_ties_are_broken_by_identifier():
    r = holm({"b": 0.01, "a": 0.01}, 0.05)
    assert r["a"]["rank"] == 1 and r["b"]["rank"] == 2


def test_min_discordant_matches_the_smallest_attainable_p():
    assert min_discordant(0.05) == 5            # 0.5 ** 4 = 0.0625 > 0.05 >= 0.5 ** 5
    assert min_discordant(0.5) == 1
    assert min_discordant(0.05 / 3) == 6        # Bonferroni-sized alpha for a family of three
    for alpha in (0.1, 0.05, 0.01):
        k = min_discordant(alpha)
        assert mcnemar_one_sided(k, 0) <= alpha < mcnemar_one_sided(k - 1, 0)
    for bad in (0, -0.1, 1, 1.5):
        with pytest.raises(ValueError):
            min_discordant(bad)


def test_mcnemar_values():
    assert mcnemar_one_sided(0, 0) == 1.0
    assert mcnemar_one_sided(5, 3) == pytest.approx(93 / 256)   # the figure of the decision-rule audit (8 discordant pairs)
    assert mcnemar_one_sided(5, 0) == pytest.approx(1 / 32)


def test_canonical_is_order_independent_and_fingerprint_ignores_case_and_spacing():
    assert canonical({"b": 1, "a": [1, 2]}) == canonical({"a": [1, 2], "b": 1}) == '{"a":[1,2],"b":1}'
    a = {"mechanism": "Error  notes", "variable": "v", "corpus": "C", "direction": "Increase", "metric": "solved"}
    b = {"mechanism": " error notes ", "variable": "V", "corpus": "c", "direction": "increase", "metric": "SOLVED"}
    assert fingerprint(a) == fingerprint(b)
    assert fingerprint(a) != fingerprint({**a, "direction": "decrease"})
    assert len(fingerprint(a)) == 64


def test_conditions_three_valued_logic():
    cond = {"all": [{"metric": "T.solved", "op": ">=", "value": {"metric": "C.solved", "plus": 3}},
                    {"not": {"metric": "T.errors", "op": ">", "value": 10}}]}
    assert metrics_of(cond) == {"T.solved", "C.solved", "T.errors"}
    assert evaluate(cond, {"T.solved": 40, "C.solved": 30, "T.errors": 4}) is True
    assert evaluate(cond, {"T.solved": 32, "C.solved": 30, "T.errors": 4}) is False
    assert evaluate(cond, {"T.solved": 40, "C.solved": 30}) is None                      # a missing metric: unknown
    assert evaluate({"any": [{"metric": "x", "op": ">", "value": 1}, {"metric": "y", "op": ">", "value": 1}]},
                    {"x": 5}) is True                                                    # one true branch decides
    assert evaluate({"lhs": {"abs": {"sub": [{"metric": "T"}, {"metric": "C"}]}}, "op": "<=", "rhs": 2},
                    {"T": 31, "C": 30}) is True


@pytest.mark.parametrize("bad", [
    {}, [], {"all": []}, {"all": [{"metric": "m", "op": "<", "value": 1}], "any": []},
    {"metric": "m", "op": "~", "value": 1}, {"metric": "m", "op": "<"}, {"lhs": 1, "op": "<", "rhs": {"pow": [1, 2]}},
    {"metric": "", "op": "<", "value": 1}, {"metric": "m", "op": "<", "value": True},
])
def test_conditions_reject_anything_outside_the_closed_language(bad):
    with pytest.raises(ConditionError):
        metrics_of(bad)


def test_conditions_depth_is_bounded():
    cond = {"metric": "m", "op": ">", "value": 0}
    for _ in range(20):
        cond = {"not": cond}
    with pytest.raises(ConditionError):
        metrics_of(cond)


def test_textsim_detects_a_close_paraphrase_and_ignores_unrelated_claims():
    existing = {
        "H1": "Showing success traces before acting raises the number of solved tasks",
        "H2": "Placeholder masking of copied values lowers the repeated error rate",
        "H3": "A cheaper reader model reduces the cost per answer",
    }
    ranked = most_similar("Success traces shown before acting raise the number of solved tasks", existing)
    assert ranked[0][0] == "H1" and ranked[0][1] > 0.45 > ranked[1][1]
    assert most_similar("anything", {}) == []
    assert cosine({}, {"a": 1.0}) == 0.0


def test_textsim_blind_spot_is_real_a_synonym_paraphrase_is_not_detected():
    """The documented blind spot: no shared words, no similarity. The structural fingerprint has to catch such cases."""
    a = "Success traces raise solved tasks"
    b = "Winning transcripts improve completed problems"
    assert most_similar(a, {"b": b})[0][1] == 0.0


def test_textsim_tokens_fold_accents_and_drop_stop_words():
    assert tokens("Łódź i ŻÓŁW the cat") == ["lodz", "zolw", "cat"]
    assert features("alpha beta gamma", reach=1)["alpha|beta"] == 1
    assert "alpha|gamma" not in features("alpha beta gamma", reach=1)
