"""K1 checker: a separate process that runs after the raw data of the given blocks are closed (frozen by the supervisor:
meta/RAW.json). Uses the unchanged NIGHT evaluation (p0.evaluate_episode) with the standard BFCL class (ground truth allowed
here; the episode process never reads eval/). Writes eval/<block>.jsonl; an exception for one episode gives
eval_status technical_error (spec sec. 7.2). Same as the pilot's checker.py.
Usage: python -I -X utf8 -B checker.py --base DIR --blocks A S1 [S2 S3]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_lib as kl  # noqa: E402


def evaluate_records(records, n1, p0, bfcl, tag):
    names = p0.Names(tag)
    out = []
    for r in records:
        rec = r["episode"]
        if 100 <= int(rec["task"].rsplit("_", 1)[1]) < 150:
            raise RuntimeError("TradingBot task in the records")
        try:
            ev = p0.evaluate_episode(bfcl, rec, names)
            ev.update({"block": r.get("block"), "eval_status": "ok"})
        except Exception as exc:                                   # spec sec. 7.2: technical error of one episode
            ev = {"task": rec["task"], "arm": r.get("arm"), "block": r.get("block"), "status": rec.get("status"),
                  "eval_status": "technical_error", "error": repr(exc)[:300]}
        out.append(ev)
    return out


def main():
    args = sys.argv[1:]
    base = Path(args[args.index("--base") + 1])
    blocks = args[args.index("--blocks") + 1:]
    L = kl.layout(base)
    raw = kl.read_json(L["meta"] / "RAW.json")
    for f, h in raw["files"].items():
        if kl.sha_file(Path(f)) != h:
            raise SystemExit(f"raw file changed after freezing: {f}")
    n2, p0, xv, n1 = kl.import_harness()
    bfcl = n1.BfclN(kl.BFCL)
    L["eval"].mkdir(parents=True, exist_ok=True)
    for b in blocks:
        recs = n1.read_rows(L["run"] / "sessions" / f"{b}.jsonl")
        ev = evaluate_records(recs, n1, p0, bfcl, f"k1_eval_{b}")
        (L["eval"] / f"{b}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in ev), encoding="utf-8")
        print(f"checked {b}: {len(ev)} episodes, technical errors {sum(e['eval_status'] != 'ok' for e in ev)}")


if __name__ == "__main__":
    main()
