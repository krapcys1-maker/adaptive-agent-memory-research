"""Write the public synthetic fixture that pins the retriever and the formatter in CI.

The bank is made up (ALFWorld-like train games, no real game data). The expected picks and block digests come from
the V5B instrument code (``tools/alfworld_ladder/agent.py`` at the SHA-256 of the V5B program pin), not from
the package, so the fixture is an independent record of the measured rule. Queries are built to hit ties, a goal
with no content word in common with the bank, punctuation and case. Cases with a family exclusion have no instrument
counterpart (the V5B bank and units share no family); their expectation is derived from the no-exclusion picks by
the documented rule: the tie-break numbers are drawn before the exclusion.

Run from the repository root:  python tools/experience_memory/parity/make_synthetic_fixture.py
"""
from __future__ import annotations

import hashlib
import random
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check_v5b_parity import PUBLIC_AGENT, V5B_PINS, load_reference, pinned_public_source  # noqa: E402

OUT = HERE.parents[2] / "tests" / "fixtures" / "experience-memory-synthetic"


def game(type_, obj, recep, scene, goal, steps):
    task = f"train/{type_}-{obj}-None-{recep}-{scene}/trial_T0000_{scene}"
    room = f"You are in the middle of a room. Looking quickly around you, you see a {recep.lower()} 1, a shelf 1, and a drawer 1."
    return {"task": task, "family": task.split("/")[1], "type": type_,
            "initial_observation": f"-= Welcome to TextWorld, ALFRED! =-\n\n{room}\n\nYour task is to: {goal}.",
            "steps": [{"action": a, "observation": o} for a, o in steps], "won": True, "all_admissible": True}


BANK = [
    game("pick_and_place_simple", "CD", "Shelf", 301, "put a cd in shelf",
         [("go to drawer 1", "You arrive at drawer 1. The drawer 1 is closed."),
          ("open drawer 1", "You open the drawer 1. The drawer 1 is open. In it, you see a cd 1."),
          ("take cd 1 from drawer 1", "You pick up the cd 1 from the drawer 1."),
          ("go to shelf 1", "You arrive at shelf 1. On the shelf 1, you see nothing."),
          ("move cd 1 to shelf 1", "You move the cd 1 to the shelf 1.")]),
    game("pick_and_place_simple", "CD", "Shelf", 302, "put some cd on shelf",
         [("go to shelf 1", "You arrive at shelf 1.   On the shelf 1,\n you see a cd 2."),
          ("take cd 2 from shelf 1", "You pick up the cd 2 from the shelf 1."),
          ("move cd 2 to shelf 1", "You move the cd 2 to the shelf 1.")]),
    game("pick_and_place_simple", "Pen", "Drawer", 303, "put a pen in drawer",
         [("go to shelf 1", "You arrive at shelf 1. On the shelf 1, you see a pen 1."),
          ("take pen 1 from shelf 1", "You pick up the pen 1 from the shelf 1."),
          ("go to drawer 1", "You arrive at drawer 1. The drawer 1 is open. " + "In it you see nothing. " * 20),
          ("move pen 1 to drawer 1", "You move the pen 1 to the drawer 1.")]),
    game("pick_heat_then_place_in_recep", "Egg", "Fridge", 304, "put a hot egg in fridge",
         [("go to microwave 1", "You arrive at microwave 1."),
          ("heat egg 1 with microwave 1", "You heat the egg 1 using the microwave 1."),
          ("go to fridge 1", "You arrive at fridge 1."),
          ("move egg 1 to fridge 1", "You move the egg 1 to the fridge 1.")]),
    game("pick_heat_then_place_in_recep", "Egg", "CounterTop", 305, "heat some egg and put it in countertop",
         [("go to countertop 1", "You arrive at countertop 1. On it you see an egg 1."),
          ("take egg 1 from countertop 1", "You pick up the egg 1 from the countertop 1."),
          ("heat egg 1 with microwave 1", "You heat the egg 1 using the microwave 1."),
          ("move egg 1 to countertop 1", "You move the egg 1 to the countertop 1.")]),
    game("pick_cool_then_place_in_recep", "Apple", "Fridge", 306, "put a cool apple in fridge",
         [("go to fridge 1", "You arrive at fridge 1."),
          ("cool apple 1 with fridge 1", "You cool the apple 1 using the fridge 1."),
          ("move apple 1 to fridge 1", "You move the apple 1 to the fridge 1.")]),
    game("pick_clean_then_place_in_recep", "Mug", "Shelf", 307, "clean some mug and put it in shelf",
         [("go to sinkbasin 1", "You arrive at sinkbasin 1."),
          ("clean mug 1 with sinkbasin 1", "You clean the mug 1 using the sinkbasin 1."),
          ("move mug 1 to shelf 1", "You move the mug 1 to the shelf 1.")]),
    game("look_at_obj_in_light", "CD", "DeskLamp", 308, "look at cd under the desklamp",
         [("go to desk 1", "You arrive at desk 1. On the desk 1, you see a cd 3, and a desklamp 1."),
          ("take cd 3 from desk 1", "You pick up the cd 3 from the desk 1."),
          ("use desklamp 1", "You turn on the desklamp 1.")]),
    game("pick_two_obj_and_place", "CD", "Shelf", 309, "put two cd in shelf", []),
]

