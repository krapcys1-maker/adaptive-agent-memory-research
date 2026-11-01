#!/usr/bin/env python3
"""The metering proxy of scripts/metered_proxy.py, restricted to the one model the owner authorised for paid tests: deepseek-flash.

A request for any other model is answered with HTTP 403 and is never forwarded, so nothing is spent on it. This exists because an earlier
run of the judges used deepseek-v4-pro although the owner had said "4.1 flash"; the restriction is technical so that it cannot happen
again by a slip. The key is loaded exactly as in metered_proxy.py (never printed or stored); the spend cap and the ledger are the same.

Usage: python scripts/flash_only_proxy.py --ledger data/lab/aam-deepseek-2026-11/spend-ledger.jsonl --total-cap-usd 12 --cap-scope e1
                                          --run-id e1-flash --port 8799
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metered_proxy as mp  # noqa: E402
from arena import provider_proxy as pp  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

ALLOWED: Tuple[str, ...] = ("deepseek-flash",)


def guarded_handler(state: "pp.ProxyState", allowed: Sequence[str] = ALLOWED):
    base = pp.make_handler(state)

    class Guarded(base):  # type: ignore[valid-type, misc]
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                model = json.loads(raw).get("model") if raw else None
            except (ValueError, AttributeError):
                model = None
            if model not in allowed:
                body = json.dumps({"error": {"type": "model_not_authorised", "note": "the request was never forwarded, so nothing was spent",
                                             "message": "only %s may be used for paid tests (the owner's instruction); requested %r" % (", ".join(allowed), model)}}).encode()
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            original, self.rfile = self.rfile, io.BytesIO(raw)       # the base handler reads the body itself
            try:
                super().do_POST()
            finally:
                self.rfile = original

    return Guarded


def serve(upstream: str, api_key: str, port: int, ledger: SpendLedger, run_cap_usd: Optional[float], decoding: Dict[str, Any],
          allowed: Sequence[str] = ALLOWED) -> Tuple[ThreadingHTTPServer, "pp.ProxyState"]:
    state = pp.ProxyState(upstream, api_key, ledger, run_cap_usd, decoding)
    server = ThreadingHTTPServer(("127.0.0.1", port), guarded_handler(state, allowed))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Metering proxy that forwards only deepseek-flash.")
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--total-cap-usd", required=True, type=float)
    parser.add_argument("--run-cap-usd", type=float, default=None)
    parser.add_argument("--cap-scope", default=None)
    parser.add_argument("--run-id", default="proxy")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--upstream", default=mp.DEFAULT_UPSTREAM)
    parser.add_argument("--decoding-json", default='{"thinking": {"type": "disabled"}}')
    args = parser.parse_args(argv)
    if not (0 < args.total_cap_usd <= 15):
        print("refusing: --total-cap-usd must be between 0 and the owner's 15 USD", file=sys.stderr)
        return 2
    decoding = json.loads(args.decoding_json)
    if not isinstance(decoding, dict):
        print("refusing: --decoding-json must be a JSON object", file=sys.stderr)
        return 2
    ledger = SpendLedger(args.ledger, total_cap_usd=args.total_cap_usd, run_id=args.run_id, cap_scope=args.cap_scope)
    server, state = serve(args.upstream, mp.load_key(), args.port, ledger, args.run_cap_usd, decoding)
    print("flash-only metering proxy on http://127.0.0.1:%d/v1 -> %s; allowed models %s; total cap $%.2f (scope %r), already spent in scope $%.4f" % (
        server.server_address[1], args.upstream, ", ".join(ALLOWED), args.total_cap_usd, args.cap_scope, ledger.scoped_usd()), flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
        print(json.dumps(state.summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
