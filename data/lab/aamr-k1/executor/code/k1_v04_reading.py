"""K1 v0.4: frozen reading rules as code (W4, W6). Replaces k1_v03_reading.py (kept unchanged in ../v0.3).

Changes against v0.3:
  - read() takes the decision intervals, not only the states; the state is computed here (state()), so state and text can
    never disagree;
  - V5 sentence states the upper bound U and says whether the historical M - N gain (12 of 148 tasks = 8.1 pp, temperature 0)
    is excluded (U < 8.108) or not (U >= 8.108), instead of always saying "not excluded";
  - composite A no longer claims that "memory content matters" in general: it names the beaten arm(s) and, when M - X is
    detected, warns that the advantage over X may come from harm done by foreign-domain traces;
  - composite B no longer claims an advantage over no block;
  - INVALID: one sentence and the descriptive line, nothing else;
  - forbidden phrases are checked on stems with regular expressions (tests below);
  - label of M - P: "format, domena i dobór łącznie" (section 3).
Run the tests: python -I -X utf8 -B k1_v04_reading.py
"""
from __future__ import annotations

import itertools
import re

THRESHOLD = 10.0
HIST_MN = 100.0 * 12 / 148                     # 8.108 pp: historical M - N at temperature 0 (NIGHT-2, E* vs N, 148 tasks)
STATES = ("V1", "V2", "V3", "V4", "V5", "V6")
DETECTED = {"V1", "V2", "V3"}
CONTRASTS = {
    "MP": ("M - P", "format, domena i dobór łącznie", "neutralny tekst tej samej długości pod tym samym nagłówkiem"),
    "MX": ("M - X", "domena i dobór przy stałym formacie śladu", "ślady z obcej domeny"),
    "MS": ("M - S", "dobór śladów do zadania", "losowe ślady z tej samej domeny"),
}


