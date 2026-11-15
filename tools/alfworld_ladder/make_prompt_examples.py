"""Write instrument/prompt_examples.txt: the full step-1 prompt of every catalogue arm for one non-test game
(the first pilot game), built by the same functions agent.py uses. Needs the vLLM server (for /tokenize)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent  # noqa: E402

import textworld
import textworld.gym
from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos

root = os.path.expanduser("~/test-a-feasibility/alfworld_data/json_2.1.1")
here = agent.BASE
agent.init(root, os.path.join(here, "data", "bank.jsonl"))
job = json.loads(open(os.path.join(here, "data", "pilot_batch.jsonl")).readline())
task = job["task"]
env = textworld.gym.make(textworld.gym.register_game(
    os.path.join(root, *task.split("/"), "game.tw-pddl"), textworld.EnvInfos(won=True, admissible_commands=True),
    max_episode_steps=50, wrappers=[AlfredDemangler(), AlfredInfos]))
obs, info = env.reset()
obs0 = obs.split("\n\n", 1)[-1] if "Your task is to" in obs.split("\n\n", 1)[-1] else obs
goal = agent.goal_of(obs)
adm = "\n ".join(f"'{s}'" for s in info["admissible_commands"] if s != "help")
base = agent.TEMPLATE_NO_HIS.format(current_observation=obs0, admissible_actions=adm)
out = [f"# Step-1 prompt of each arm for the non-test game {task} (seed 0).",
       "# From step 2 the BASE part switches to TEMPLATE with history; the arm part stays the same.\n"]
for arm in ("none", "placebo", "retrieved_task"):
    block, src = agent.choose_memory(task, goal, arm, 0, agent.BANK)
    suffix = agent.ACTION_INSTR if block is None else agent.MEMORY_WRAPPER.format(retrieved_exp=block)
    mt = 0 if block is None else agent.count_tokens(agent.MEMORY_WRAPPER.format(retrieved_exp=block))
    out.append(f"=================== ARM {arm} | memory_tokens {mt} | memory_sources {src}\n{base + suffix}")
open(os.path.join(here, "instrument", "prompt_examples.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("written", task)
