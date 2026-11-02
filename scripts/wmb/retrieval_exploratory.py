"""WMB-R1: the EXPLORATORY U1 readings, computed with the independent reference implementation when the judge's gate has failed.

The frozen analysis (retrieval_bench.analyse) leaves the U1 tables out when the gate fails, as the README says (Amendment 3). This script does not touch the frozen files: it reads
prep.json (scores and first candidates), the judge's pooled labels (labels.jsonl, kind "pool") and the assistant's decisive-pair labels, and calls
retrieval_bench_ref.p1_readings. Everything it writes is labelled EXPLORATORY: it cannot enter the decision table and is not a verdict.

Usage: python scripts/wmb/retrieval_exploratory.py --workdir WORKDIR --out exploratory_u1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wmb import contract, retrieval_bench_ref as ref  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json"
METHODS = ("EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL", "LEX_BM25", "LEX_TFIDF", "HYB_SHIPPED")


def structure(prep: dict):
    tasks = [int(i) for i in prep["eligible"]]
    scores = {m: [(prep["rankings"][m][str(i)][0][1] if prep["rankings"][m][str(i)] else float("-inf")) for i in tasks] for m in METHODS}
    first = {m: [(prep["rankings"][m][str(i)][0][0] if prep["rankings"][m][str(i)] else -1) for i in tasks] for m in METHODS}
    days = [prep["times"][i][:10] for i in tasks]
    return scores, first, days, tasks


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--draws", type=int, default=None, help="override the number of bootstrap draws (default: the config's)")
    args = parser.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    work = Path(args.workdir)
    prep = json.loads((work / "prep.json").read_text(encoding="utf-8"))
    scores, first, days, tasks = structure(prep)
    rows = contract.load_jsonl(work / "labels.jsonl")
    labels: Dict[Tuple[int, int], str] = {(r["i"], r["j"]): r["label"] for r in rows if r["kind"] == "pool"}
    assistant_raw = json.loads((work / "decisive_labels_assistant.json").read_text(encoding="utf-8"))
    keys = json.loads((work / "decisive_keys.json").read_text(encoding="utf-8"))
    assistant = {(int(keys[k]["i"]), int(keys[k]["j"])): v for k, v in assistant_raw.items()}
    lenient = {pair: ("SAME" if label in ("SAME", "RELATED") else label) for pair, label in labels.items()}
    out: dict = {"status": "EXPLORATORY: the judge gate failed (Amendment 3); not a verdict, cannot enter the decision table", "pooled_labels": dict(Counter(labels.values())), "pairs_labelled": len(labels)}
    for name, lab, ass in (("strict_judge_labels", labels, assistant), ("lenient_judge_labels", lenient, {p: ("SAME" if v in ("SAME", "RELATED") else v) for p, v in assistant.items()})):
        reading = ref.p1_readings(scores, first, days, tasks, lab, cfg, ass, args.draws)
        out[name] = json.loads(json.dumps(reading, default=lambda x: x.item() if hasattr(x, "item") else str(x)))
    decisive = Counter()
    for pair, mine in assistant.items():
        judge = labels.get(pair)
        decisive[(mine, judge)] += 1
    out["decisive_audit"] = {"n": len(assistant), "assistant_vs_judge": {"%s|%s" % k: v for k, v in sorted(decisive.items(), key=lambda kv: str(kv[0]))},
                             "agreement_same_vs_not": sum(v for (m, j), v in decisive.items() if (m == "SAME") == (j == "SAME")) / max(1, len(assistant))}
    Path(args.out).write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"verdict_strict": out["strict_judge_labels"]["verdict"], "d_emb": out["strict_judge_labels"]["d_emb"], "d_hyb": out["strict_judge_labels"]["d_hyb"],
                      "tasks_with_same": out["strict_judge_labels"]["tasks_with_same"], "audit": out["decisive_audit"]["agreement_same_vs_not"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
