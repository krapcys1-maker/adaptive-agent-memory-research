"""ALFWorld ladder agent (V6): one batch of (unit, task, arm, seed) jobs -> one JSONL of results.

Runs inside WSL with the ALFWorld venv, against a vLLM OpenAI-compatible server.
Prompt text follows AdaMEM (yunx-z/AdaMEM, Apache-2.0, agent_system/environments/prompts/alfworld.py):
the no-memory arm is exactly AdaMEM's ALFWORLD_TEMPLATE / ALFWORLD_TEMPLATE_NO_HIS; memory arms use
AdaMEM's ALFWORLD_TEMPLATE_DIRECT_ACTION_FROM_RETRIEVAL wrapper in place of the action instruction.

Arms (memory block is chosen once per episode and shown at every step, same position for every arm):
- none:             no block (AdaMEM no-memory prompt).
- placebo:          the wrapper with neutral filler, token-matched to the retrieved_task block
                    of the same (task, seed). Unchanged from V5B.
- retrieved_task:   k=2 expert walkthroughs whose goal text is most similar to this task's goal
                    (content-word Jaccard over the whole bank; ladder rung 4). Unchanged from V5B.
- retrieved_steps:  (V6) the SAME 2 walkthroughs, actions only: observations removed, actions verbatim (numbers and
                    locations kept). The block = two placebo filler items first (the placebo's lines and split), then
                    the two content items last, token-matched to the retrieved_task block of the same (task, seed).
- retrieved_plan:   (V6) the SAME 2 walkthroughs turned by deterministic rules (no model) into an abstract subgoal plan:
                    verbs and object/receptacle classes kept, every number and every room-specific location (where an
                    object or the lamp was found) removed; padded like retrieved_steps.
- mismatched_type, random_same_type: V5B / V3 arms, kept in code, not in the V6 catalogue.
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
    # V4: forbid ending the answer within the first 8 tokens. In V3 the model ended at once (<|im_end|> as
    # first token, p ~ 0.4-0.5) in arms none and retrieved_task but almost never in placebo, so the arms
    # differed in empty answers (0.74 / 0.58 / 0.001 per step). Same for every arm.
    "min_tokens": int(os.environ.get("LADDER_MIN_TOKENS", "8")),
    # V5: the same one-line format reminder at the very end of every arm's prompt (none included), after the
    # memory block. Off reproduces V3/V4 prompts exactly.
    "format_reminder": os.environ.get("LADDER_FORMAT_REMINDER", "1") == "1",
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
FORMAT_REMINDER = "\nReminder: end your answer with exactly one admissible action inside <action> </action> tags.\n"
ARMS = ("none", "placebo", "random_same_type", "retrieved_task", "mismatched_type", "retrieved_steps", "retrieved_plan")
# V6 arms that show the retrieved_task picks in another rendering, padded to the retrieved_task block length
PADDED_ARMS = ("retrieved_steps", "retrieved_plan")
# Positive-control arms (lab POSITIVE_CONTROL_SPEC): never in a program's arm catalogue; only in jobs marked
# {"control": "positive"} and only on pilot games that have a replayed walkthrough in PILOT.
CONTROL_ARMS = ("oracle_self", "scripted_expert", "scripted_null", "oracle_steps")
# oracle_steps (V6 pilot check, not used by the lab's sensitivity step): the oracle block's two walkthroughs rendered
# as retrieved_steps and padded in the same layout, token-matched to the oracle block — shows whether the padded
# layout can carry a large effect
PILOT: dict = {}
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


# ---------------------------------------------------------------------------------------------- V6 renderings
_ACT = {
    "go": re.compile(r"^go to (\S+) \d+$"),
    "take": re.compile(r"^take (\S+) \d+ from (\S+) \d+$"),
    "move": re.compile(r"^move (\S+) \d+ to (\S+) \d+$"),
    "put": re.compile(r"^put (\S+) \d+ in/on (\S+) \d+$"),
    "open": re.compile(r"^open (\S+) \d+$"),
    "close": re.compile(r"^close (\S+) \d+$"),
    "clean": re.compile(r"^clean (\S+) \d+ with (\S+) \d+$"),
    "heat": re.compile(r"^heat (\S+) \d+ with (\S+) \d+$"),
    "cool": re.compile(r"^cool (\S+) \d+ with (\S+) \d+$"),
    "use": re.compile(r"^use (\S+) \d+$"),
}


def parse_act(a: str) -> tuple:
    """(verb, object class, receptacle class) of one walkthrough action; numbers dropped. Unknown form ->
    ("other", text without numbers, None)."""
    for verb, rx in _ACT.items():
        m = rx.match(a.strip())
        if m:
            g = m.groups()
            if verb in ("go", "open", "close", "use"):
                return verb, None, g[0]
            return verb, g[0], g[1]
    return "other", re.sub(r"\s*\d+", "", a).strip(), None


def _a(w: str) -> str:
    return ("an " if w[:1] in "aeiou" else "a ") + w


def plan_steps(actions: list) -> list:
    """Deterministic abstraction of one walkthrough (no model). Kept: the verbs and the object / receptacle classes the
    task needs. Removed: every number, and every room-specific location: where an object was found (the 'go to R'
    and 'open R' before 'take O from R') and where the lamp stands (the 'go to R' before 'use L'). Rules:
    - go to R [open R] take O from R      -> "find a O and take it" ("find another O and take it" for a 2nd O)
    - go to R [open R] use L              -> "find a L and use it"
    - go to R [open R] clean/heat/cool/move/put ... R -> "go to the R" [+ "open the R"], then that action
    - clean/heat/cool O with R            -> "<verb> the O with the R"
    - move O to R / put O in/on R         -> "move the O to the R"
    - open R / close R otherwise          -> "<verb> the R" (an 'open R' right before 'take O from R' is dropped)
    - use L alone                         -> "use the L"
    - go to R followed by anything else   -> dropped (navigation without a recorded purpose)
    - any other form                      -> the action without numbers"""
    p = [parse_act(a) for a in actions]
    out, taken, i = [], set(), 0
    while i < len(p):
        v, o, r = p[i]
        if v == "go":
            j, opened = i + 1, False
            if j < len(p) and p[j][0] == "open" and p[j][2] == r:
                j, opened = j + 1, True
            nv, no, nr = p[j] if j < len(p) else (None, None, None)
            if nv == "take" and nr == r:
                out.append(f"find another {no} and take it" if no in taken else f"find {_a(no)} and take it")
                taken.add(no)
                i = j + 1
                continue
            if nv == "use":
                out.append(f"find {_a(nr)} and use it")
                i = j + 1
                continue
            if nv in ("clean", "heat", "cool", "move", "put") and nr == r:
                out.append(f"go to the {r}")
                if opened:
                    out.append(f"open the {r}")
                i = j
                continue
            i += 1
            continue
        if v == "take":
            out.append(f"find another {o} and take it" if o in taken else f"find {_a(o)} and take it")
            taken.add(o)
        elif v in ("clean", "heat", "cool"):
            out.append(f"{v} the {o} with the {r}")
        elif v in ("move", "put"):
            out.append(f"move the {o} to the {r}")
        elif v in ("open", "close"):
            if not (v == "open" and i + 1 < len(p) and p[i + 1][0] == "take" and p[i + 1][2] == r):
                out.append(f"{v} the {r}")
        elif v == "use":
            out.append(f"use the {r}")
        else:
            out.append(o)
        i += 1
    return out


def render_plan(entry: dict) -> str:
    """retrieved_plan item: the walkthrough's task line and its abstract plan, one subgoal per line, in order. Bullets,
    not numbers, so the item holds no digit at all (contract plan_digit_count = 0)."""
    steps = plan_steps([s["action"] for s in entry["steps"]])
    return "\n".join([f"Task: {goal_of(entry['initial_observation'])}.", "Plan (in order):"]
                     + [f"- {s}" for s in steps])


def render_steps(entry: dict) -> str:
    """retrieved_steps item: the walkthrough's task line and its actions verbatim, in the agent's own history format
    without the observations ([Action i: '<action>'])."""
    return "\n".join([f"Task: {goal_of(entry['initial_observation'])}."]
                     + [f"[Action {i + 1}: '{s['action']}']" for i, s in enumerate(entry["steps"])])


def _filler_lines() -> list:
    filler = open(os.path.join(INSTR, "placebo.txt"), encoding="utf-8").read().strip().split("\n")
    return [l for l in filler if l.strip() and not l.startswith("#")]


def padded_items(contents: list, n_tokens: int) -> list:
    """Filler items FIRST, then the content items unchanged and last. The filler items are built exactly like the
    placebo's two items (the same lines, order and half/half split), with n lines chosen so that the block has the
    token count of the target block (closest from below or above, as placebo_items). No filler line shares an item
    with content (the filler says its slot is empty, which would contradict the content — V6 review F1), and the
    content ends right before the action instruction, as the walkthrough does in retrieved_task."""
    lines = _filler_lines()

    def items(n_lines):
        out = [lines[i % len(lines)] for i in range(n_lines)]
        half = (len(out) + 1) // 2
        fill = [x for x in ("\n".join(out[:half]), "\n".join(out[half:])) if x]
        return fill + list(contents)

    prev, prev_n = items(0), count_tokens(wrap(items(0)))
    if prev_n >= n_tokens:
        return prev
    for n_lines in range(1, 400):
        cur = items(n_lines)
        c = count_tokens(wrap(cur))
        if c >= n_tokens:
            return cur if (c - n_tokens) <= (n_tokens - prev_n) else prev
        prev, prev_n = cur, c
    return prev


# details of the last block choice in this process (read by episode()): the block it is matched to and its content
BLOCK_INFO: dict = {}


_ITEM_TOKENS: dict = {}


def jaccard(goal: str, other: str) -> float:
    a, b = words(goal), words(other)
    return len(a & b) / max(1, len(a | b))


def similarity_metrics(goal: str, sources: list, bank: list) -> dict:
    """top1_similarity: the best goal Jaccard over the whole bank (the same for every arm of a unit; the input
    for a relevance gate). memory_similarity: mean goal Jaccard of the items actually shown (None if none)."""
    by_task = {b["task"]: b for b in bank}
    shown = [jaccard(goal, by_task[t]["goal"]) for t in sources if t in by_task]
    return {"top1_similarity": round(max((jaccard(goal, b["goal"]) for b in bank), default=0.0), 4),
            "memory_similarity": round(sum(shown) / len(shown), 4) if shown else None}


MISMATCH_INFO: dict = {}   # details of the last mismatched_type choice in this process, read by episode()


def mismatched_items(task: str, goal: str, seed: int, bank: list, target: int, exclude=(), tol: float = 0.03):
    """Two real walkthroughs of OTHER task types than the unit: real walkthrough content, unrelated task.
    Candidates: other-type bank entries that are not among `exclude` (the retrieved_task picks of the same task and
    seed), ordered by goal similarity, lowest first. Every pair of the least similar quarter (at least 20 entries)
    is scored by estimated block token count against `target` (the retrieved_task block). If no pair is within
    `tol` (3%), the least similar HALF is searched. The pool never goes beyond the least similar half, so the shown
    tasks stay unrelated; the closest pair found is used even if it is more than 3% off, and the real difference is
    reported. Ties are broken by a sha256 hash of (task, seed, pair). Item token counts are cached per entry."""
    other = sorted((b for b in bank if b["type"] != ttype_of(task) and b["task"] not in set(exclude)),
                   key=lambda b: (jaccard(goal, b["goal"]), b["task"]))
    for b in other:
        if b["task"] not in _ITEM_TOKENS:
            _ITEM_TOKENS[b["task"]] = count_tokens(render(b))
    overhead = count_tokens(wrap(["x", "x"])) - 2 * count_tokens("x")
    best, level = None, None
    for level, size in (("quarter", max(20, len(other) // 4)), ("half", max(20, len(other) // 2))):
        pool = other[:size]
        for i in range(len(pool)):
            for j in range(i + 1, len(pool)):
                a, b = pool[i], pool[j]
                diff = abs(_ITEM_TOKENS[a["task"]] + _ITEM_TOKENS[b["task"]] + overhead - target)
                key = (diff, _h(task, seed, "mis", a["task"], b["task"]))
                if best is None or key < best[0]:
                    best = (key, a, b)
        if best[0][0] <= tol * target:
            break
    picks = [best[1], best[2]]
    block = wrap([render(x) for x in picks])
    MISMATCH_INFO.clear()
    MISMATCH_INFO.update({"mismatched_pool": level,
                          "mismatched_length_diff": round((count_tokens(block) - target) / max(1, target), 4),
                          "overlap_with_retrieved": len({x["task"] for x in picks} & set(exclude))})
    return block, [x["task"] for x in picks]


def choose_memory(task: str, goal: str, arm: str, seed: int, bank: list, control: bool = False):
    k = CFG["k"]
    if arm == "none":
        return None, []
    if arm == "random_same_type":
        pool = [b for b in bank if b["type"] == ttype_of(task)]
        picks = random.Random(_h(task, seed, "rst")).sample(pool, k)
        return wrap([render(b) for b in picks]), [b["task"] for b in picks]
    if arm in ("retrieved_task", "placebo", "mismatched_type", "oracle_self", "oracle_steps") + PADDED_ARMS:
        gw = words(goal)
        rng = random.Random(_h(task, seed, "ret"))
        scored = sorted(bank, key=lambda b: (-len(gw & words(b["goal"])) / max(1, len(gw | words(b["goal"]))),
                                             rng.random()))
        picks = scored[:k]
        if control:
            # positive control: Item 0 = the expert walkthrough of THIS game (same trial), Item 1 = the top
            # retrieved bank item, so the block has the same build as the program's blocks (k = 2). Placebo in a
            # control job is token-matched to this oracle block.
            oracle = [render(PILOT[task]), render(picks[0])]
            BLOCK_INFO.update({"target_block": wrap(oracle)})
            if arm == "oracle_self":
                BLOCK_INFO.update({"content": wrap(oracle)})
                return wrap(oracle), [task, picks[0]["task"]]
            if arm == "oracle_steps":
                contents = [render_steps(PILOT[task]), render_steps(picks[0])]
                BLOCK_INFO.update({"content": wrap(contents), "items": contents})
                return wrap(padded_items(contents, count_tokens(wrap(oracle)))), [task, picks[0]["task"]]
            if arm == "placebo":
                BLOCK_INFO.update({"content": ""})
                return wrap(placebo_items(count_tokens(wrap(oracle)))), []
            raise ValueError(f"arm {arm} is not allowed in a positive-control job")
        if arm in ("oracle_self", "oracle_steps"):
            raise ValueError(f"{arm} exists only in a positive-control job")
        ret_block = wrap([render(b) for b in picks])
        BLOCK_INFO.update({"target_block": ret_block})
        if arm == "retrieved_task":
            BLOCK_INFO.update({"content": ret_block})
            return ret_block, [b["task"] for b in picks]
        if arm == "mismatched_type":
            return mismatched_items(task, goal, seed, bank, count_tokens(ret_block),
                                    exclude=[b["task"] for b in picks])
        if arm in PADDED_ARMS:
            # V6: the SAME picks as retrieved_task in another rendering, padded to the retrieved_task block length
            contents = [(render_steps if arm == "retrieved_steps" else render_plan)(b) for b in picks]
            BLOCK_INFO.update({"content": wrap(contents), "items": contents})
            return wrap(padded_items(contents, count_tokens(ret_block))), [b["task"] for b in picks]
        # placebo: token-matched to the retrieved_task block of the same (task, seed); no source is shown
        n = count_tokens(ret_block)
        BLOCK_INFO.update({"content": ""})
        return wrap(placebo_items(n)), []
    raise ValueError(f"unknown arm {arm}")


class ServerError(RuntimeError):
    """The model server failed on every attempt: the episode must end as an error (the lab retries it),
    never as an unsolved result."""


def chat(prompt: str, seed: int) -> tuple:
    """Returns (text, tokens, empty_retries, finish_reason). Empty answers are retried with a new seed (AdaMEM feasibility
    patch) and counted; if every attempt raised (server down, timeout), raises ServerError."""
    body = {"model": CFG["model"], "messages": [{"role": "user", "content": prompt}],
            "temperature": CFG["temperature"], "max_tokens": CFG["max_tokens"],
            "min_tokens": CFG["min_tokens"], "seed": seed}
    empty, last_exc = 0, None
    for attempt in range(4):
        try:
            req = urllib.request.Request(CFG["base_url"] + "/v1/chat/completions", method="POST",
                                         data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                j = json.load(r)
            text = j["choices"][0]["message"]["content"] or ""
            if text.strip():
                return (text, j["usage"]["prompt_tokens"] + j["usage"]["completion_tokens"], empty,
                        j["choices"][0].get("finish_reason"))
            empty += 1
            body["seed"] = seed + 7919 * (attempt + 1)
        except Exception as e:
            last_exc = e
            time.sleep(5 * (attempt + 1))
    if empty == 0:
        raise ServerError(f"model server failed 4 times: {last_exc!r}"[:200])
    return "", 0, empty, None


def classify_answer(text: str, finish_reason) -> dict:
    """Process counters for one answer, identical for every arm.
    truncated: the server stopped at max_tokens (finish_reason == "length"); behaviour, not format.
    untagged_not_truncated: no complete <action>...</action> pair (missing or malformed tags) in an answer
    that was NOT truncated; this is the format counter."""
    truncated = finish_reason == "length"
    untagged = re.search(r"<action>(.*?)</action>", text, re.S) is None
    return {"truncated": int(truncated), "untagged_not_truncated": int(untagged and not truncated)}


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
    control = job.get("control") == "positive"
    game = os.path.join(DATA_ROOT, *task.split("/"), "game.tw-pddl")
    infos = textworld.EnvInfos(won=True, admissible_commands=True)
    env_id = textworld.gym.register_game(game, infos, max_episode_steps=CFG["max_steps"],
                                         wrappers=[AlfredDemangler(), AlfredInfos])
    env = textworld.gym.make(env_id)
    try:
        obs, info = env.reset()
        obs0 = obs.split("\n\n", 1)[-1] if "Your task is to" in obs.split("\n\n", 1)[-1] else obs
        goal = goal_of(obs)
        MISMATCH_INFO.clear()
        BLOCK_INFO.clear()
        if arm in ("scripted_expert", "scripted_null"):
            return scripted_episode(job, env, obs, goal, t0)
        block, sources = choose_memory(task, goal, arm, seed, BANK, control=control)
        mis = dict(MISMATCH_INFO) if arm == "mismatched_type" else {}
        suffix = ACTION_INSTR if block is None else MEMORY_WRAPPER.format(retrieved_exp=block)
        if CFG["format_reminder"]:
            suffix += FORMAT_REMINDER
        mem_tokens = 0 if block is None else count_tokens(MEMORY_WRAPPER.format(retrieved_exp=block))
        binfo = dict(BLOCK_INFO)
        # V6 block metrics (None for arms without a matched block): length of the matched block (retrieved_task block
        # in program jobs, oracle block in control jobs) in the same wrapper, relative difference of this block, tokens
        # of the non-filler content, and the rule checks of the two re-rendered arms
        tb = binfo.get("target_block")
        matched = (None if tb is None else mem_tokens if tb == block
                   else count_tokens(MEMORY_WRAPPER.format(retrieved_exp=tb)))
        content = binfo.get("content")
        block_metrics = {
            "matched_block_tokens": matched,
            "block_length_diff": None if not matched else round(mem_tokens / matched - 1, 4),
            "content_tokens": None if content is None else (count_tokens(content) if content else 0),
            # counted on the item texts only (the wrapper's own labels "Retrieved Item 0/1" are not content)
            "plan_digit_count": (len(re.findall(r"\d", "".join(binfo["items"]))) if arm == "retrieved_plan"
                                 else None),
            "steps_observation_count": ("".join(binfo["items"]).count("Observation") if arm == "retrieved_steps"
                                        else None),
        }
        hist, tokens, invalid, won, cur = [], 0, 0, False, obs0
        no_tag, bad_samples, empty_retries = 0, [], 0
        truncated, untagged_nt = 0, 0
        wt = [st["action"] for st in PILOT[task]["steps"]] if control and task in PILOT else None
        wt_pos, oracle_hits = 0, 0
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
            text, used, n_empty, finish = chat(p + suffix, _h(job["unit"], arm, seed, step) % (2 ** 31))
            tokens += used
            empty_retries += n_empty
            c = classify_answer(text, finish)
            truncated += c["truncated"]
            untagged_nt += c["untagged_not_truncated"]
            action, ok = parse_action(text, info["admissible_commands"])
            invalid += (not ok)
            if not ok:
                no_tag += ("<action>" not in text)
                if len(bad_samples) < 3:
                    bad_samples.append(text[-160:])
            hist.append((cur, action))
            if wt is not None and wt_pos < len(wt) and action == wt[wt_pos]:
                wt_pos += 1
                oracle_hits += 1
            cur, _r, done, info = env.step(action)
            won = won or bool(info["won"])
            if done:
                break
        extra = {"control": "positive"} if control else {}
        # share of steps whose action equals the next not-yet-matched action of this game's walkthrough
        extra_metrics = ({"oracle_action_match": round(oracle_hits / max(1, len(hist)), 4), "walkthrough_length": len(wt)}
                         if wt is not None else {})
        return {"unit": job["unit"], "arm": arm, "seed": seed, "solved": bool(won), **extra,
                "memory_sources": sources,
                "actions": [a for _, a in hist],  # full action sequence, for CPU replay checks
                "metrics": {"memory_tokens": mem_tokens, "tokens": tokens, "steps": len(hist),
                            "invalid_actions": invalid, "invalid_no_action_tag": no_tag,
                            "truncated": truncated, "untagged_not_truncated": untagged_nt,
                            **similarity_metrics(goal, sources, BANK),
                            "mismatched_pool": mis.get("mismatched_pool"),
                            "mismatched_length_diff": mis.get("mismatched_length_diff"),
                            "overlap_with_retrieved": mis.get("overlap_with_retrieved"),
                            **block_metrics,
                            "invalid_samples": bad_samples, "empty_retries": empty_retries, "seconds": round(time.time() - t0, 1),
                            "temperature": CFG["temperature"], "max_tokens": CFG["max_tokens"],
                            "min_tokens": CFG["min_tokens"], "format_reminder": CFG["format_reminder"], "max_steps": CFG["max_steps"], "model": CFG["model"],
                            **extra_metrics},
                "evidence": (f"goal: {goal} | won: {won} | last: " +
                             " ; ".join(f"{a} -> {' '.join(o.split())[:60]}" for o, a in
                                        list(zip([h[0] for h in hist[1:]] + [cur], [h[1] for h in hist]))[-4:]))[:500]}
    except Exception as e:  # missing result -> the lab retries; never report a fake 'solved'
        return {"unit": job["unit"], "arm": arm, "seed": seed, "error": repr(e)[:300]}
    finally:
        env.close()


def scripted_episode(job: dict, env, obs: str, goal: str, t0: float) -> dict:
    """Rung 0 of the positive control, no model: scripted_expert sends this game's walkthrough actions,
    scripted_null sends 'look' 50 times. Checks the game and the 'solved' scoring."""
    actions = ([st["action"] for st in PILOT[job["task"]]["steps"]] if job["arm"] == "scripted_expert"
               else ["look"] * CFG["max_steps"])
    won, done_steps = False, 0
    for a in actions[:CFG["max_steps"]]:
        _o, _r, done, info = env.step(a)
        done_steps += 1
        won = won or bool(info["won"])
        if done:
            break
    return {"unit": job["unit"], "arm": job["arm"], "seed": int(job["seed"]), "solved": bool(won),
            "control": "positive", "memory_sources": [], "actions": actions[:done_steps],
            "metrics": {"memory_tokens": 0, "steps": done_steps, "scripted": True,
                        "seconds": round(time.time() - t0, 1)},
            "evidence": f"goal: {goal} | won: {won} | scripted {job['arm']}"[:500]}


def init(data_root, bank_path, pilot_path=None):
    global DATA_ROOT, BANK
    DATA_ROOT = data_root
    BANK = [json.loads(l) for l in open(bank_path, encoding="utf-8")]
    for b in BANK:
        b["goal"] = goal_of(b["initial_observation"])
    PILOT.clear()
    if pilot_path and os.path.exists(pilot_path):
        for line in open(pilot_path, encoding="utf-8"):
            if line.strip():
                e = json.loads(line)
                PILOT[e["task"]] = e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", default=os.path.expanduser("~/test-a-feasibility/alfworld_data/json_2.1.1"))
    ap.add_argument("--bank", default=os.path.join(BASE, "data", "bank.jsonl"))
    ap.add_argument("--parallel", type=int, default=24)
    ap.add_argument("--pilot-walkthroughs", default=os.path.join(BASE, "data", "pilot_walkthroughs.jsonl"),
                    help="replayed walkthroughs of the pilot games (positive control only)")
    ap.add_argument("--min-tokens", type=int, default=None,
                    help="default 8; 0 reproduces the V3 empty-answer artefact (answers that end at once)")
    a = ap.parse_args()
    if a.min_tokens is not None:
        CFG["min_tokens"] = a.min_tokens
        os.environ["LADDER_MIN_TOKENS"] = str(a.min_tokens)  # also for spawned workers
    jobs = [json.loads(l) for l in open(a.batch, encoding="utf-8") if l.strip()]
    pilot_tasks = set()
    if os.path.exists(a.pilot_walkthroughs):
        pilot_tasks = {json.loads(x)["task"] for x in open(a.pilot_walkthroughs, encoding="utf-8") if x.strip()}
    for j in jobs:
        if j.get("control") == "positive":
            if j["arm"] not in CONTROL_ARMS + ("placebo",):
                sys.exit(f"arm {j['arm']} is not allowed in a positive-control job")
            if j["task"] not in pilot_tasks:
                sys.exit(f"positive-control job on a game without a pilot walkthrough: {j['task']}")
        elif j["arm"] not in ARMS:
            sys.exit(f"unknown arm {j['arm']}; control arms need control=positive")
        if j["task"].split("/")[0] not in ("valid_seen", "train"):
            sys.exit(f"refusing task outside valid_seen/train (valid_unseen is never used): {j['task']}")
    with Pool(a.parallel, initializer=init, initargs=(a.data_root, a.bank, a.pilot_walkthroughs)) as p, \
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
