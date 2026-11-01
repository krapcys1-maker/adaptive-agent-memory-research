#!/usr/bin/env python3
"""Run the AAM-E1-SIM harness against an OpenAI-compatible endpoint (a local metering proxy for a paid API) instead of Ollama.

The harness itself (scripts/writer_memory_sim.py) is not changed: it takes a `generate` callable, and this runner supplies one.
Records are appended to --records and a finished entry is never redone, so the run can be stopped and started again.

Usage: python scripts/run_writer_memory_sim_openai.py --records PATH --base-url http://127.0.0.1:8799/v1 --model deepseek-flash
                                                      --seeds 4 5 6 7 8 9 [--days 36] [--workers 5]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_backends as backends  # noqa: E402
import writer_memory_sim as sim  # noqa: E402


def proxy_summary(base_url: str) -> Optional[dict]:
    """The metering proxy's running totals (its /arena/summary endpoint), if the endpoint is one."""
    root = base_url.rstrip("/")
    root = root[:-3] if root.endswith("/v1") else root
    try:
        with urllib.request.urlopen(root + "/arena/summary", timeout=15) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AAM-E1-SIM harness against an OpenAI-compatible endpoint.")
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--days", type=int, default=36)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--arms", nargs="+", default=list(sim.ARMS), choices=list(sim.ARMS))
    args = parser.parse_args(argv)
    meta_path = args.records.with_name("run-meta.json")
    meta = {"model": args.model, "endpoint": "OpenAI-compatible, through a local metering proxy", "write_options": sim.WRITE_OPTS,
            "trace_options": sim.TRACE_OPTS, "seeds": args.seeds, "days": args.days,
            "harness_sha256": hashlib.sha256(Path(sim.__file__).read_bytes()).hexdigest(),
            "backends_sha256": hashlib.sha256(Path(backends.__file__).read_bytes()).hexdigest()}
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        for key in ("model", "harness_sha256", "backends_sha256"):
            if previous.get(key) != meta[key]:
                print("refusing to continue: %s differs from the first run" % key, file=sys.stderr)
                return 2
    else:
        meta["first_started"] = datetime.now().isoformat(timespec="seconds")
        meta["proxy_at_start"] = proxy_summary(args.base_url)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    try:
        written = sim.run(args.records, backends.openai_generate(args.base_url, args.model), args.seeds, args.days, args.arms,
                          args.workers, log=lambda line: print(line, flush=True))
    except backends.SpendCapRefused as stop:
        print("stopped by the spend cap: %s" % stop, file=sys.stderr)
        return 3
    finally:
        args.records.with_name("proxy-summary.json").write_text(json.dumps(proxy_summary(args.base_url), indent=2) + "\n", encoding="utf-8")
    print("done: %d new entries" % written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
