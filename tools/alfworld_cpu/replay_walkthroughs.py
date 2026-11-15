"""Replay ALFWorld expert walkthroughs on the CPU and save them as trajectories.

Every ALFWorld game file carries a planner walkthrough in the action syntax of the
installed ALFWorld version. Replaying it in the text environment gives a full
trajectory with observations, without a GPU and without a language model. The result
can serve as an expert bank (ladder rung 1) or as a pool for random-bank controls.

Caveat: the planner knows where every object is, so walkthroughs go straight to the
right place and never show searching. They are not a substitute for a bank of the
agent's own successful runs.

Usage (inside the environment where `alfworld` and `textworld` are installed):
    python replay_walkthroughs.py --data-root <ALFWORLD_DATA>/json_2.1.1 --split train \
        --n 30 --seed 0 --out walkthroughs.jsonl
    (--n 0 replays every game in the split)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import time

import textworld
import textworld.gym
from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos


def replay(game_file: str, max_steps: int) -> dict:
    infos = textworld.EnvInfos(won=True, admissible_commands=True, extras=["walkthrough"])
    env_id = textworld.gym.register_game(game_file, infos, max_episode_steps=max_steps,
                                         wrappers=[AlfredDemangler(), AlfredInfos])
    env = textworld.gym.make(env_id)
    try:
        obs, info = env.reset()
        steps, all_admissible, won = [], True, False
        for action in info["extra.walkthrough"]:
            admissible = action in info["admissible_commands"]
            all_admissible &= admissible
            obs_next, _score, done, info = env.step(action)
            steps.append({"action": action, "admissible": admissible, "observation": obs_next})
            won = won or bool(info["won"])
            if done:
                break
        return {"initial_observation": obs, "steps": steps, "won": won, "all_admissible": all_admissible}
    finally:
        env.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--split", default="train")
    ap.add_argument("--n", type=int, default=30, help="number of games to sample; 0 = all")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-steps", type=int, default=60)
    ap.add_argument("--out", default=None, help="JSONL file, one trajectory per line")
    args = ap.parse_args()
    games = sorted(glob.glob(os.path.join(args.data_root, args.split, "*", "*", "game.tw-pddl")))
    if args.n:
        games = random.Random(args.seed).sample(games, min(args.n, len(games)))
    t0, won, adm = time.time(), 0, 0
    out = open(args.out, "w", encoding="utf-8") if args.out else None
    try:
        for g in games:
            r = replay(g, args.max_steps)
            r["game"] = os.path.relpath(os.path.dirname(g), os.path.join(args.data_root, args.split))
            won += r["won"]
            adm += r["all_admissible"]
            if out:
                out.write(json.dumps(r) + "\n")
    finally:
        if out:
            out.close()
    dt = time.time() - t0
    print(f"games {len(games)} | won {won} | all actions admissible {adm} | {dt:.1f}s ({dt / max(1, len(games)):.2f}s per game)")


if __name__ == "__main__":
    main()
