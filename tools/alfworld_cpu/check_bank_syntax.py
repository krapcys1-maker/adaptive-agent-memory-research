"""Check whether the actions in an ALFWorld trajectory bank match the installed action syntax.

Older ALFWorld versions place objects with "put X in/on Y"; newer versions use
"move X to Y". A bank written in the old syntax, retrieved into a newer environment,
shows the agent an action that the parser rejects, usually the action that completes
the task (see MATE, arXiv 2609.35808). Run this before using any public bank.

The templates default to the newer syntax. Pass --templates with a file holding one
regular expression per line to check against another version.

Input: a JSON list (or JSONL) of records with a ShareGPT-style "conversations" list,
where agent turns contain "Action: <action>" (ETO, AgentTraj-L and AgentBank use this
layout), or a .parquet file with a "conversations" column (needs pandas).

Usage:
    python check_bank_syntax.py bank.json [bank2.parquet ...]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

NEW_SYNTAX = [
    r"go to \S+ \d+", r"open \S+ \d+", r"close \S+ \d+", r"take \S+ \d+ from \S+ \d+",
    r"move \S+ \d+ to \S+ \d+", r"put \S+ \d+ into \S+ \d+", r"put \S+ \d+ in \S+ \d+",
    r"inventory", r"examine \S+ \d+", r"use \S+ \d+", r"heat \S+ \d+ with \S+ \d+",
    r"clean \S+ \d+ with \S+ \d+", r"cool \S+ \d+ with \S+ \d+", r"slice \S+ \d+ with \S+ \d+", r"look",
]


def load(path: str) -> list:
    if path.endswith(".parquet"):
        import pandas as pd  # optional dependency
        return [list(c) for c in pd.read_parquet(path)["conversations"]]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [d["conversations"] for d in data]


def actions(conv: list) -> list[str]:
    out = []
    for turn in conv:
        if turn.get("from") in ("gpt", "assistant"):
            out += [a.strip().rstrip(".") for a in re.findall(r"Action:\s*(.+)", turn.get("value", ""))]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("banks", nargs="+")
    ap.add_argument("--templates", default=None, help="file with one regex per line")
    args = ap.parse_args()
    patterns = NEW_SYNTAX
    if args.templates:
        with open(args.templates, encoding="utf-8") as f:
            patterns = [line.strip() for line in f if line.strip()]
    compiled = [re.compile("^" + p + "$") for p in patterns]
    for bank in args.banks:
        convs = load(bank)
        n_act = n_ok = n_bad_traj = 0
        forms = Counter()
        for conv in convs:
            bad_here = False
            for a in actions(conv):
                n_act += 1
                if any(c.match(a) for c in compiled):
                    n_ok += 1
                else:
                    bad_here = True
                    forms[re.sub(r"\d+", "N", a)] += 1
            n_bad_traj += bad_here
        print(f"{bank}: {len(convs)} trajectories, {n_act} actions, compatible {100 * n_ok / max(1, n_act):.1f}%, "
              f"trajectories with an incompatible action {100 * n_bad_traj / max(1, len(convs)):.0f}%")
        print("  most common incompatible forms:", forms.most_common(5))


if __name__ == "__main__":
    main()
