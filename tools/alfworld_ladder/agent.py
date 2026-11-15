"""ALFWorld ladder agent: one batch of (unit, task, arm, seed) jobs -> one JSONL of results.

Runs inside WSL with the ALFWorld venv, against a vLLM OpenAI-compatible server.
Prompt text follows AdaMEM (yunx-z/AdaMEM, Apache-2.0, agent_system/environments/prompts/alfworld.py):
the no-memory arm is exactly AdaMEM's ALFWORLD_TEMPLATE / ALFWORLD_TEMPLATE_NO_HIS; memory arms use
AdaMEM's ALFWORLD_TEMPLATE_DIRECT_ACTION_FROM_RETRIEVAL wrapper in place of the action instruction.

Arms (memory block is chosen once per episode and shown at every step, same position for every arm):
- none:             no block (AdaMEM no-memory prompt).
- placebo:          the wrapper with neutral filler, token-matched to the retrieved_task block
                    of the same (task, seed).
- random_same_type: k=2 expert walkthroughs drawn at random from bank entries of the same task type
                    (ladder rung 3, the TRAD "Random" control).
- retrieved_task:   k=2 expert walkthroughs whose goal text is most similar to this task's goal
                    (content-word Jaccard over the whole bank; ladder rung 4).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.request
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
# layout: <approach>/src/agent.py + <approach>/instrument + <approach>/data, or everything in one folder
BASE = os.path.dirname(HERE) if os.path.isdir(os.path.join(os.path.dirname(HERE), "instrument")) else HERE
INSTR = os.path.join(BASE, "instrument")

CFG = {
    "base_url": os.environ.get("LADDER_VLLM", "http://127.0.0.1:8001"),
    "model": os.environ.get("LADDER_MODEL", "Qwen/Qwen3-4B-Instruct-2507-FP8"),
    "temperature": 0.7,
    "max_tokens": 2048,
    "max_steps": 50,
    "history_length": 50,
    "k": 2,
    "obs_chars_in_memory": 240,
}

TEMPLATE_NO_HIS = """
You are an expert agent operating in the ALFRED Embodied Environment.
Your current observation is: {current_observation}
Your admissible actions of the current situation are: [{admissible_actions}].
"""
TEMPLATE = """
You are an expert agent operating in the ALFRED Embodied Environment. Your task is to: {task_description}
Prior to this step, you have already taken {step_count} step(s). Below are the most recent {history_length} observations and the corresponding actions you took: {action_history}
You are now at step {current_step} and your current observation is: {current_observation}
Your admissible actions of the current situation are: [{admissible_actions}].
"""
ACTION_INSTR = """
Now it's your turn to take an action.
You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.
Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags.
"""
MEMORY_WRAPPER = """
Here are some task solving trajectories on similar tasks:

Retrieved Experiences:
{retrieved_exp}

