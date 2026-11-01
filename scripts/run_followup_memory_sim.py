#!/usr/bin/env python3
"""Run the AAM-E2-FU harness (scripts/followup_memory_sim.py) against an OpenAI-compatible endpoint, normally a local metering proxy.

Records are appended to --records and a finished note is never redone, so the run can be stopped and started again. The embedder
(sentence-transformers, offline) is loaded here and shared by the worker threads.

Usage: python scripts/run_followup_memory_sim.py --records PATH --base-url http://127.0.0.1:8799/v1 --model deepseek-flash --tau 0.7
                                                 --seeds 11 12 [--days 60] [--workers 4]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import followup_memory_sim as fu  # noqa: E402
import llm_backends as backends  # noqa: E402
import run_writer_memory_sim_openai as e1_runner  # noqa: E402


def main(argv: Optional[List[str]] = None, embedder=None) -> int:
    parser = argparse.ArgumentParser(description="Run the AAM-E2-FU harness against an OpenAI-compatible endpoint.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tau", required=True, type=float, help="retrieval threshold calibrated beforehand from the task inputs alone")
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--arms", nargs="+", default=list(fu.ARMS), choices=list(fu.ALL_ARMS))
    args = parser.parse_args(argv)
    meta_path = args.records.with_name("run-meta.json")
    meta = {"model": args.model, "endpoint": "OpenAI-compatible, through a local metering proxy", "tau": args.tau, "write_options": fu.WRITE_OPTS,
            "trace_options": fu.TRACE_OPTS, "seeds": args.seeds, "days": args.days, "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "harness_sha256": hashlib.sha256(Path(fu.__file__).read_bytes()).hexdigest(),
            "backends_sha256": hashlib.sha256(Path(backends.__file__).read_bytes()).hexdigest()}
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        for key in ("model", "tau", "harness_sha256", "backends_sha256"):
            if previous.get(key) != meta[key]:
                print("refusing to continue: %s differs from the first run" % key, file=sys.stderr)
                return 2
    else:
        meta["first_started"] = datetime.now().isoformat(timespec="seconds")
        meta["proxy_at_start"] = e1_runner.proxy_summary(args.base_url)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    embedder = embedder or fu.Embedder()
    try:
        written = fu.run(args.records, backends.openai_generate(args.base_url, args.model), embedder, args.tau, args.seeds, args.days,
                         args.arms, args.workers, log=lambda line: print(line, flush=True))
    except backends.SpendCapRefused as stop:
        print("stopped by the spend cap: %s" % stop, file=sys.stderr)
        return 3
    finally:
        args.records.with_name("proxy-summary.json").write_text(json.dumps(e1_runner.proxy_summary(args.base_url), indent=2) + "\n", encoding="utf-8")
    print("done: %d new notes" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
