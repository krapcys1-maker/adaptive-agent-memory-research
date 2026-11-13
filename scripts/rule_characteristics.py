"""P1: charakterystyka reguły decyzyjnej — mechaniczny warunek zamrożenia nowego protokołu (audyt 2026-11-13).

Audyt pokazał, że zamrożone reguły dawały werdykty, których dane nie uzasadniały:
- test główny NIGHT-2 (SPEC §5): „obalone” przy stratach ≥ 8 — ramiona z blokiem mają 27–34 pary niezgodne, więc przy
  prawdziwym zysku +10 zadań reguła prawie nie mogła dać „wsparte”, a zwykle dawała „obalone”;
- H16 (PROTOCOL D12): próg „TrT ≥ TrQ + 2” bez istotności — przy 8 parach niezgodnych 36,3% fałszywych wsparć;
- bramka G2 księgi hipotez: „obalona” po progu w powtórzeniach, które przy temperaturze 0 są pseudoreplikacją.

Ten moduł nie zmienia żadnego historycznego werdyktu ani artefaktu. Liczy charakterystykę reguły symulacją na
zadeklarowanym modelu szumu, zanim protokół zostanie zamrożony, i odmawia zamrożenia, gdy:
- błąd I rodzaju (wsparcie bez efektu) przekracza próg — dla rodziny testów próg dzielony przez jej liczność;
- moc przy minimalnym efekcie istotnym praktycznie (SESOI) jest za mała, chyba że protokół jest jawnie eksploracyjny;
- prawdopodobieństwo ZAMKNIĘCIA kierunku (równoważność albo efekt ujemny) przy prawdziwym efekcie SESOI przekracza próg —
  to wychwytuje „brak istotności = brak efektu”;
- reguła nie ma osiągalnego stanu nierozstrzygniętego;
- etykieta „praktycznie istotne” pojawia się często przy efekcie dodatnim, ale mniejszym niż SESOI (brak rozdziału
  „efekt dodatni” od „efekt praktycznie istotny”);
- zależność obserwacji nie jest zadeklarowana (klastry albo jawne uzasadnienie niezależności);
- szum pochodzi z ponownego przebiegu (|N′ − N|) zamiast z rotacji placebo/perturbacji;
- reguła liczy powtórzenia jako replikację, a powtórzenia są prawie deterministyczne.

Progi (alpha_max, power_min, false_close_max, practical_leak_max) są DECYZJĄ NAUKOWĄ WŁAŚCICIELA; wartości domyślne
są propozycją. Moduł jest czysty: nie otwiera bazy, nie czyta danych eksperymentów, nie zapisuje plików.
Kategorie: practical (efekt ≥ SESOI wykazany), positive (efekt > 0 wykazany, praktyczność nierozstrzygnięta),
inconclusive, equivalent (|efekt| < SESOI wykazane), negative (efekt < 0 wykazany), invalid.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass, field
from functools import lru_cache

CATEGORIES = ("practical", "positive", "inconclusive", "equivalent", "negative", "invalid")
SUPPORT = frozenset({"practical", "positive"})
CLOSE = frozenset({"equivalent", "negative"})
NOISE_SOURCES = ("placebo", "perturbation")          # szum = rotacja przy bloku bez treści/przetasowanym, nie rerun

DEFAULT_THRESHOLDS = {"alpha_max": 0.05, "power_min": 0.80, "false_close_max": 0.05, "practical_leak_max": 0.25,
                      "inconclusive_min": 0.01, "deterministic_repeat_correlation": 0.9}


class RuleSpecError(ValueError):
    pass


@dataclass
class Design:
    n_units: int
    discordance: float                    # P(para niezgodna z ramieniem bazowym) przy braku efektu
    noise_source: str                     # 'placebo' | 'perturbation' (inne wartości = błąd)
    sesoi: float                          # minimalny efekt istotny praktycznie: zysk netto jako ułamek jednostek
    cluster_sizes: list[int] | None = None
    icc: float = 0.0                      # korelacja wewnątrzklastrowa kierunku zmiany (zależność obserwacji)
    independent_units: bool = False
    independence_justification: str = ""
    repeats: int = 1
    repeat_correlation: float | None = None   # 1.0 = powtórzenie deterministyczne (pseudoreplikacja)
    family_size: int = 1


# ------------------------------------------------------------------------------------------- statystyka
@lru_cache(maxsize=None)
def mcnemar_one_sided(gains: int, losses: int) -> float:
    """Dokładny jednostronny McNemar: P(X ≥ gains), X ~ Bin(gains+losses, 1/2)."""
    n = gains + losses
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(gains, n + 1)) / 2 ** n


def exact_threshold_rate(discordant: int, min_diff: int) -> float:
    """P(zyski − straty ≥ min_diff) przy braku efektu i ustalonej liczbie par niezgodnych (wynik dokładny)."""
    need = math.ceil((discordant + min_diff) / 2)
    return sum(math.comb(discordant, k) for k in range(max(need, 0), discordant + 1)) / 2 ** discordant


def paired_ci(gains: int, losses: int, n: int, z: float, deff: float = 1.0) -> tuple[float, float]:
    """Przedział dla różnicy proporcji w parach (Wald) z poprawką na efekt schematu (deff)."""
    d = (gains - losses) / n
    var = max(((gains + losses) / n - d * d) / n, 0.0) * deff
    se = math.sqrt(var) if var > 0 else 1.0 / n
    return d - z * se, d + z * se


# ------------------------------------------------------------------------------------------------ reguły
@dataclass
class Rule:
    """Reguła wbudowana (bez wykonywania kodu ze specyfikacji). kind: threshold | ci_states | repeats_gate."""
    kind: str
    params: dict = field(default_factory=dict)
    categories: dict = field(default_factory=dict)   # etykieta reguły -> kategoria
    uses_repeats_as_replication: bool = False

    def label(self, obs: dict, design: Design) -> str:
        n = obs["n"]
        r0 = obs["repeats"][0]
        g, l = r0["gains"], r0["losses"]
        p = self.params
        if self.kind == "threshold":
            diff = g - l
            sup = p.get("support", {})
            ref = p.get("refute", {})
            ok = diff >= sup.get("min_diff", 10 ** 9)
            ok = ok and mcnemar_one_sided(g, l) <= sup.get("max_p", 1.0)
            ok = ok and l <= sup.get("max_losses", 10 ** 9)
            if ok:
                return p.get("support_label", "supported")
            refuted = diff <= ref.get("max_diff", -10 ** 9) or l >= ref.get("min_losses", 10 ** 9)
            if ref.get("if_not_significant_at") is not None:
                refuted = refuted or mcnemar_one_sided(g, l) > ref["if_not_significant_at"]
            if refuted:
                return p.get("refute_label", "refuted")
            return p.get("else_label", "inconclusive")
        if self.kind == "ci_states":
            z = p.get("z", 1.959964)
            deff = 1.0
            if design.cluster_sizes:
                m = sum(design.cluster_sizes) / len(design.cluster_sizes)
                deff = 1.0 + (m - 1.0) * float(p.get("icc_assumed", 0.0))
            lo, hi = paired_ci(g, l, n, z, deff)
            delta = design.sesoi
            if lo >= delta:
                return "practical"
            if lo > 0:
                return "positive"
            if hi < 0:
                return "negative"
            if lo > -delta and hi < delta:
                return "equivalent"
            return "inconclusive"
        if self.kind == "repeats_gate":       # model bramki G2: próg w powtórzeniach, wsparcie dodatkowo z p
            need = 1 if p.get("deterministic") else int(p.get("min_repeats", 2))
            met = fal = 0
            for r in obs["repeats"]:
                d = (r["gains"] - r["losses"]) / n
                if d >= p["met_min"]:
                    met += 1
                elif d <= p["falsified_max"]:
                    fal += 1
            sig = mcnemar_one_sided(g, l) <= p.get("alpha", 0.05) / max(design.family_size, 1)
            if met and fal:
                return "conflicting"
            if fal >= need:
                return "refuted"
            if met >= need and sig:
                return "supported"
            return "inconclusive"
        raise RuleSpecError(f"nieznany rodzaj reguły {self.kind!r}")

    def category(self, label: str) -> str:
        if self.kind == "ci_states":
            return label
        cat = self.categories.get(label)
        if cat not in CATEGORIES:
            raise RuleSpecError(f"etykieta {label!r} bez kategorii (dozwolone: {CATEGORIES})")
        return cat


# --------------------------------------------------------------------------------------------- symulacja
def _beta(rng: random.Random, mean: float, icc: float) -> float:
    if icc <= 0 or mean <= 0 or mean >= 1:
        return mean
    k = 1.0 / icc - 1.0
    return rng.betavariate(mean * k, (1 - mean) * k)


def simulate_program(design: Design, effect: float, rng: random.Random) -> dict:
    """Jeden przebieg: zysk netto `effect` (ułamek jednostek); przy parze niezgodnej P(zysk) = 1/2 + effect/(2·d).
    Klastry: P(zysk) losowane z rozkładu beta o średniej jak wyżej i korelacji `icc`. Powtórzenia: jednostka
    zachowuje wynik z prawdopodobieństwem `repeat_correlation`, w przeciwnym razie jest losowana od nowa."""
    d = design.discordance
    p_gain = 0.5 + effect / (2 * d)
    if not 0.0 <= p_gain <= 1.0:
        raise RuleSpecError(f"efekt {effect} niemożliwy przy niezgodności {d} (|efekt| ≤ niezgodność)")
    sizes = design.cluster_sizes or [1] * design.n_units
    pcs = []
    for s in sizes:
        pc = _beta(rng, p_gain, design.icc) if design.cluster_sizes else p_gain
        pcs += [pc] * s
    first = []
    for pc in pcs:
        first.append(0 if rng.random() >= d else (1 if rng.random() < pc else -1))
    reps = []
    rho = 1.0 if design.repeat_correlation is None else design.repeat_correlation
    for r in range(max(design.repeats, 1)):
        cur = first if r == 0 else [u if rng.random() < rho else
                                    (0 if rng.random() >= d else (1 if rng.random() < pc else -1))
                                    for u, pc in zip(first, pcs)]
        reps.append({"gains": sum(1 for u in cur if u > 0), "losses": sum(1 for u in cur if u < 0)})
    return {"n": len(pcs), "repeats": reps}


def characteristics(rule: Rule, design: Design, effects: list[float], n_sim: int = 4000, seed: int = 20261113) -> dict:
    rng = random.Random(seed)
    table = {}
    for e in effects:
        counts = {c: 0 for c in CATEGORIES}
        labels: dict = {}
        for _ in range(n_sim):
            lab = rule.label(simulate_program(design, e, rng), design)
            labels[lab] = labels.get(lab, 0) + 1
            counts[rule.category(lab)] += 1
        table[f"{e:+.4f}"] = {"effect": e, **{c: v / n_sim for c, v in counts.items()},
                              "labels": {k: v / n_sim for k, v in sorted(labels.items())}}
    return table


def _ucb(p: float, n: int) -> float:
    return p + 2 * math.sqrt(max(p * (1 - p), 0.25 / n) / n)


def _lcb(p: float, n: int) -> float:
    return p - 2 * math.sqrt(max(p * (1 - p), 0.25 / n) / n)


# ------------------------------------------------------------------------------------ bramka zamrożenia
def parse_spec(spec: dict) -> tuple[Rule, Design, dict, str]:
    try:
        design = Design(**spec["design"])
        r = spec["rule"]
        rule = Rule(kind=r["kind"], params=r.get("params", {}), categories=r.get("categories", {}),
                    uses_repeats_as_replication=bool(r.get("uses_repeats_as_replication", r["kind"] == "repeats_gate")))
    except (KeyError, TypeError) as exc:
        raise RuleSpecError(f"niekompletna specyfikacja reguły: {exc}") from exc
    th = {**DEFAULT_THRESHOLDS, **(spec.get("thresholds") or {})}
    return rule, design, th, spec.get("tier", "confirmatory")


def spec_sha(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def freeze_check(spec: dict, n_sim: int | None = None, seed: int = 20261113) -> dict:
    """Raport: ok (czy wolno zamrozić), problemy, ostrzeżenia, tabela charakterystyki. Deterministyczny (ziarno)."""
    rule, d, th, tier = parse_spec(spec)
    n_sim = int(n_sim or spec.get("n_sim", 4000))
    problems: list[str] = []
    warnings: list[str] = []
    # ------------------------------------------------------------------ deklaracje wymagane przed symulacją
    if d.noise_source not in NOISE_SOURCES:
        problems.append(f"szum z „{d.noise_source}”: wymagana rotacja placebo/perturbacji ({NOISE_SOURCES}); "
                        "|N′ − N| mierzy tylko niedeterminizm ponownego przebiegu")
    if not d.sesoi or d.sesoi <= 0:
        problems.append("brak minimalnego efektu istotnego praktycznie (sesoi > 0)")
    if d.cluster_sizes:
        if sum(d.cluster_sizes) != d.n_units:
            problems.append(f"suma klastrów {sum(d.cluster_sizes)} ≠ n_units {d.n_units}")
        if not 0 <= d.icc < 1:
            problems.append("icc poza [0, 1)")
    elif not (d.independent_units and d.independence_justification.strip()):
        problems.append("zależność obserwacji niezadeklarowana: podaj cluster_sizes i icc albo independent_units "
                        "z uzasadnieniem")
    if d.repeats > 1 and d.repeat_correlation is None:
        problems.append("powtórzenia bez zmierzonej korelacji (repeat_correlation)")
    if rule.uses_repeats_as_replication and d.repeats > 1 and (d.repeat_correlation or 0) >= \
            th["deterministic_repeat_correlation"]:
        problems.append(f"pseudoreplikacja: reguła liczy powtórzenia jako replikację, a ich korelacja "
                        f"{d.repeat_correlation} ≥ {th['deterministic_repeat_correlation']} (replikacja = nowe jednostki)")
    if rule.kind == "repeats_gate" and rule.params.get("deterministic"):
        problems.append("flaga deterministic dla agenta LLM: jedno powtórzenie liczone jako replikacja")
    if problems and any("sesoi" in p or "≠ n_units" in p for p in problems):
        return {"ok": False, "problems": problems, "warnings": warnings, "table": {}, "spec_sha256": spec_sha(spec),
                "thresholds": th, "n_sim": n_sim}
    # ------------------------------------------------------------------------------------------ symulacja
    effects = [0.0, d.sesoi / 2, d.sesoi, 2 * d.sesoi]
    effects = [e for e in effects if abs(e) <= d.discordance]
    try:
        table = characteristics(rule, d, effects, n_sim=n_sim, seed=seed)
    except RuleSpecError as exc:
        problems.append(str(exc))
        return {"ok": False, "problems": problems, "warnings": warnings, "table": {}, "spec_sha256": spec_sha(spec),
                "thresholds": th, "n_sim": n_sim}
    row = {round(v["effect"], 9): v for v in table.values()}
    null, half, ses = row.get(0.0), row.get(round(d.sesoi / 2, 9)), row.get(round(d.sesoi, 9))
    sup = lambda r: sum(r[c] for c in SUPPORT)            # noqa: E731
    clo = lambda r: sum(r[c] for c in CLOSE)              # noqa: E731
    alpha = th["alpha_max"] / max(d.family_size, 1)
    if _ucb(sup(null), n_sim) > alpha:
        problems.append(f"błąd I rodzaju: P(wsparcie | brak efektu) = {sup(null):.3f} > {alpha:.4f}"
                        + (f" (alpha {th['alpha_max']} / rodzina {d.family_size})" if d.family_size > 1 else ""))
    if ses is None:
        problems.append("SESOI większe niż niezgodność: efektu nie da się zasymulować")
    else:
        if _lcb(sup(ses), n_sim) < th["power_min"]:
            msg = f"moc przy SESOI {d.sesoi:+.3f}: P(wsparcie) = {sup(ses):.3f} < {th['power_min']}"
            if tier == "exploratory":
                warnings.append(msg + " — protokół eksploracyjny: wynik nie zamyka kierunku i nie jest podstawą")
            else:
                problems.append(msg)
        if _ucb(clo(ses), n_sim) > th["false_close_max"]:
            problems.append(f"fałszywe zamknięcie: przy prawdziwym efekcie SESOI P(równoważność/ujemny) = "
                            f"{clo(ses):.3f} > {th['false_close_max']} (brak istotności traktowany jak brak efektu)")
    if max(v["inconclusive"] for v in table.values()) < th["inconclusive_min"]:
        problems.append("reguła nie ma osiągalnego stanu nierozstrzygniętego")
    has_practical = any(v["practical"] > 0 for v in table.values()) or "practical" in rule.categories.values()
    if has_practical and half is not None and _ucb(half["practical"], n_sim) > th["practical_leak_max"]:
        problems.append(f"brak rozdziału efektu dodatniego od praktycznego: przy efekcie SESOI/2 "
                        f"P(„praktycznie istotne”) = {half['practical']:.3f} > {th['practical_leak_max']}")
    if any(v["invalid"] > 0 for v in table.values()):
        warnings.append("reguła zwraca stan invalid w symulacji bez błędów wykonania")
    return {"ok": not problems, "problems": problems, "warnings": warnings, "table": table,
            "spec_sha256": spec_sha(spec), "thresholds": th, "n_sim": n_sim, "seed": seed, "tier": tier,
            "design": asdict(d), "rule": {"kind": rule.kind, "params": rule.params, "categories": rule.categories},
            "note": "progi są decyzją naukową właściciela; tabela nie zmienia historycznych werdyktów"}


def render(report: dict) -> str:
    lines = [f"Charakterystyka reguły ({report.get('n_sim')} symulacji na wiersz): "
             f"{'MOŻNA ZAMROZIĆ' if report['ok'] else 'ODMOWA ZAMROŻENIA'}", "",
             "| efekt | practical | positive | inconclusive | equivalent | negative | invalid |",
             "|---|---|---|---|---|---|---|"]
    for v in report.get("table", {}).values():
        lines.append(f"| {v['effect']:+.3f} | " + " | ".join(f"{v[c]:.3f}" for c in CATEGORIES) + " |")
    lines += [""] + [f"PROBLEM: {p}" for p in report["problems"]] + [f"uwaga: {w}" for w in report["warnings"]]
    return "\n".join(lines)
