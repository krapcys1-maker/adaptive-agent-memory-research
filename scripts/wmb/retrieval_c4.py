"""WMB-R1 control C4: the analysis and its independent reference return identical readings on synthetic label sets with a planted gain.

Run after `retrieval_bench.py prepare` (free, before any model call): the scores and first candidates are the REAL ones of the slice, the labels are synthetic.
For each planted D_emb in config readings.c4.planted_gains and each of `--sets` label sets: pairs are labelled SAME at random with probability --base, then
labels of the EMB_MINILM first candidates are flipped (or those of the LEX_KERNEL first candidates cleared) until hits(EMB) - hits(LEX) equals the planted gain at
q = primary_q. Both implementations then read the set; every field of their result must be identical, and the share of sets with verdict EMBEDDER_HELPS_GATE is
reported per gain (at most readings.c4.max_helps_share_at_zero at gain 0, and rising with the gain).

Usage: python scripts/wmb/retrieval_c4.py --prep WORKDIR/prep.json --out WORKDIR/c4.json [--sets 1000] [--draws 300]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wmb import contract, retrieval_bench as rb, retrieval_bench_ref as ref  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json"
METHODS = ("EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL")


def plain(x):
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    return x.item() if hasattr(x, "item") else x


def load_structure(prep_path: Path) -> Tuple[Dict[str, List[float]], Dict[str, List[int]], List[str], List[int]]:
    prep = json.loads(Path(prep_path).read_text(encoding="utf-8"))
    tasks = [int(i) for i in prep["eligible"]]
    scores = {m: [(prep["rankings"][m][str(i)][0][1] if prep["rankings"][m][str(i)] else float("-inf")) for i in tasks] for m in METHODS}
    first = {m: [(prep["rankings"][m][str(i)][0][0] if prep["rankings"][m][str(i)] else -1) for i in tasks] for m in METHODS}
    days = [prep["times"][i][:10] for i in tasks]
    return scores, first, days, tasks


def fired_pairs(scores: List[float], first: List[int], tasks: List[int], q: float) -> List[Tuple[int, int]]:
    pos = rb.fire_positions(scores, tasks, q)
    return [(int(tasks[p]), int(first[p])) for p in pos.tolist() if first[p] >= 0]


def plant(rng: random.Random, scores, first, tasks, base: float, gain: int, q: float) -> Dict[Tuple[int, int], str]:
    pairs = {(int(i), int(first[m][k])) for m in METHODS for k, i in enumerate(tasks) if first[m][k] >= 0}
    labels = {p: ("SAME" if rng.random() < base else "UNRELATED") for p in sorted(pairs)}
    emb, lex = fired_pairs(scores["EMB_MINILM"], first["EMB_MINILM"], tasks, q), fired_pairs(scores["LEX_KERNEL"], first["LEX_KERNEL"], tasks, q)
    lex_set, emb_set = set(lex), set(emb)
    for _ in range(4 * len(tasks)):
        d = sum(1 for p in emb if labels[p] == "SAME") - sum(1 for p in lex if labels[p] == "SAME")
        if d == gain:
            break
        if d < gain:      # more hits for EMB, or fewer for LEX
            moves = [(p, "SAME") for p in emb if labels[p] != "SAME" and p not in lex_set] + [(p, "UNRELATED") for p in lex if labels[p] == "SAME" and p not in emb_set]
        else:             # fewer hits for EMB, or more for LEX
            moves = [(p, "UNRELATED") for p in emb if labels[p] == "SAME" and p not in lex_set] + [(p, "SAME") for p in lex if labels[p] != "SAME" and p not in emb_set]
        if not moves:
            break
        pair, label = rng.choice(moves)
        labels[pair] = label
    return labels


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prep", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--sets", type=int, default=None)
    parser.add_argument("--draws", type=int, default=300)
    parser.add_argument("--base", type=float, default=0.25)
    args = parser.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    spec = cfg["readings"]["c4"]
    sets = args.sets or spec["synthetic_sets"]
    q = cfg["readings"]["primary_q"]
    scores, first, days, tasks = load_structure(args.prep)
    result: Dict[str, dict] = {}
    mismatches = 0
    for gain in spec["planted_gains"]:
        helps, achieved = 0, []
        for n in range(sets):
            rng = random.Random(1000003 * gain + n)
            labels = plant(rng, scores, first, tasks, args.base, gain, q)
            a = plain(rb.p1_readings(scores, first, days, tasks, labels, cfg, None, args.draws))
            b = plain(ref.p1_readings(scores, first, days, tasks, labels, cfg, None, args.draws))
            mismatches += 0 if a == b else 1
            helps += 1 if a["verdict"] == "EMBEDDER_HELPS_GATE" else 0
            achieved.append(a["d_emb"]["d"])
        result[str(gain)] = {"sets": sets, "helps_share": helps / sets, "mean_d": sum(achieved) / sets, "min_d": min(achieved), "max_d": max(achieved)}
        print(gain, result[str(gain)], flush=True)
    shares = [result[str(g)]["helps_share"] for g in spec["planted_gains"]]
    report = {"draws": args.draws, "base_relevance": args.base, "gains": result, "implementations_identical": mismatches == 0, "mismatches": mismatches,
              "helps_at_zero_ok": result[str(spec["planted_gains"][0])]["helps_share"] <= spec["max_helps_share_at_zero"],
              "helps_rises_with_gain": all(shares[k] <= shares[k + 1] + 0.02 for k in range(len(shares) - 1))}
    contract.write_text_lf(args.out, json.dumps(report, indent=1, sort_keys=True) + "\n")          # LF on every platform
    print(json.dumps(report, sort_keys=True))
    return 0 if report["implementations_identical"] and report["helps_at_zero_ok"] and report["helps_rises_with_gain"] else 1


if __name__ == "__main__":
    sys.exit(main())
