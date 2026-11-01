"""Tests for the GOALSHIFT generator (AAM-E0). Standard library and pytest only."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus import goalshift as gs  # noqa: E402

SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)  # development-style seeds; never 100-119


@pytest.fixture(scope="module")
def worlds():
    return {s: gs.generate(s) for s in SEEDS}


def _strip(template: str) -> str:
    return re.sub(r"\{[a-z0-9]+\}", " ", template)


def test_lcg_is_pinned_across_python_versions():
    r = gs.Lcg(1)
    assert [r.below(1000) for _ in range(6)] == [795, 500, 553, 65, 839, 198]
    r = gs.stream(7, "a", "b")
    assert [r.below(1000) for _ in range(6)] == [944, 804, 43, 954, 629, 434]


def test_stemmer_and_content_words():
    assert gs.stem("delivered") == "deliver"
    assert gs.stem("policies") == "policy"
    assert gs.stems_of("The 14th of May: delays and delayed shipments") >= {"delay", "shipment"}
    assert gs.stems_of("the and of 14th 7") == set()


def test_generation_is_deterministic_and_seeds_differ():
    assert gs.digest(gs.generate(3)) == gs.digest(gs.generate(3))
    assert gs.digest(gs.generate(3)) != gs.digest(gs.generate(4))


def test_world_shape(worlds):
    for seed, w in worlds.items():
        events = w["events"]
        assert len(events) == gs.N_EVENTS
        assert [e["event_id"] for e in events] == ["e%03d" % i for i in range(1, 151)]
        assert [e["day"] for e in events] == sorted(e["day"] for e in events)
        assert all(gs.LEN_MIN <= gs.word_count(e["text"]) <= gs.LEN_MAX for e in events)
        assert all(1 <= e["day"] <= gs.N_DAYS for e in events)
        probes = w["labels"]["probes"]
        assert len(probes) == 12
        for cell in gs.CELLS:
            assert sum(1 for p in probes if p["cell"] == cell) == gs.PROBES_PER_CELL
        domains = [g["domain"] for g in w["goals"]]
        assert len(set(domains)) == 3 and all(d in gs.DOMAINS for d in domains)


def test_probe_timing_gold_and_decoys(worlds):
    for w in worlds.values():
        by_id = {e["event_id"]: e for e in w["events"]}
        cue_of = {c["probe_id"]: c for c in w["cues"]}
        codes = set()
        for p in w["labels"]["probes"]:
            target, cue = by_id[p["gold_event_id"]], cue_of[p["probe_id"]]
            assert 2 <= target["day"] <= 9
            assert 21 <= cue["day"] <= 30
            assert cue["day"] - target["day"] >= 14
            assert p["gold_answer"] in target["text"].lower()
            assert p["gold_answer"] not in (cue["cue"] + cue["question"] + cue["goal"]).lower()
            assert not re.search(r"\be\d{3}\b", cue["cue"] + cue["question"] + cue["goal"])
            assert len(p["decoy_ids"]) >= 2
            assert all(by_id[d]["day"] < cue["day"] for d in p["decoy_ids"])
            assert p["gold_answer"] not in codes
            codes.add(p["gold_answer"])
        kinds = [lab["kind"] for lab in w["labels"]["events"].values()]
        assert kinds.count("target") == 12


def test_overlap_levels_are_measured_not_assumed(worlds):
    c1 = []
    for w in worlds.values():
        by_id = {e["event_id"]: e for e in w["events"]}
        cue_of = {c["probe_id"]: c for c in w["cues"]}
        for p in w["labels"]["probes"]:
            cue, target = cue_of[p["probe_id"]], by_id[p["gold_event_id"]]
            measured = gs.overlap_fraction(cue["cue"], target["text"])
            assert abs(measured - p["overlap"]) < 1e-3
            assert gs.overlap_fraction(cue["goal"], target["text"]) == p["goal_overlap"]
            if p["cell"] == "C1":
                c1.append(measured)
                assert 0.25 <= measured <= 0.55
            else:
                assert measured == 0.0 and p["goal_overlap"] == 0.0
    assert 0.33 <= sum(c1) / len(c1) <= 0.47


def test_c3_is_role_based_in_another_domain(worlds):
    for w in worlds.values():
        for p in w["labels"]["probes"]:
            if p["cell"] == "C3":
                assert p["concept"].startswith("role:") and p["role"] in gs.ROLE_NAMES
                assert p["domain_target"] != p["domain_cue"]
            else:
                assert p["concept"].startswith("topic:") and p["role"] is None
    roles = {p["role"] for w in worlds.values() for p in w["labels"]["probes"] if p["cell"] == "C3"}
    assert len(roles) >= 6  # role variety across worlds (8 roles exist)


def test_c3_lookalike_decoy_has_opposite_outcome(worlds):
    for w in worlds.values():
        labs = w["labels"]["events"]
        for p in w["labels"]["probes"]:
            kinds = [labs[d]["kind"] for d in p["decoy_ids"]]
            assert ("decoy_lookalike" in kinds) == (p["cell"] == "C3")
            assert "decoy_surface" in kinds and "decoy_domain" in kinds


def test_cue_file_identical_without_history(worlds):
    for seed, w in worlds.items():
        assert gs.generate(seed, history=False)["cues"] == w["cues"]


def test_cues_do_not_depend_on_filler(monkeypatch):
    base = gs.generate(2)
    monkeypatch.setattr(gs, "ROUTINE", {k: ["{p} reviewed the quarterly folder"] * 6
                                        for k in gs.ROUTINE})
    monkeypatch.setattr(gs, "CHATTER", ["{p} watered the plants at {pl}"] * 6)
    changed = gs.generate(2)
    assert changed["cues"] == base["cues"]
    assert [e["text"] for e in changed["events"]] != [e["text"] for e in base["events"]]


def test_cue_names_do_not_leak_into_other_events(worlds):
    for w in worlds.values():
        labs = w["labels"]["events"]
        by_id = {e["event_id"]: e for e in w["events"]}
        cue_of = {c["probe_id"]: c for c in w["cues"]}
        for p in w["labels"]["probes"]:
            names = set(re.findall(r"\b[A-Z][a-z]+[a-z]{2,}\b", cue_of[p["probe_id"]]["cue"])) - {
                "Plan", "Decide", "Work", "Start", "Look", "Recall", "Anything", "Prepare"}
            for eid, e in by_id.items():
                if eid == p["gold_event_id"] or labs[eid]["probe_id"] == p["probe_id"]:
                    continue
                for name in names:
                    if len(name) > 6 and name[-4:] in ("ford", "mere", "wick", "dale", "ham", "worth"):
                        assert name not in e["text"]


def test_write_time_fields_depend_on_position_only(monkeypatch):
    """Consequence and novelty are drawn by position, so they cannot encode kind, text or
    anything after the event (the v0.1 leak: consequence by kind, novelty falling with time)."""
    base = gs.generate(1)
    assert all(0.0 <= e["novelty"] <= 1.0 and e["consequence"] in (0, 1, 2, 3) for e in base["events"])
    monkeypatch.setattr(gs, "ROUTINE", {k: ["{p} reviewed the quarterly folder"] * 6
                                        for k in gs.ROUTINE})
    changed = gs.generate(1)
    assert [e["text"] for e in changed["events"]] != [e["text"] for e in base["events"]]
    assert ([(e["consequence"], e["novelty"]) for e in changed["events"]]
            == [(e["consequence"], e["novelty"]) for e in base["events"]])


def test_write_time_fields_carry_no_information_about_the_targets(worlds):
    by = {"target": [], "filler": []}
    first_days, late_days = [], []
    for w in worlds.values():
        labs = w["labels"]["events"]
        for e in w["events"]:
            kind = labs[e["event_id"]]["kind"]
            if kind == "target":
                by["target"].append((e["consequence"], e["novelty"]))
            elif kind in ("filler", "noise"):
                by["filler"].append((e["consequence"], e["novelty"]))
                (first_days if e["day"] <= 9 else late_days).append(e["novelty"])
    mean = lambda xs: sum(xs) / len(xs)  # noqa: E731
    assert abs(mean([c for c, _ in by["target"]]) - mean([c for c, _ in by["filler"]])) < 0.35
    assert abs(mean([n for _, n in by["target"]]) - mean([n for _, n in by["filler"]])) < 0.12
    assert abs(mean(first_days) - mean(late_days)) < 0.08  # no fall with time


def test_every_event_carries_a_reference_code(worlds):
    code = re.compile(r"\b[bcdfghjkmnpqrstvwxz]{2}\d{4}\b")
    for w in worlds.values():
        assert all(code.search(e["text"].lower()) for e in w["events"])


def test_roles_are_balanced_over_consecutive_seeds():
    counts = {r: 0 for r in gs.ROLE_NAMES}
    for seed in range(200, 220):
        goals = gs.build_goals(seed)
        specs, _ = gs.build_probe_specs(seed, goals, gs.Used())
        roles = [s["role"] for s in specs if s["cell"] == "C3"]
        assert len(set(roles)) == 4
        for r in roles:
            counts[r] += 1
    assert set(counts.values()) == {10}


def test_templates_are_lexically_disjoint_between_event_and_cue_side():
    for domain, topics in gs.TOPICS.items():
        assert len(topics) == 9 and len({t["id"] for t in topics}) == 9
        for t in topics:
            assert len(t["B"]) >= 2
            for a in t["A"]:
                for b in t["B"]:
                    assert not (gs.stems_of(_strip(a)) & gs.stems_of(b)), (t["id"], a, b)
                for goal in gs.GOALS[domain]:
                    assert not (gs.stems_of(_strip(a)) & gs.stems_of("Current goal: " + goal)) or \
                        len(t["A"]) > 1, (t["id"], goal)


def test_role_material_covers_eight_roles_and_six_domains():
    assert len(gs.ROLES) == 8 and len(gs.DOMAINS) == 6
    for role, d in gs.ROLES.items():
        assert len(d["E"]) >= 2 and len(d["Q"]) >= 2 and d["NEG"]
    assert set(gs.SCENES) == set(gs.TASKS) == set(gs.ROUTINE) == set(gs.DOMAINS)


def test_no_surface_form_is_shared_across_worlds(worlds):
    texts = [e["text"] for w in worlds.values() for e in w["events"]]
    assert len(set(texts)) >= 0.99 * len(texts)
    targets = [e["text"] for w in worlds.values() for e in w["events"]
               if w["labels"]["events"][e["event_id"]]["kind"] == "target"]
    assert len(set(targets)) == len(targets)


def test_many_seeds_generate_without_error():
    for seed in range(200, 240):  # never the test seeds
        gs.generate(seed)


def test_written_files_use_lf(tmp_path, worlds):
    gs.write_world(worlds[0], tmp_path / "w")
    for name in ("history.jsonl", "cues.jsonl", "labels.json"):
        data = (tmp_path / "w" / name).read_bytes()
        assert b"\r" not in data and data.endswith(b"\n")


@pytest.mark.parametrize("name", ["corpus/goalshift.py", "corpus/goalshift_arms.py",
                                  "run_goalshift_e0.py"])
def test_sources_parse_as_python_311(name):
    source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
    ast.parse(source, feature_version=(3, 11))
    assert "\r" not in source
