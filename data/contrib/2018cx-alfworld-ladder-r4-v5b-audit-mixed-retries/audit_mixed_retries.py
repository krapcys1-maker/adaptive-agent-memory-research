"""Replay mixed empty completions and transport failures on the pinned V5B runner."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "tools/alfworld_ladder/agent.py"
RUNNER_PIN = "c5c5eea0545eba11fbd27435296a80bb88e0c31e707762862f98417caba9636a"
CSV = ROOT / "data/lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv"


class OneStepGame:
    def __init__(self):
        self.actions = []

    def reset(self):
        return "Your task is to go to the shelf.", {"admissible_commands": ["go to shelf 1"]}

    def step(self, action):
        self.actions.append(action)
        return "Game ended.", 0, True, {"won": action == "go to shelf 1"}

    def close(self):
        pass


def run_case(agent, replies):
    game = OneStepGame()
    gym = SimpleNamespace(register_game=lambda *a, **kw: "stub", make=lambda env_id: game)
    modules = {
        "textworld": SimpleNamespace(EnvInfos=lambda **kw: kw, gym=gym),
        "textworld.gym": gym,
        "alfworld.agents.environment.alfred_tw_env": SimpleNamespace(
            AlfredDemangler=object, AlfredInfos=object
        ),
    }
    responses = iter(replies)
    requests = []

    def urlopen(request, timeout):
        if not request.full_url.endswith("/v1/chat/completions"):
            raise AssertionError(f"Unexpected request: {request.full_url}")
        reply = next(responses)
        requests.append(reply)
        if reply == "error":
            raise URLError("synthetic transport failure")
        content = "<action>go to shelf 1</action>" if reply == "valid" else ""
        payload = {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 0 if not content else 7},
        }
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    job = {"unit": "synthetic", "task": "train/pick_and_place_simple-example/trial",
           "arm": "none", "seed": 0}
    with (
        patch.dict(sys.modules, modules),
        patch.multiple(agent, DATA_ROOT=".", BANK=[], create=True),
        patch.object(agent.urllib.request, "urlopen", side_effect=urlopen),
        patch.object(agent.time, "sleep"),
    ):
        result = agent.episode(job)
    if tuple(requests) != replies:
        raise AssertionError(f"Unexpected request trace: {requests}")
    metrics = result.get("metrics", {})
    summary = {
        "actions": game.actions,
        "solved": result.get("solved"),
        "error": "error" in result,
        "empty_retries": metrics.get("empty_retries"),
        "untagged_not_truncated": metrics.get("untagged_not_truncated"),
        "invalid_actions": metrics.get("invalid_actions"),
    }
    print(f"{', '.join(replies)} -> {summary}")
    return summary


def main():
    if hashlib.sha256(RUNNER.read_bytes()).hexdigest() != RUNNER_PIN:
        raise SystemExit("Runner does not match the V5B pin.")
    spec = importlib.util.spec_from_file_location("v5b_agent", RUNNER)
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)

    def unsolved(empty_count):
        return {"actions": ["None"], "solved": False, "error": False,
                "empty_retries": empty_count, "untagged_not_truncated": 1, "invalid_actions": 1}

    cases = (
        (("error",) * 4, {"actions": [], "solved": None, "error": True,
                         "empty_retries": None, "untagged_not_truncated": None, "invalid_actions": None}),
        (("empty",) * 4, unsolved(4)),
        (("empty", "error", "error", "error"), unsolved(1)),
        (("error", "error", "error", "empty"), unsolved(1)),
        (("empty", "error", "valid"), {"actions": ["go to shelf 1"], "solved": True, "error": False,
                                       "empty_retries": 1, "untagged_not_truncated": 0, "invalid_actions": 0}),
    )
    for replies, expected in cases:
        if run_case(agent, replies) != expected:
            raise SystemExit(f"Runner behaviour for {replies} differs from the audit.")

    with CSV.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    empty = sum(int(row["empty_retries"]) for row in rows)
    errors = sum(int(row["error"]) for row in rows)
    print(f"Published CSV: {len(rows)} rows, empty_retries={empty}, error={errors}")
    if (len(rows), empty, errors) != (804, 0, 0):
        raise SystemExit("Published counters differ from the audited CSV.")


if __name__ == "__main__":
    main()
