#!/usr/bin/env python3
"""A local metering proxy for the paid-API experiments of the memory research: a hard spend cap, a ledger, and no key in any script.

It reuses the arena's proxy (scripts/arena/provider_proxy.py) and changes two things: the decoding block that is merged into every
request is chosen by the caller (the arena's block forces temperature 0, which an experiment that samples cannot accept), and the
key is found from a git worktree as well as from the main checkout. The key is loaded by the arena's own helper, held in this
process only, and never printed, logged or written. Clients talk to http://127.0.0.1:PORT/v1 with a dummy key.

A request that could cross the cap is answered with HTTP 402 and is never forwarded, so nothing is spent. Every forwarded call is
appended to the ledger (run id, model, token counts, cost at the arena's list price, which is deliberately high). The ledger holds
no message content.

Usage: python scripts/metered_proxy.py --ledger data/lab/aam-deepseek-2026-11/spend-ledger.jsonl --total-cap-usd 12 --cap-scope e1
                                       [--run-cap-usd 6] [--run-id e1ds] [--port 8799] [--decoding-json '{"thinking": {"type": "disabled"}}']
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena import provider_proxy as pp  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

DEFAULT_UPSTREAM = "https://api.deepseek.com"


def main_checkout() -> Path:
    """The root of the repository's main working tree, also when called from a linked worktree."""
    out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.strip()
    return Path(out).parent


def load_key() -> str:
    """The arena's helper looks in ROOT and ROOT.parent; from a linked worktree retry from the main checkout. The value is never shown."""
    try:
        return pp.load_key()
    except SystemExit:
        pp.ROOT = main_checkout()
        return pp.load_key()


def serve(upstream: str, api_key: str, port: int, ledger: SpendLedger, run_cap_usd: Optional[float],
          decoding: Dict[str, Any]) -> Tuple[ThreadingHTTPServer, "pp.ProxyState"]:
    state = pp.ProxyState(upstream, api_key, ledger, run_cap_usd, decoding)
    server = ThreadingHTTPServer(("127.0.0.1", port), pp.make_handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Metering proxy with a hard spend cap for the paid-API experiments.")
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--total-cap-usd", required=True, type=float, help="hard cap over the runs counted by --cap-scope (the ledger is the authority)")
    parser.add_argument("--run-cap-usd", type=float, default=None, help="optional cap for this proxy process alone")
    parser.add_argument("--cap-scope", default=None, help="run-id prefix that the total cap counts")
    parser.add_argument("--run-id", default="proxy")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    parser.add_argument("--decoding-json", default='{"thinking": {"type": "disabled"}}',
                        help="JSON object merged into every request; the caller's temperature and top_p are left alone")
    args = parser.parse_args(argv)
    if not (0 < args.total_cap_usd <= 15):
        print("refusing: --total-cap-usd must be between 0 and the owner's 15 USD", file=sys.stderr)
        return 2
    decoding = json.loads(args.decoding_json)
    if not isinstance(decoding, dict):
        print("refusing: --decoding-json must be a JSON object", file=sys.stderr)
        return 2
    ledger = SpendLedger(args.ledger, total_cap_usd=args.total_cap_usd, run_id=args.run_id, cap_scope=args.cap_scope)
    server, state = serve(args.upstream, load_key(), args.port, ledger, args.run_cap_usd, decoding)
    print("metering proxy on http://127.0.0.1:%d/v1 -> %s; total cap $%.2f (scope %r), already spent in scope $%.4f; decoding %s" % (
        server.server_address[1], args.upstream, args.total_cap_usd, args.cap_scope, ledger.scoped_usd(), json.dumps(decoding)), flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
        print(json.dumps(state.summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