Now it's your turn to take an action.
You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.
Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags.
"""
ARMS = ("none", "placebo", "random_same_type", "retrieved_task")
STOP = set("a an the some put in on to and of with it then your is".split())


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def goal_of(obs: str) -> str:
    i = obs.find("Your task is to: ")
    return obs[i + len("Your task is to: "):].strip().rstrip(".") if i >= 0 else ""


def words(g: str) -> set:
    return {w for w in re.findall(r"[a-z]+", g.lower()) if w not in STOP}


def ttype_of(task: str) -> str:
    return task.split("/")[1].split("-")[0]


def render(entry: dict) -> str:
    """One bank walkthrough in exactly the format the agent sees its own history in the prompt
    ([Observation i: '...', Action i: '...'], as AdaMEM), so memory and placebo differ in content, not in format.
    The first observation is the room description without the task line; observations are cut to 240 chars."""
    def cut(o):
        return " ".join(o.split())[: CFG["obs_chars_in_memory"]]
    room = [r for r in entry["initial_observation"].split("\n\n")
            if r.strip() and "Welcome to TextWorld" not in r and "Your task is to" not in r]
    obs = [cut(room[0]) if room else ""] + [cut(s["observation"]) for s in entry["steps"]]
    lines = [f"Task: {goal_of(entry['initial_observation'])}."]
    for i, s in enumerate(entry["steps"]):
        lines.append(f"[Observation {i + 1}: '{obs[i]}', Action {i + 1}: '{s['action']}']")
    lines.append(f"Final observation: '{obs[-1]}'")
    return "\n".join(lines)


def wrap(items: list) -> str:
    return "\n\n".join(f"Retrieved Item {i}:\n{c}" for i, c in enumerate(items))


def count_tokens(text: str) -> int:
    req = urllib.request.Request(CFG["base_url"] + "/tokenize", method="POST",
                                 data=json.dumps({"model": CFG["model"], "prompt": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(json.load(r)["count"])


def placebo_items(n_tokens: int) -> list:
    """Neutral filler with the same wrapper and item layout, cut to n_tokens."""
    filler = open(os.path.join(INSTR, "placebo.txt"), encoding="utf-8").read().strip().split("\n")
    lines = [l for l in filler if l.strip() and not l.startswith("#")]

    def items(n_lines):
        out = [lines[i % len(lines)] for i in range(n_lines)]
        half = (len(out) + 1) // 2
        return ["\n".join(out[:half]), "\n".join(out[half:])]

    prev, prev_n = items(1), count_tokens(wrap(items(1)))
    for n_lines in range(2, 400):
        cur = items(n_lines)
        c = count_tokens(wrap(cur))
        if c >= n_tokens:
            return cur if (c - n_tokens) <= (n_tokens - prev_n) else prev
        prev, prev_n = cur, c
    return prev


def choose_memory(task: str, goal: str, arm: str, seed: int, bank: list):
    k = CFG["k"]
    if arm == "none":
        return None, []
    if arm == "random_same_type":
        pool = [b for b in bank if b["type"] == ttype_of(task)]
        picks = random.Random(_h(task, seed, "rst")).sample(pool, k)
        return wrap([render(b) for b in picks]), [b["task"] for b in picks]
    if arm in ("retrieved_task", "placebo"):
        gw = words(goal)
        rng = random.Random(_h(task, seed, "ret"))
        scored = sorted(bank, key=lambda b: (-len(gw & words(b["goal"])) / max(1, len(gw | words(b["goal"]))),
                                             rng.random()))
        picks = scored[:k]
        if arm == "retrieved_task":
            return wrap([render(b) for b in picks]), [b["task"] for b in picks]
        # placebo: token-matched to the retrieved_task block of the same (task, seed); no source is shown
        n = count_tokens(wrap([render(b) for b in picks]))
        return wrap(placebo_items(n)), []
    raise ValueError(f"unknown arm {arm}")


def chat(prompt: str, seed: int) -> tuple:
    body = {"model": CFG["model"], "messages": [{"role": "user", "content": prompt}],
            "temperature": CFG["temperature"], "max_tokens": CFG["max_tokens"], "seed": seed}
    for attempt in range(4):
        try:
            req = urllib.request.Request(CFG["base_url"] + "/v1/chat/completions", method="POST",
                                         data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                j = json.load(r)
            text = j["choices"][0]["message"]["content"] or ""
            if text.strip():
                return text, j["usage"]["prompt_tokens"] + j["usage"]["completion_tokens"]
            body["seed"] = seed + 7919 * (attempt + 1)  # retry empty answers (AdaMEM feasibility patch)
        except Exception:
            time.sleep(5 * (attempt + 1))
    return "", 0


def parse_action(text: str, admissible: list) -> tuple:
    m = re.findall(r"<action>(.*?)</action>", text, re.S)
    a = m[-1].strip().strip("'\"").strip() if m else ""
    low = {x.lower(): x for x in admissible}
    if a.lower() in low:
        return low[a.lower()], True
    return (a if a else "None"), False


def episode(job: dict) -> dict:
    import textworld
    import textworld.gym
    from alfworld.agents.environment.alfred_tw_env import AlfredDemangler, AlfredInfos
    t0 = time.time()
    task, arm, seed = job["task"], job["arm"], int(job["seed"])
    game = os.path.join(DATA_ROOT, *task.split("/"), "game.tw-pddl")
    infos = textworld.EnvInfos(won=True, admissible_commands=True)
    env_id = textworld.gym.register_game(game, infos, max_episode_steps=CFG["max_steps"],
                                         wrappers=[AlfredDemangler(), AlfredInfos])
    env = textworld.gym.make(env_id)
    try:
        obs, info = env.reset()
        obs0 = obs.split("\n\n", 1)[-1] if "Your task is to" in obs.split("\n\n", 1)[-1] else obs
        goal = goal_of(obs)
        block, sources = choose_memory(task, goal, arm, seed, BANK)
        suffix = ACTION_INSTR if block is None else MEMORY_WRAPPER.format(retrieved_exp=block)
        mem_tokens = 0 if block is None else count_tokens(MEMORY_WRAPPER.format(retrieved_exp=block))
        hist, tokens, invalid, won, cur = [], 0, 0, False, obs0
        no_tag, bad_samples = 0, []
        limit = float(os.environ.get("LADDER_EPISODE_TIMEOUT", "5400"))
        for step in range(CFG["max_steps"]):
            if time.time() - t0 > limit:
                raise TimeoutError(f"episode over {limit:.0f} s at step {step}")
            adm = "\n ".join(f"'{s}'" for s in info["admissible_commands"] if s != "help")
            if step == 0:
                p = TEMPLATE_NO_HIS.format(current_observation=cur, admissible_actions=adm)
            else:
                recent = hist[-CFG["history_length"]:]
                start = len(hist) - len(recent)
                ah = "\n".join(f"[Observation {start + j + 1}: '{o}', Action {start + j + 1}: '{a}']"
                               for j, (o, a) in enumerate(recent))
                p = TEMPLATE.format(task_description=goal, step_count=len(hist), history_length=len(recent),
                                    action_history=ah, current_step=len(hist) + 1, current_observation=cur,
                                    admissible_actions=adm)
            text, used = chat(p + suffix, _h(job["unit"], arm, seed, step) % (2 ** 31))
            tokens += used
            action, ok = parse_action(text, info["admissible_commands"])
            invalid += (not ok)
            if not ok:
                no_tag += ("<action>" not in text)
                if len(bad_samples) < 3:
                    bad_samples.append(text[-160:])
            hist.append((cur, action))
            cur, _r, done, info = env.step(action)
            won = won or bool(info["won"])
            if done:
                break
        return {"unit": job["unit"], "arm": arm, "seed": seed, "solved": bool(won),
                "memory_sources": sources,
                "metrics": {"memory_tokens": mem_tokens, "tokens": tokens, "steps": len(hist),
                            "invalid_actions": invalid, "invalid_no_action_tag": no_tag,
                            "invalid_samples": bad_samples, "seconds": round(time.time() - t0, 1),
                            "temperature": CFG["temperature"], "max_tokens": CFG["max_tokens"],
                            "max_steps": CFG["max_steps"], "model": CFG["model"]},
                "evidence": (f"goal: {goal} | won: {won} | last: " +
                             " ; ".join(f"{a} -> {' '.join(o.split())[:60]}" for o, a in
                                        list(zip([h[0] for h in hist[1:]] + [cur], [h[1] for h in hist]))[-4:]))[:500]}
    except Exception as e:  # missing result -> the lab retries; never report a fake 'solved'
        return {"unit": job["unit"], "arm": arm, "seed": seed, "error": repr(e)[:300]}
    finally:
        env.close()


def init(data_root, bank_path):
    global DATA_ROOT, BANK
    DATA_ROOT = data_root
    BANK = [json.loads(l) for l in open(bank_path, encoding="utf-8")]
    for b in BANK:
        b["goal"] = goal_of(b["initial_observation"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", default=os.path.expanduser("~/test-a-feasibility/alfworld_data/json_2.1.1"))
    ap.add_argument("--bank", default=os.path.join(BASE, "data", "bank.jsonl"))
    ap.add_argument("--parallel", type=int, default=24)
    a = ap.parse_args()
    jobs = [json.loads(l) for l in open(a.batch, encoding="utf-8") if l.strip()]
    for j in jobs:
        if j["arm"] not in ARMS:
            sys.exit(f"unknown arm {j['arm']}")
        if j["task"].split("/")[0] not in ("valid_seen", "train"):
            sys.exit(f"refusing task outside valid_seen/train (valid_unseen is never used): {j['task']}")
    with Pool(a.parallel, initializer=init, initargs=(a.data_root, a.bank)) as p, \
            open(a.out, "a", encoding="utf-8") as f:
        for r in p.imap_unordered(episode, jobs):
            if "error" in r:
                print("episode error", r, file=sys.stderr, flush=True)
                continue
            f.write(json.dumps(r) + "\n")
            f.flush()
            os.fsync(f.fileno())


if __name__ == "__main__":
    main()
