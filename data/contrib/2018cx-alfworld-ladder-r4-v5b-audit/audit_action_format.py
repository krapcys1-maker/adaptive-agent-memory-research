"""Reproduce the V5B action-format counter blind spot from public inputs."""

import csv
import hashlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "tools" / "alfworld_ladder" / "agent.py"
RUNNER_PIN = "c5c5eea0545eba11fbd27435296a80bb88e0c31e707762862f98417caba9636a"
CSV = ROOT / "data" / "lab" / "autolab-alfworld-ladder-r4-v5b" / "per_unit.csv"
ARMS = ("placebo", "retrieved_task")
COUNTERS = ("steps", "untagged_not_truncated", "invalid_no_action_tag", "invalid_actions")


def check_runner():
    if hashlib.sha256(RUNNER.read_bytes()).hexdigest() != RUNNER_PIN:
        raise SystemExit("Runner bytes differ from the V5B pin. Use the audited revision.")
    sys.path.insert(0, str(RUNNER.parent))
    import agent

    admissible = ["go to desk 1", "go to shelf 1"]
    expected_action = admissible[-1]
    answers = (
        "<think>Choose the shelf.</think><action>go to shelf 1</action>",
        "<think>Choose the shelf.</think><action>go to desk 1</action>"
        "<action>go to shelf 1</action>",
    )
    if "exactly one admissible action" not in agent.FORMAT_REMINDER:
        raise SystemExit("Expected the V5B exactly-one-action reminder.")
    for label, answer, expected_count in zip(("single", "double"), answers, (1, 2)):
        count = len(re.findall(r"<action>(.*?)</action>", answer, re.S))
        metrics = agent.classify_answer(answer, "stop")
        action, ok = agent.parse_action(answer, admissible)
        print(f"{label}: complete_pairs={count}, {metrics}, action={action!r}, accepted={ok}")
        if count != expected_count or metrics != {"truncated": 0, "untagged_not_truncated": 0}:
            raise SystemExit("Unexpected format counter result.")
        if (action, ok) != (expected_action, True):
            raise SystemExit("Unexpected parser result.")


def summarize_csv():
    totals = {arm: dict.fromkeys(COUNTERS, 0) for arm in ARMS}
    with CSV.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["arm"] in totals:
                for counter in COUNTERS:
                    totals[row["arm"]][counter] += int(row[counter])

    print("\nPublished field totals and step-weighted format rates:")
    rates = {}
    for arm, counts in totals.items():
        rates[arm] = counts["untagged_not_truncated"] / counts["steps"]
        print(f"{arm}: {counts}, untagged_not_truncated_per_step={rates[arm]:.6f}")
    print(f"retrieved minus placebo: {rates['retrieved_task'] - rates['placebo']:+.6f}")


if __name__ == "__main__":
    check_runner()
    summarize_csv()
