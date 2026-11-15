"""Build the task list, the family map and the expert bank for the ALFWorld ladder approach.

Runs inside WSL with the ALFWorld venv:
    .venv/bin/python build_data.py --data-root ~/test-a-feasibility/alfworld_data/json_2.1.1 \
        --out data --per-type 120 --workers 6

Outputs:
- units.json: the 140 valid_seen games, ids "valid_seen/<task dir>/<trial>", sorted.
- bank.jsonl: replayed planner walkthroughs of a seeded sample of train games (per-type quota),
  with every family that also occurs among the units removed.
- families.json: {task id: family} for every unit and every bank entry. Family = the task directory
  (task type, objects, receptacle, scene), so two trials of the same task are one family.
- data_manifest.json: counts and seeds.
valid_unseen is never read.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
from multiprocessing import Pool

TYPES = ["pick_and_place_simple", "look_at_obj_in_light", "pick_clean_then_place_in_recep",
         "pick_heat_then_place_in_recep", "pick_cool_then_place_in_recep", "pick_two_obj_and_place"]


def task_id(split: str, game_dir: str, root: str) -> str:
    return split + "/" + os.path.relpath(game_dir, os.path.join(root, split)).replace(os.sep, "/")


def family_of(tid: str) -> str:
    return tid.split("/")[1]


def ttype_of(tid: str) -> str:
    return family_of(tid).split("-")[0]


def replay(args):
    game_file, tid = args
    import textworld
    import textworld.gym
    from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos
    infos = textworld.EnvInfos(won=True, admissible_commands=True, extras=["walkthrough"])
    env_id = textworld.gym.register_game(game_file, infos, max_episode_steps=60,
                                         wrappers=[AlfredDemangler(), AlfredInfos])
    env = textworld.gym.make(env_id)
    try:
        obs, info = env.reset()
        steps, won, adm = [], False, True
        for a in info["extra.walkthrough"]:
            adm &= a in info["admissible_commands"]
            o, _, done, info = env.step(a)
            steps.append({"action": a, "observation": o})
            won = won or bool(info["won"])
            if done:
                break
        return {"task": tid, "family": family_of(tid), "type": ttype_of(tid),
                "initial_observation": obs, "steps": steps, "won": won, "all_admissible": adm}
    finally:
        env.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--per-type", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    root = os.path.expanduser(a.data_root)

    units = sorted(task_id("valid_seen", os.path.dirname(g), root)
                   for g in glob.glob(os.path.join(root, "valid_seen", "*", "*", "game.tw-pddl")))
    unit_fams = {family_of(u) for u in units}

    train = sorted(task_id("train", os.path.dirname(g), root)
                   for g in glob.glob(os.path.join(root, "train", "*", "*", "game.tw-pddl")))
    excluded_twins = sorted({family_of(t) for t in train} & unit_fams)
    rng = random.Random(a.seed)
    chosen = []
    for ty in TYPES:
        pool = [t for t in train if ttype_of(t) == ty and family_of(t) not in unit_fams]
        # at most one trial per family, so the bank is not dominated by a few tasks
        seen, uniq = set(), []
        for t in rng.sample(pool, len(pool)):
            if family_of(t) not in seen:
                seen.add(family_of(t))
                uniq.append(t)
        chosen += uniq[: a.per_type]

    jobs = [(os.path.join(root, *t.split("/"), "game.tw-pddl"), t) for t in chosen]
    with Pool(a.workers) as p:
        bank = p.map(replay, jobs, chunksize=4)
    bad = [b["task"] for b in bank if not (b["won"] and b["all_admissible"])]
    bank = [b for b in bank if b["won"] and b["all_admissible"]]

    os.makedirs(a.out, exist_ok=True)
    json.dump(units, open(os.path.join(a.out, "units.json"), "w"), indent=0)
    with open(os.path.join(a.out, "bank.jsonl"), "w", encoding="utf-8") as f:
        for b in bank:
            f.write(json.dumps(b) + "\n")
    fams = {u: family_of(u) for u in units}
    fams.update({b["task"]: b["family"] for b in bank})
    json.dump(fams, open(os.path.join(a.out, "families.json"), "w"), indent=0, sort_keys=True)
    from collections import Counter
    man = {"units": len(units), "unit_types": Counter(ttype_of(u) for u in units),
           "bank": len(bank), "bank_types": Counter(b["type"] for b in bank),
           "bank_replay_failed": bad, "train_families_also_in_units_excluded": len(excluded_twins),
           "per_type": a.per_type, "seed": a.seed, "valid_unseen_read": False}
    json.dump(man, open(os.path.join(a.out, "data_manifest.json"), "w"), indent=1)
    print(json.dumps(man))


if __name__ == "__main__":
    main()
