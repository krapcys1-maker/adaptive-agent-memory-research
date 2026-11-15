"""Pilot batch: train games whose family is in neither units.json nor the bank, 5 per task type (seed 1),
times the arms none, placebo, retrieved_task, seed 0. Output: data/pilot_batch.jsonl (lab batch format)."""
import glob
import json
import os
import random
import sys

root = os.path.expanduser(sys.argv[1])
data = sys.argv[2]
per_type = int(sys.argv[3]) if len(sys.argv) > 3 else 5
units = json.load(open(os.path.join(data, "units.json")))
bank = [json.loads(l) for l in open(os.path.join(data, "bank.jsonl"))]
used = {u.split("/")[1] for u in units} | {b["family"] for b in bank}
train = sorted("train/" + os.path.relpath(os.path.dirname(g), os.path.join(root, "train")).replace(os.sep, "/")
               for g in glob.glob(os.path.join(root, "train", "*", "*", "game.tw-pddl")))
rng = random.Random(1)
picked = []
for ty in sorted({t.split("/")[1].split("-")[0] for t in train}):
    pool, fams = [], set()
    for t in rng.sample([t for t in train if t.split("/")[1].split("-")[0] == ty and t.split("/")[1] not in used],
                        k=sum(1 for t in train if t.split("/")[1].split("-")[0] == ty and t.split("/")[1] not in used)):
        if t.split("/")[1] not in fams:
            fams.add(t.split("/")[1]); pool.append(t)
    picked += pool[:per_type]
with open(os.path.join(data, "pilot_batch.jsonl"), "w") as f:
    for t in picked:
        for arm in ("none", "placebo", "retrieved_task"):
            f.write(json.dumps({"unit": "pilot~" + t, "task": t, "arm": arm, "seed": 0}) + "\n")
print(len(picked), "games", 3 * len(picked), "jobs")
