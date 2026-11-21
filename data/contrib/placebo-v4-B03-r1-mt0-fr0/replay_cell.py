import json
import os
import sys
from pathlib import Path

import textworld
import textworld.gym
from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos


def replay(game, actions):
    env_id = textworld.gym.register_game(
        str(game), textworld.EnvInfos(won=True, admissible_commands=True),
        max_episode_steps=50, wrappers=[AlfredDemangler(), AlfredInfos],
    )
    env = textworld.gym.make(env_id)
    won = False
    try:
        env.reset()
        for index, action in enumerate(actions, 1):
            _, _, done, info = env.step(action)
            won = won or bool(info["won"])
            if done:
                return won, index
        return won, len(actions)
    finally:
        env.close()


def main(cell):
    game_root = Path(os.environ["ALFWORLD_DATA"]) / "json_2.1.1"
    jobs = [json.loads(line) for line in (cell / "batch.jsonl").read_text().splitlines()]
    rows = [json.loads(line) for line in (cell / "records.jsonl").read_text().splitlines()]
    task_by_key = {(job["unit"], job["arm"], job["seed"]): job["task"] for job in jobs}
    if not rows:
        raise SystemExit("No scored rows to replay")
    for row in rows:
        key = (row["unit"], row["arm"], row["seed"])
        won, steps = replay(game_root / task_by_key[key] / "game.tw-pddl", row["actions"])
        expected = (bool(row["solved"]), row["metrics"]["steps"])
        if (won, steps) != expected:
            raise SystemExit(f"{key}: replay {(won, steps)} != recorded {expected}")
    print(f"Replayed {len(rows)}/{len(jobs)} episode(s); solve flags and step counts matched")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
