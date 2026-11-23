"""The published ALFWORLD-LADDER-R4-V6 instrument (tools/alfworld_ladder/v6/) is the lab's instrument, byte for byte.

A `setup: same` replication (#252, #251, #250) is only meaningful if every file a volunteer runs has the digest the
lab pinned. These tests tie the folder to the program's public provenance (`knowledge.jsonl`), check that its games
are the published package's games, and check that nothing in it comes from a sealed split (`valid_unseen`) or the
other held-out split (`valid_seen`).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
V6 = ROOT / "tools" / "alfworld_ladder" / "v6"
PACKAGE = ROOT / "data" / "lab" / "autolab-alfworld-ladder-r4-v6"
sys.path.insert(0, str(ROOT / "scripts"))

import aamr_export  # noqa: E402

# Full SHA-256 of each pinned file, as in the program envelope and in knowledge.jsonl.
PINNED = {
    "src/agent.py": "b223b34ba1f9d2957d9ab2dffca11e339d9dda2dddaf84e2ebf2572beb56b841",
    "src/run_episode.sh": "39024c9525d1a575dccd0e7bc96828ec7eb9932fe2f94e94628ead61b7ecfa39",
    "src/vllm_serve.sh": "b4ba3d576d80b70550b1b833b0c52067a8b109148a52e861fd7733f6d4d520a3",
    "instrument/memory_build.md": "44ac891f6fd33da80b97dcd72ff1aab97fb291829db5afebdafed064470c9920",
    "instrument/prompt_template.txt": "f04f0ba7697cf78e5fd6babd87f9cad81e68b627829555e31edd14f5bf6e6cd7",
    "instrument/prompt_examples.txt": "bf37a8630a85b28b9ba6fa0081a1fa4e422fb2358b396dfe64bd27b8f00600b1",
    "instrument/placebo.txt": "ac91b81d689a4994bf60ea660b7294d5606792ca1e6e46274243d09e2720b834",
    "instrument/length_check.json": "ec2c8ded3f46082922873feb99da61ba59943904e0b705f0939223af3daea094",
    "data/bank.jsonl": "e8bd0daf75f30847b8a839a0c45ccb72b0fa3d7e23b485fdc59c99743dfccef1",
    "data/units.json": "5c4b594aa6e389db14316cd2a0d533428111542cc7ec16a8c8d37d58c40ea78e",
    "data/families.json": "83c42d8f04e60aa55e27556e1502584a75a7229ee5856feba66cb734cf9f6c6c",
    "data/pilot_units.json": "5d0a565f11934420094be57e7471242ecde2b9e9bde5ba5e7968e8933f139924",
}
# Not pinned before this publication (the agent does not read it); fixed here.
UNPINNED = {"data/unit_goals.json": "92cb33541dd97021787cb738c739814426d6fd4347e6f8b6a98bb3cb8760b07c"}
DESIGNATED_300 = {
    "retrieved_task": "c90b87e5ea2de9b96645b68841a122b389f41a64344ebc3045fae50724778e0e",
    "retrieved_steps": "49de1b1845fc3a94cfa04bc69044b4679207621dec941d7f71b544e0996c1407",
    "retrieved_plan": "e03b7c17411d31c0fa644e9e39e7db788218d8bda590f9a16b69d2f7fb2efee3",
}
GAME_ID = re.compile(r"\b(train|valid_seen|valid_unseen|valid_train)/[a-z_]+-[A-Za-z]")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(rel: str):
    return json.loads((V6 / rel).read_text(encoding="utf-8"))


def bank() -> list[dict]:
    return [json.loads(line) for line in (V6 / "data" / "bank.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def unit_id(task: str) -> str:
    return hashlib.sha256(("alfworld-ladder-r4-v6|" + task).encode()).hexdigest()[:10] + "~" + task


def knowledge_text() -> str:
    return (PACKAGE / "knowledge.jsonl").read_text(encoding="utf-8")


def published_files() -> list[Path]:
    return sorted(p for p in V6.rglob("*") if p.is_file())


def test_folder_holds_exactly_the_expected_files():
    expected = set(PINNED) | set(UNPINNED) | {"SETUP_SAME.md"}
    assert {p.relative_to(V6).as_posix() for p in published_files()} == expected


@pytest.mark.parametrize("rel", sorted(PINNED))
def test_file_matches_the_lab_pin(rel):
    assert sha256(V6 / rel) == PINNED[rel]


def test_every_pin_is_in_the_program_provenance():
    objects = [json.loads(line) for line in knowledge_text().splitlines() if line.strip()]
    program = next(o["payload"] for o in objects if o["kind"] == "program")
    run = next(o["payload"] for o in objects if o["kind"] == "run")
    envelope_pins = set(program["domain_params"]["runner"]["pins"].values()) | set(program["instrument"]["sha256"].values())
    runner_pins = set(run["measurement"]["runner_pins"].values())
    command_files = {"src/agent.py", "src/run_episode.sh", "src/vllm_serve.sh", "data/bank.jsonl", "data/units.json",
                     "data/families.json", "data/pilot_units.json", "instrument/placebo.txt"}
    for rel, digest in PINNED.items():
        assert digest in envelope_pins, rel
        if rel in command_files:
            assert digest in runner_pins, rel
    assert set(run["measurement"]["runner_pins_at_end"].values()) == runner_pins
    assert program["domain_params"]["units_sha256"] == PINNED["data/units.json"]
    assert program["domain_params"]["families_sha256"] == PINNED["data/families.json"]


def test_unit_goals_cover_exactly_the_units():
    assert sha256(V6 / "data" / "unit_goals.json") == UNPINNED["data/unit_goals.json"]
    goals = load("data/unit_goals.json")
    assert set(goals) == set(load("data/units.json"))
    assert all(isinstance(g, str) and g.strip() for g in goals.values())


def test_setup_same_lists_every_digest():
    text = (V6 / "SETUP_SAME.md").read_text(encoding="utf-8")
    for rel, digest in {**PINNED, **UNPINNED}.items():
        assert f"`{rel}`" in text and digest in text, rel


def test_units_are_the_published_package_units():
    units = load("data/units.json")
    assert len(units) == len(set(units)) == 360
    ids = {unit_id(t) for t in units}
    with open(PACKAGE / "per_unit.csv", encoding="utf-8-sig", newline="") as handle:
        measured = {row["unit"] for row in csv.DictReader(handle)}
    assert len(measured) == 300
    assert measured <= ids


@pytest.mark.parametrize("arm", sorted(DESIGNATED_300))
def test_designated_300_reproduce_the_task_pin(arm):
    ids = sorted(unit_id(t) for t in load("data/units.json"))
    chosen = sorted(random.Random(f"ALFWORLD-LADDER-R4-V6:replication:{arm}").sample(ids, 300))
    digest = hashlib.sha256(json.dumps(chosen).encode()).hexdigest()
    assert digest == DESIGNATED_300[arm]
    assert digest in knowledge_text()


def test_only_train_games_and_no_shared_family():
    units, pilot, items = load("data/units.json"), load("data/pilot_units.json"), bank()
    families = load("data/families.json")
    tasks = units + pilot + [item["task"] for item in items]
    assert all(t.startswith("train/") for t in tasks)
    assert set(families) == set(tasks) and len(families) == 770
    assert all(families[t] == t.split("/")[1] for t in tasks)
    unit_fam = {families[t] for t in units}
    bank_fam = {families[item["task"]] for item in items}
    pilot_fam = {families[t] for t in pilot}
    assert len(unit_fam) == len(units)  # one game per family
    assert not unit_fam & bank_fam and not unit_fam & pilot_fam and not bank_fam & pilot_fam


def test_no_held_out_or_sealed_game_id_anywhere():
    for path in published_files():
        found = {m.group(1) for m in GAME_ID.finditer(path.read_text(encoding="utf-8"))}
        assert found <= {"train"}, (path, found)


def test_no_secret_local_path_or_protected_name():
    for path in published_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        assert not aamr_export.protected_name(path.name, rel.parts[:-1]), rel
        assert not aamr_export.LOCAL_PATH.search(text), rel
        for code, pattern in aamr_export.CONTENT_PATTERNS.items():
            assert not pattern.search(text), (rel, code)
        assert "/home/" not in text and "/mnt/" not in text, rel
