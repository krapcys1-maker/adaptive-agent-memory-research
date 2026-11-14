"""Imported from the AAMR coordinator (commit 74980a3). The three tests that exercise the coordinator's experiment admission
and its CLI stay in the coordinator; everything below tests the pure simulation module only.

P1: charakterystyka reguł decyzyjnych przed zamrożeniem protokołu (audyt 2026-11-13, ustalenia 1–3).

Testy odtwarzają liczby audytu na regułach historycznych (bez zmiany ich werdyktów) i sprawdzają, że bramka zamrożenia
odmawia: błędu I rodzaju, braku mocy, fałszywego zamykania kierunku, braku stanu nierozstrzygniętego, braku rozdziału
efektu dodatniego od praktycznego, niezadeklarowanej zależności, szumu z ponownego przebiegu i pseudoreplikacji.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rule_characteristics import (Design, Rule, RuleSpecError, characteristics, exact_threshold_rate,  # noqa: E402
                                  freeze_check, mcnemar_one_sided, render)

N_SIM = 1500
INDEP = {"independent_units": True, "independence_justification": "test: jednostki z osobnych źródeł"}

NIGHT2_MAIN = {"kind": "threshold", "params": {
    "support": {"min_diff": 9, "max_p": 0.01, "max_losses": 4}, "refute": {"max_diff": 4, "min_losses": 8},
    "support_label": "wsparte", "refute_label": "obalone", "else_label": "pośrednie"},
    "categories": {"wsparte": "positive", "obalone": "equivalent", "pośrednie": "inconclusive"}}
H16 = {"kind": "threshold", "params": {"support": {"min_diff": 2}, "refute": {"max_diff": -2}},
       "categories": {"supported": "positive", "refuted": "negative", "inconclusive": "inconclusive"}}
G2 = {"kind": "repeats_gate", "params": {"met_min": 0.10, "falsified_max": 0.03, "min_repeats": 2},
      "categories": {"supported": "positive", "refuted": "equivalent", "inconclusive": "inconclusive",
                     "conflicting": "inconclusive"}}


def ci_spec(n=1000, sesoi=0.06, **design):
    return {"design": {"n_units": n, "discordance": 0.30, "noise_source": "placebo", "sesoi": sesoi,
                       **(design or INDEP)}, "rule": {"kind": "ci_states"}}


# ----------------------------------------------------------------- odtworzenie ustaleń audytu (bez zmiany werdyktów)
def test_h16_rule_false_support_rate_exact():
    assert round(exact_threshold_rate(8, 2), 4) == 0.3633            # 93/256: audyt, ustalenie 2
    assert round(mcnemar_one_sided(5, 3), 4) == 0.3633               # p H16 z surowych danych


def test_night2_main_rule_characteristic_matches_audit():
    """Audyt, ustalenie 1: przy +10 zadaniach (rotacja 0,35) wsparte ≈ 1,8%, obalone ≈ 83%."""
    d = Design(n_units=88, discordance=0.35, noise_source="placebo", sesoi=10 / 88, cluster_sizes=[30, 30, 28])
    row = list(characteristics(Rule(**NIGHT2_MAIN), d, [10 / 88], n_sim=3000).values())[0]
    assert row["positive"] < 0.05 and 0.75 < row["equivalent"] < 0.90


def test_freeze_refuses_night2_main_rule():
    rep = freeze_check({"design": {"n_units": 88, "discordance": 0.35, "noise_source": "placebo", "sesoi": 10 / 88,
                                   "cluster_sizes": [30, 30, 28], "icc": 0.0}, "rule": NIGHT2_MAIN}, n_sim=N_SIM)
    assert not rep["ok"]
    assert any("fałszywe zamknięcie" in p for p in rep["problems"]) and any("moc" in p for p in rep["problems"])


def test_freeze_refuses_h16_threshold_without_significance():
    rep = freeze_check({"design": {"n_units": 88, "discordance": 8 / 88, "noise_source": "placebo",
                                   "sesoi": 4 / 88, **INDEP}, "rule": H16}, n_sim=N_SIM)
    assert not rep["ok"] and any("błąd I rodzaju" in p for p in rep["problems"])
    assert rep["table"]["+0.0000"]["positive"] > 0.2


def test_freeze_refuses_pseudoreplication_and_deterministic_flag():
    base = {"n_units": 88, "discordance": 0.35, "noise_source": "placebo", "sesoi": 0.05, "repeats": 2, **INDEP}
    rep = freeze_check({"design": {**base, "repeat_correlation": 1.0}, "rule": G2}, n_sim=N_SIM)
    assert any("pseudoreplikacja" in p for p in rep["problems"])
    det = {**G2, "params": {**G2["params"], "deterministic": True}}
    rep = freeze_check({"design": {**base, "repeat_correlation": 0.0}, "rule": det}, n_sim=N_SIM)
    assert any("deterministic" in p for p in rep["problems"])
    rep = freeze_check({"design": {**base, "repeat_correlation": None}, "rule": G2}, n_sim=N_SIM)
    assert any("repeat_correlation" in p for p in rep["problems"])


def test_threshold_refuting_on_non_significance_is_refused():
    """„Brak istotności = brak efektu”: obalenie przy p > 0,05 zamyka kierunek z prawdziwym efektem SESOI."""
    rule = {"kind": "threshold", "params": {"support": {"min_diff": 1, "max_p": 0.025},
                                            "refute": {"if_not_significant_at": 0.025}},
            "categories": {"supported": "positive", "refuted": "equivalent", "inconclusive": "inconclusive"}}
    rep = freeze_check({"design": {"n_units": 400, "discordance": 0.30, "noise_source": "placebo", "sesoi": 0.06,
                                   **INDEP}, "rule": rule}, n_sim=N_SIM)
    assert any("fałszywe zamknięcie" in p for p in rep["problems"])
    assert any("nierozstrzygniętego" in p for p in rep["problems"])


# ------------------------------------------------------------------------------------- reguła referencyjna
def test_reference_ci_rule_passes_with_enough_units():
    rep = freeze_check(ci_spec(n=1000), n_sim=N_SIM)
    assert rep["ok"], rep["problems"]
    t = rep["table"]
    assert t["+0.0000"]["positive"] + t["+0.0000"]["practical"] < 0.05           # błąd I rodzaju
    assert t["+0.0600"]["practical"] < t["+0.0600"]["positive"]                  # dodatni ≠ praktycznie istotny
    assert t["+0.1200"]["practical"] > 0.8


def test_reference_ci_rule_underpowered_at_88_units():
    rep = freeze_check(ci_spec(n=88), n_sim=N_SIM)
    assert not rep["ok"] and any("moc" in p for p in rep["problems"])
    rep = freeze_check({**ci_spec(n=88), "tier": "exploratory"}, n_sim=N_SIM)
    assert rep["ok"] and any("eksploracyjny" in w for w in rep["warnings"])


def test_dependence_ignored_inflates_type_one_error():
    clustered = {"cluster_sizes": [50] * 20, "icc": 0.2}
    rep = freeze_check(ci_spec(n=1000, **clustered), n_sim=N_SIM)                 # reguła zakłada niezależność
    assert any("błąd I rodzaju" in p for p in rep["problems"])
    spec = ci_spec(n=1000, **clustered)
    spec["rule"]["params"] = {"icc_assumed": 0.2}
    rep = freeze_check(spec, n_sim=N_SIM)
    assert not any("błąd I rodzaju" in p for p in rep["problems"])               # poprawny deff: I rodzaj w normie


def test_practical_label_must_not_fire_below_sesoi():
    rule = {"kind": "threshold", "params": {"support": {"min_diff": 1, "max_p": 0.025}},
            "categories": {"supported": "practical", "refuted": "negative", "inconclusive": "inconclusive"}}
    rep = freeze_check({"design": {"n_units": 1000, "discordance": 0.30, "noise_source": "placebo", "sesoi": 0.06,
                                   **INDEP}, "rule": rule}, n_sim=N_SIM)
    assert any("rozdziału efektu dodatniego od praktycznego" in p for p in rep["problems"])


# ----------------------------------------------------------------------------------------- deklaracje
@pytest.mark.parametrize("change,needle", [
    ({"noise_source": "rerun"}, "rotacja placebo"),
    ({"independent_units": False}, "zależność obserwacji"),
    ({"sesoi": 0}, "sesoi"),
    ({"cluster_sizes": [10, 10], "independent_units": False}, "≠ n_units"),
])
def test_required_declarations(change, needle):
    spec = ci_spec(n=1000)
    spec["design"].update(change)
    rep = freeze_check(spec, n_sim=200)
    assert not rep["ok"] and any(needle in p for p in rep["problems"])


def test_family_size_tightens_alpha():
    rep = freeze_check({**ci_spec(n=1000), "design": {**ci_spec(n=1000)["design"], "family_size": 3}}, n_sim=N_SIM)
    assert any("rodzina 3" in p for p in rep["problems"])                         # 0,025 > 0,05/3


def test_unknown_label_and_rule_kind_rejected():
    rep = freeze_check({"design": ci_spec()["design"], "rule": {"kind": "threshold", "params": {}}}, n_sim=50)
    assert not rep["ok"] and any("bez kategorii" in p for p in rep["problems"])
    rep = freeze_check({"design": ci_spec()["design"], "rule": {"kind": "eval"}}, n_sim=50)
    assert not rep["ok"] and any("nieznany rodzaj" in p for p in rep["problems"])
    with pytest.raises(RuleSpecError):
        freeze_check({"design": {"n_units": 10}}, n_sim=50)


def test_deterministic_and_rendered():
    a = freeze_check(ci_spec(n=400), n_sim=300)
    b = freeze_check(ci_spec(n=400), n_sim=300)
    assert a["table"] == b["table"] and a["spec_sha256"] == b["spec_sha256"]
    assert "ODMOWA ZAMROŻENIA" in render(a) and "| +0.000 |" in render(a)
