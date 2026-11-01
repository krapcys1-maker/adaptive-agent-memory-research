"""wmb.t0_battery and wmb.contract: planted pairs for the pairwise judge, the rules applied at their boundaries, and the offline verifier.

Everything is synthetic: the replay data come from the E5 harness with a fake embedder and a fake writer; the judges are fakes (an ideal one and a blind one).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import replay_memory_sim as rp  # noqa: E402
from test_followup_memory_sim import FakeEmbedder  # noqa: E402
from test_replay_memory_sim import fake_generate, fake_judge as replay_judge, make_items  # noqa: E402
from wmb import contract, t0_battery as t0  # noqa: E402


def writer(system: str, user: str, seed: int, opts: dict) -> dict:
    out = fake_generate(system, user, seed, opts)
    if "BUILDS ON EARLIER" in out["text"]:
        out["text"] = "A note on the item. As I wrote earlier, the point stands. It adds one more detail about the item itself today."
    return out


def ideal_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    notes = re.search(r"NOTE 1:\n(.*?)\n\nNOTE 2:\n(.*?)\n\nWhich is", user, re.S).groups()

    def score(note: str) -> float:
        if note.startswith("note "):
            return 0.0                          # a verbatim copy of the earlier note
        if "Nothing to add here" in note:
            return -1.0
        if note.startswith("As I wrote last week about"):
            return -2.0                         # a fabricated callback
        return 1.0 if "As I wrote earlier" in note else 0.5

    a, b = score(notes[0]), score(notes[1])
    return {"text": "WINNER: %s" % ("TIE" if a == b else ("1" if a > b else "2"))}


def blind_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    return {"text": "WINNER: 1"}


@pytest.fixture(scope="module")
def replay(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("replay")
    items = make_items()
    prep = rp.prepare(items, FakeEmbedder(), fake_generate, workers=4)
    (root / "prep.json").write_text(json.dumps(prep), encoding="utf-8")
    rp.write_all(items, prep, root / "records.jsonl", writer, workers=4, log=lambda line: None)
    rp.judge_all(items, prep, rp.load_jsonl(root / "records.jsonl"), root / "pairs.jsonl", replay_judge, workers=4, log=lambda line: None)
    source = root / "items.jsonl"
    source.write_text("\n".join(json.dumps({"id": i.item_id, "date": str(i.day), "text": i.text}) for i in items) + "\n", encoding="utf-8")
    return {"dir": root, "items": source}


def run_all(replay: dict, work: Path, judge) -> dict:
    base = ["--items", str(replay["items"]), "--replay", str(replay["dir"]), "--workdir", str(work), "--workers", "4"]
    assert t0.main(["run"] + base + ["--retest"], generate=judge) == 0
    assert t0.main(["analyse"] + base + ["--json", str(work / "result.json")]) == 0
    return json.loads((work / "result.json").read_text(encoding="utf-8"))


def test_the_planted_pairs_are_what_they_say_they_are(replay: dict) -> None:
    prep, records = json.loads((replay["dir"] / "prep.json").read_text(encoding="utf-8")), contract.load_jsonl(replay["dir"] / "records.jsonl")
    from shadow_baseline_measures import parse_items
    with open(replay["items"], encoding="utf-8") as handle:
        items = parse_items(handle)
    tasks = t0.build_tasks(items, prep, records)
    by = {f: [t for t in tasks if t["family"] == f] for f in t0.FAMILIES}
    assert all(by[f] for f in t0.FAMILIES) and len(by["aa"]) == len(by["copy"])
    assert all(t["x"] == t["y"] for t in by["aa"]) and all(t["y"] == t["reference"] and t["y"].startswith("note ") for t in by["copy"])
    assert all("As I wrote earlier" in t["x"] and "As I wrote earlier" not in t["y"] and len(t["y"].split()) >= 10 for t in by["callback"])
    assert all(t["y"].startswith("As I wrote last week about ") and t["reference"] is None for t in by["spurious"]) and all(t["y"] == t0.NULL_NOTE for t in by["null"])
    assert t0.strip_callbacks("Fine start. As I wrote earlier, it holds. Then more.") == "Fine start. Then more." and t0.fabricate_callback("The point.", "a topic here.").startswith("As I wrote last week about a topic here, the point.")


def test_an_ideal_judge_passes_every_rule_and_a_second_run_changes_nothing(replay: dict, tmp_path: Path) -> None:
    result = run_all(replay, tmp_path, ideal_judge)
    read, fam = result["readings"], result["families"]
    assert all(read[k] for k in ("aa_ties", "copy_seen", "callback_seen", "spurious_seen", "null_seen", "order_consistent", "format_ok", "judge_usable_as_secondary"))
    assert fam["aa"]["tie_rate"] == 1.0 and fam["copy"]["win_share"] == 1.0 and fam["retest_agreement"]["same_verdict"] == 1.0 and result["order_consistency"]["share"] == 1.0
    again = t0.run_judgments([], ideal_judge, tmp_path / "judgments.jsonl")
    assert again == 0 and result["minimum_detectable_win_rate"]["43"] == pytest.approx(0.72, abs=5e-3)
    verdict = contract.verify_summary(tmp_path / "summary.json", tmp_path / "judgments.jsonl", t0.aggregate)
    assert verdict == {"records_sha256": True, "aggregates": True}


def test_a_blind_judge_fails_the_battery_and_the_verifier_notices_a_tampered_record(replay: dict, tmp_path: Path) -> None:
    result = run_all(replay, tmp_path, blind_judge)
    read, fam = result["readings"], result["families"]
    assert read["aa_ties"] is False and read["copy_seen"] is False and read["null_seen"] is False and read["judge_usable_as_secondary"] is False
    assert fam["aa"]["first_position_share_among_non_ties"] == 1.0 and fam["copy"]["win_share"] == 0.0
    lines = (tmp_path / "judgments.jsonl").read_text(encoding="utf-8").splitlines()
    changed = json.loads(lines[0])
    changed["winner"] = 2 if changed["winner"] == 1 else 1
    (tmp_path / "judgments.jsonl").write_text("\n".join([json.dumps(changed)] + lines[1:]) + "\n", encoding="utf-8")
    verdict = contract.verify_summary(tmp_path / "summary.json", tmp_path / "judgments.jsonl", t0.aggregate)
    assert verdict["records_sha256"] is False


def test_every_rule_applies_its_threshold_at_the_boundary() -> None:
    def agg(**over) -> dict:
        base = {"aa": {"verdicts": 80, "format_failures": 0, "tie_rate": 0.90}, "copy": {"verdicts": 80, "format_failures": 0, "win_share": 0.925},
                "callback": {"verdicts": 60, "format_failures": 0, "win_share": 0.925}, "spurious": {"verdicts": 80, "format_failures": 0, "win_share": 0.925},
                "null": {"verdicts": 80, "format_failures": 0, "win_share": 0.925}}
        for key, value in over.items():
            family, field = key.split("__")
            base[family][field] = value
        return base

    ok = {"share": 0.70}
    assert t0.readings(agg(), ok)["judge_usable_as_secondary"] is True
    assert t0.readings(agg(aa__tie_rate=0.899), ok)["aa_ties"] is False
    for family in ("copy", "callback", "spurious", "null"):
        assert t0.readings(agg(**{family + "__win_share": 0.924}), ok)[family + "_seen"] is False
    assert t0.readings(agg(), {"share": 0.699})["order_consistent"] is False and t0.readings(agg(), {"share": None})["order_consistent"] is False
    assert t0.readings(agg(copy__format_failures=4), ok)["format_ok"] is True and t0.readings(agg(copy__format_failures=8), ok)["format_ok"] is False
    assert t0.WIN_SHARE_MIN == pytest.approx(37 / 40) and t0.TIE_RATE_MIN == 0.90 and t0.ORDER_CONSISTENCY_MIN == 0.70 and t0.FORMAT_FAILURE_MAX == 0.02