def fmt(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def state(L: float, U: float) -> str:
    assert L <= U
    if L >= THRESHOLD:
        return "V1"
    if L > 0:
        return "V2" if U >= THRESHOLD else "V3"
    if U < 0:
        return "V6"
    return "V4" if U >= THRESHOLD else "V5"


def contrast_sentence(k: str, L: float, U: float) -> str:
    name, what, _ = CONTRASTS[k]
    s = state(L, U)
    iv = f"[{fmt(L)}; {fmt(U)}] pp"
    if s == "V1":
        return f"{name}: efekt co najmniej 10 pp wykazany; przedział {iv} ({what})."
    if s == "V2":
        return f"{name}: efekt dodatni wykryty; nie wiadomo, czy sięga 10 pp; przedział {iv} ({what})."
    if s == "V3":
        return f"{name}: efekt dodatni wykryty i mniejszy niż 10 pp; przedział {iv} ({what})."
    if s == "V4":
        return f"{name}: nic nie rozstrzygnięto; przedział {iv} obejmuje zarówno zero, jak i 10 pp ({what})."
    if s == "V6":
        return f"{name}: efekt ujemny; ramię kontrolne wypada lepiej niż prawidłowa pamięć; przedział {iv} ({what})."
    tail = (f" Wynik nie wyklucza, że cały historyczny zysk M - N ({fmt(HIST_MN)} pp przy temperaturze 0) pochodzi z tego składnika."
            if U >= HIST_MN else
            f" Wynik wyklucza, że ten składnik w reżimie próbkowanym daje tyle, ile cały historyczny zysk M - N przy temperaturze 0 "
            f"({fmt(HIST_MN)} pp).")
    return f"{name}: efektu nie wykryto; przedział {iv} dopuszcza efekty najwyżej do {fmt(U)} pp ({what}).{tail}"


def read(intervals: dict, est: dict, invalid: str | None = None, length: dict | None = None) -> list:
    """intervals: MP/MX/MS -> (L, U) in pp (98.33% decision intervals); est: descriptive M - N and P - N (strings);
    invalid: reason for the INVALID state (section 7.2) or None; length: MP/MX/MS -> {"flag": bool, "reasons": [str],
    "adj": (L, U)} from k1_length (rule LEN, D9) or None. Returns the reading as a list of sentences."""
    desc = (f"OPISOWO (bez stanu): M - N = {est['MN']}; P - N = {est['PN']}. Efekty kontrastów liczone są względem ramion "
            "kontrolnych, nie względem braku bloku.")
    if invalid is not None:
        return [f"NIEWAŻNY: {invalid}; żadnych wniosków o kontrastach.", desc]
    assert set(intervals) == set(CONTRASTS)
    length = length or {}
    flag = {k: bool(length.get(k, {}).get("flag")) for k in CONTRASTS}
    st = {k: state(*intervals[k]) for k in CONTRASTS}
    out = []
    for k in ("MP", "MX", "MS"):
        line = contrast_sentence(k, *intervals[k])
        if flag[k]:
            line += (" DŁUGOŚĆ (WR5): " + "; ".join(length[k].get("reasons") or ["kryterium LEN spełnione"]) +
                     ". Różnica długości bloków może wyjaśniać ten wynik; efektu nie przypisuje się treści pamięci.")
        out.append(line)
    withheld = [CONTRASTS[k][0][-1] for k in ("MX", "MS") if st[k] in DETECTED and flag[k]]
    beaten = [CONTRASTS[k][0][-1] for k in ("MX", "MS") if st[k] in DETECTED and not flag[k]]
    if withheld:
        out.append(f"ZŁOŻONE-A wstrzymane dla {' i '.join(withheld)}: różnica długości może wyjaśniać wynik (WR5).")
    if beaten:
        names = " i ".join(beaten)
        a = (f"ZŁOŻONE-A: przy tym samym nagłówku i formacie wynik zależy od treści śladów: prawidłowa pamięć wypada lepiej niż "
             f"{names}. Nie wynika z tego, że pamięć pomaga względem P ani N.")
        if "X" in beaten:
            a += " Przewaga nad X może wynikać ze szkody wyrządzanej przez ślady obcej domeny (patrz opisowe X - P)."
        out.append(a)
    if st["MP"] in DETECTED and flag["MP"]:
        out.append("ZŁOŻONE-B wstrzymane: różnica długości między M i P może wyjaśniać wynik (WR5).")
    elif st["MP"] in DETECTED:
        out.append("ZŁOŻONE-B: prawidłowa pamięć wypada lepiej niż neutralny tekst tej samej długości pod tym samym nagłówkiem; "
                   "różnicy M - P nie da się sprowadzić do samej obecności dodatkowego tekstu. O przewadze nad brakiem bloku "
                   "mówi tylko opisowe M - N.")
    if all(s in ("V4", "V5") for s in st.values()):
        out.append(SENT_C)
    if all(s in ("V3", "V5", "V6") for s in st.values()) and \
            not any(flag[k] and length[k].get("adj", (0.0, 0.0))[1] >= THRESHOLD for k in CONTRASTS):
        out.append("ZŁOŻONE-D: każdy z trzech efektów, jeśli istnieje, jest mniejszy niż 10 pp.")
    out.append(desc)
    return out


SENT_C = "ZŁOŻONE-C: żaden kontrast nie wykrył efektu. To nie jest dowód braku efektu treści."
A_DISCLAIMER = "Nie wynika z tego, że pamięć pomaga względem P ani N."
# forbidden on stems (section 8); the two allowed sentences that negate such claims are removed before the scan
FORBIDDEN = [r"przypisyw", r"sta[łl]\w{0,3}\s+przyk[łl]ad", r"148\s+zada\w*\s+nie\s+wystarcz", r"\bnie\s+pochodz",
             r"brak\w{0,3}\s+efekt\w*\s+treści", r"pami\w*\s+(?:nie\s+)?pomaga", r"efekt\w*\s+treści\s+nie\s+(?:ma|istnieje)",
             r"przewag\w*\s+(?:prawidłowej\s+)?pamięci\s+nad\s+brak"]


def forbidden_hits(text: list) -> list:
    joined = " ".join(text).replace(SENT_C, "").replace(A_DISCLAIMER, "").replace("O przewadze nad brakiem bloku mówi tylko", "")
    return [p for p in FORBIDDEN if re.search(p, joined, re.I)]


# ----------------------------------------------------------------------------------------------- tests
def implied(line: str):
    """Constraints on (L, U) that a contrast sentence asserts, as predicates. Every assertive clause must map to one."""
    c = []
    if "co najmniej 10 pp wykazany" in line:
        c.append(("L>=10", lambda L, U: L >= 10))
    if "efekt dodatni wykryty" in line:
        c.append(("L>0", lambda L, U: L > 0))
    if "mniejszy niż 10 pp" in line:
        c.append(("U<10", lambda L, U: U < 10))
    if "nie wiadomo, czy sięga 10 pp" in line:
        c.append(("L<10<=U", lambda L, U: L < 10 <= U))
    if "nic nie rozstrzygnięto" in line:
        c.append(("L<=0, U>=10", lambda L, U: L <= 0 and U >= 10))
    if "efektu nie wykryto" in line:
        c.append(("L<=0", lambda L, U: L <= 0))
    if "Wynik nie wyklucza" in line:
        c.append(("U>=hist", lambda L, U: U >= HIST_MN))
    elif "Wynik wyklucza" in line:
        c.append(("U<hist", lambda L, U: U < HIST_MN))
    if "efekt ujemny" in line:
        c.append(("U<0", lambda L, U: U < 0))
    return c


if __name__ == "__main__":
    est = {"MN": "<estymata i przedział 95%>", "PN": "<estymata i przedział 95%>"}
    log = []
    P = lambda *a: (print(*a), log.append(" ".join(map(str, a))))
    n_checked = 0

    # T-stan: grid and boundaries from section 6.3
    for (L, U), want in {(3, 8): "V3", (-2, 8): "V5", (2, 14): "V2", (-3, 12): "V4", (11, 20): "V1", (-9, -1): "V6", (0, 10): "V4",
                         (0, 9.99): "V5", (10, 15): "V1", (0, 0): "V5", (-1, 0): "V5", (9.99, 10): "V2", (0.01, 9.99): "V3"}.items():
        assert state(L, U) == want, (L, U, state(L, U), want)
    # partition: exactly one state on a fine grid
    grid = [x / 2 for x in range(-40, 51)]                      # -20 .. 25 pp, step 0.5
    pairs = [(L, U) for L in grid for U in grid if L <= U]
    for L, U in pairs:
        assert sum([L >= 10, 0 < L < 10 <= U, 0 < L and U < 10, L <= 0 and U >= 10, L <= 0 <= U < 10, U < 0]) == 1

    # T-zgodność treści: every sentence asserts only what its interval implies (all pairs, each contrast)
    for k in CONTRASTS:
        for L, U in pairs:
            line = contrast_sentence(k, L, U)
            cons = implied(line)
            assert cons, line
            for name, f in cons:
                assert f(L, U), (k, L, U, name, line)
            if state(L, U) == "V5":
                assert ("nie wyklucza" in line) == (U >= HIST_MN)
            n_checked += 1
    P(f"contrast sentences checked against their interval: {n_checked} ({len(pairs)} (L, U) pairs x 3 contrasts, step 0.5 pp on [-20; 25])")

    # composites: on a coarser grid of all three contrasts
    reps = [(-9, -1), (-8, 2), (-2, 8), (-5, 9), (-3, 12), (2, 14), (3, 8), (11, 20), (-1, 8.11), (-1, 8.10)]
    n_comb = 0
    for mp, mx, ms in itertools.product(reps, repeat=3):
        iv = {"MP": mp, "MX": mx, "MS": ms}
        text = read(iv, est)
        st = {k: state(*v) for k, v in iv.items()}
        assert read(iv, est) == text                                   # deterministic
        assert sum(t.startswith("M - ") for t in text) == 3 and text[-1].startswith("OPISOWO")
        assert not forbidden_hits(text), (iv, forbidden_hits(text))
        A = next((t for t in text if t.startswith("ZŁOŻONE-A")), None)
        assert (A is not None) == (st["MX"] in DETECTED or st["MS"] in DETECTED)
        if A:
            assert ("niż X" in A or "X i S" in A) == (st["MX"] in DETECTED)
            assert ("S." in A.split("Nie wynika")[0]) == (st["MS"] in DETECTED)
            assert ("szkody" in A) == (st["MX"] in DETECTED)
        assert any(t.startswith("ZŁOŻONE-B") for t in text) == (st["MP"] in DETECTED)
        assert (SENT_C in text) == all(s in ("V4", "V5") for s in st.values())
        if any(t.startswith("ZŁOŻONE-D") for t in text):
            assert all(v[1] < 10 for v in iv.values())
        if SENT_C in text:
            assert all(v[0] <= 0 for v in iv.values())
        n_comb += 1
    P(f"composite rules checked on {n_comb} interval combinations ({len(reps)} representative intervals per contrast, all 6 states, "
      f"U on both sides of {fmt(HIST_MN)} pp)")

    # review N3 counterexamples, exact text
    a = contrast_sentence("MP", -8, 2)                                 # (a) V5 with U < 8.1
    assert a == ("M - P: efektu nie wykryto; przedział [-8,0; 2,0] pp dopuszcza efekty najwyżej do 2,0 pp (format, domena i dobór "
                 "łącznie). Wynik wyklucza, że ten składnik w reżimie próbkowanym daje tyle, ile cały historyczny zysk M - N przy "
                 "temperaturze 0 (8,1 pp)."), a
    b = read({"MP": (-4, 6), "MX": (1, 19), "MS": (-5, 5)}, est)       # (b) X harms: M - X detected, M - P and M - S near 0
    assert b[3] == ("ZŁOŻONE-A: przy tym samym nagłówku i formacie wynik zależy od treści śladów: prawidłowa pamięć wypada lepiej "
                    "niż X. Nie wynika z tego, że pamięć pomaga względem P ani N. Przewaga nad X może wynikać ze szkody "
                    "wyrządzanej przez ślady obcej domeny (patrz opisowe X - P)."), b[3]
    c = read({"MP": (1, 19), "MX": (-6, 9), "MS": (-6, 9)}, est)       # (c) M - P = V2 while M is worse than N
    assert c[3] == ("ZŁOŻONE-B: prawidłowa pamięć wypada lepiej niż neutralny tekst tej samej długości pod tym samym nagłówkiem; "
                    "różnicy M - P nie da się sprowadzić do samej obecności dodatkowego tekstu. O przewadze nad brakiem bloku mówi "
                    "tylko opisowe M - N."), c[3]
    assert not any("przewaga prawidłowej pamięci nie sprowadza" in t for t in c)
    P("review counterexamples N3 (a), (b), (c): exact sentences asserted")

    # (d) forbidden phrases on stems: inflected variants must be caught, the allowed negations must not
    for bad in ("zysków nie należy przypisywać pamięci", "to dowodzi brakiem efektu treści", "wystarczą stałe przykłady",
                "148 zadań nie wystarczy", "zysk nie pochodzi z pamięci", "pamięć nie pomaga", "efekt treści nie istnieje",
                "przewaga pamięci nad brakiem bloku"):
        assert forbidden_hits([bad]), bad
    assert not forbidden_hits([SENT_C, "ZŁOŻONE-A: ... X. " + A_DISCLAIMER])
    P("forbidden phrases: 8 inflected variants caught; composite C and the A disclaimer allowed")

    # W6: INVALID
    inv = read({"MP": (11, 20), "MX": (11, 20), "MS": (11, 20)}, est, invalid="mniej niż 2 ukończone bloki próbkowane")
    assert inv == ["NIEWAŻNY: mniej niż 2 ukończone bloki próbkowane; żadnych wniosków o kontrastach.", inv[1]]
    assert inv[1].startswith("OPISOWO") and not any(t.startswith(("M - ", "ZŁOŻONE")) for t in inv)
    inv2 = read({}, est, invalid="kontrola L3 zatrzymała program")
    assert len(inv2) == 2
    P("INVALID: one sentence + descriptive line, no contrast or composite sentence (also with intervals that would read V1)")

    # D9: rule LEN - no attribution to memory content when length may explain the result
    nf = 0
    for mp, mx, ms in itertools.product(reps, repeat=3):
        iv = {"MP": mp, "MX": mx, "MS": ms}
        for fl in itertools.product((False, True), repeat=3):
            L = {k: {"flag": f, "reasons": ["test"], "adj": (-5, 12)} for k, f in zip(("MP", "MX", "MS"), fl)}
            text = read(iv, est, length=L)
            if not any(fl):
                assert text == read(iv, est)
                continue
            for k, f in zip(("MP", "MX", "MS"), fl):
                line = next(t for t in text if t.startswith(CONTRASTS[k][0]))
                assert ("nie przypisuje się treści pamięci" in line) == f
            A = next((t for t in text if t.startswith("ZŁOŻONE-A:")), "")
            if fl[1]:
                assert "niż X" not in A and "X i S" not in A and "szkody" not in A
            if fl[2]:
                assert "niż S" not in A and "i S." not in A
            if fl[0]:
                assert not any(t.startswith("ZŁOŻONE-B:") for t in text)
            assert not any(t.startswith("ZŁOŻONE-D") for t in text)       # adjusted upper bound 12 >= 10 withholds D
            assert not forbidden_hits(text)
            nf += 1
    P(f"length rule LEN: {nf} flagged readings; a flagged contrast is never attributed to memory content (no A/B on it, caveat present)")

    P("\nexample, review counterexample (b):")
    for line in b:
        P("   ", line)
    P("RESULT W4/W6-reading: PASS")
    from pathlib import Path
    Path(__file__).with_suffix(".out").write_text("\n".join(log) + "\n", encoding="utf-8")