QUERIES = [
    # (query_id, goal, family or None)
    ("train/pick_and_place_simple-CD-None-Shelf-401/trial_q1", "put a cd in shelf", None),
    ("train/pick_and_place_simple-CD-None-Shelf-402/trial_q2", "Put a CD on the shelf.", None),
    ("train/pick_heat_then_place_in_recep-Egg-None-Fridge-403/trial_q3", "put a hot egg in fridge", None),
    ("train/pick_cool_then_place_in_recep-Egg-None-Fridge-404/trial_q4", "put a cool egg in fridge", None),
    ("train/pick_two_obj_and_place-Pen-None-Drawer-405/trial_q5", "put two pen in drawer", None),
    ("train/look_at_obj_in_light-Book-None-DeskLamp-406/trial_q6", "examine the book with the desklamp", None),
    ("train/pick_and_place_simple-Vase-None-Safe-407/trial_q7", "put a vase in safe", None),
    ("train/pick_clean_then_place_in_recep-Mug-None-Shelf-408/trial_q8", "put a clean mug in shelf", None),
]
SEEDS = (0, 1, 6)
# family-exclusion cases: (query index, seed, excluded family)
EXCLUSIONS = [(0, 0, "pick_and_place_simple-CD-None-Shelf-301"), (2, 1, "pick_heat_then_place_in_recep-Egg-None-Fridge-304")]


def main() -> int:
    source, origin = pinned_public_source()
    if source is None:
        print("refusing: the pinned V5B instrument is neither in the working copy nor in git history")
        return 1
    ref = load_reference(PUBLIC_AGENT, source)
    bank = json.loads(json.dumps(BANK))
    for b in bank:
        b["goal"] = ref.goal_of(b["initial_observation"])
    cases = []
    for qi, (qid, goal, fam) in enumerate(QUERIES):
        for seed in SEEDS:
            gw = ref.words(goal)
            rng = random.Random(ref._h(qid, seed, "ret"))
            full = [b["task"] for b in sorted(bank, key=lambda b: (-len(gw & ref.words(b["goal"])) / max(1, len(gw | ref.words(b["goal"]))), rng.random()))]
            block, sources = ref.choose_memory(qid, goal, "retrieved_task", seed, bank)
            assert sources == full[:2]
            cases.append({"query_id": qid, "goal": goal, "query_family": fam, "seed": seed, "expected_items": sources,
                          "expected_scores": [round(ref.jaccard(goal, ref.goal_of(next(b for b in bank if b["task"] == t)["initial_observation"])), 6) for t in sources],
                          "expected_block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                          "full_order": full})
            for eqi, eseed, efam in EXCLUSIONS:
                if (eqi, eseed) == (qi, seed):
                    kept = [t for t in full if t.split("/")[1] != efam]
                    cases.append({"query_id": qid, "goal": goal, "query_family": efam, "seed": seed,
                                  "expected_items": kept[:2], "expected_excluded": [t for t in full if t.split("/")[1] == efam],
                                  "derived_from_instrument_order": True})
    first = cases[0]
    block0, _ = ref.choose_memory(first["query_id"], first["goal"], "retrieved_task", first["seed"], bank)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "bank.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for b in BANK:
            f.write(json.dumps(b, ensure_ascii=False) + "\n")
    (OUT / "expected.json").write_text(json.dumps({
        "generated_by": "tools/experience_memory/parity/make_synthetic_fixture.py",
        "reference": "tools/alfworld_ladder/agent.py (choose_memory, arm retrieved_task)",
        "reference_sha256": V5B_PINS["src/agent.py"], "k": 2, "cases": cases}, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    (OUT / "expected_block_0.txt").write_text(block0, encoding="utf-8", newline="\n")
    print(f"wrote {len(cases)} cases to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
