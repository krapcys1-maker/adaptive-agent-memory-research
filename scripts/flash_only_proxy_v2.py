#!/usr/bin/env python3
"""The flash-only metering proxy with the version-2 spend ledger. Use this one for new paid runs.

Same behaviour as ``scripts/flash_only_proxy.py`` (only ``deepseek-flash`` is forwarded, the key
is loaded by ``metered_proxy.load_key`` and never printed, the owner's 15 USD ceiling), with
``scripts/arena/spend_ledger_v2.py`` in place of the version-1 ledger:

* the ledger is read fail-closed: a torn, invalid or unattributable line, a missing file or a
  held lock refuses the request with HTTP 402 before anything is forwarded, under a cap scope
  as well (version 1 counted a torn line as zero there);
* every forwarded call is reserved on disk before it is sent and settled after the answer, so
  two proxies on one ledger cannot both take the last slot, and a call whose process died in
  flight stays counted at its reservation;
* a call whose usage the provider did not report is charged at least its reservation;
* the per-run cap is checked before the shared one, so a request refused by the run cap
  leaves no reservation behind;
* a ledger file that does not exist is refused unless ``--new-ledger`` is given, so a mistyped
  path cannot start a budget from zero.

The frozen version-1 files (``flash_only_proxy.py``, ``metered_proxy.py``,
``arena/provider_proxy.py``, ``arena/spend_ledger.py``) are imported unchanged; this file only
composes them with the new ledger. An abandoned reservation stays counted: release it only by
inspecting what was spent, never by editing the ledger.

Usage: python scripts/flash_only_proxy_v2.py --ledger data/lab/aam-deepseek-2026-11/spend-ledger.jsonl --total-cap-usd 12
                                             --cap-scope e1 --run-id e1-flash [--new-ledger] [--port 8799]
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flash_only_proxy as fo  # noqa: E402
import metered_proxy as mp  # noqa: E402
from arena import provider_proxy as pp  # noqa: E402
from arena.spend_ledger import TotalCapReached  # noqa: E402
from arena.spend_ledger_v2 import LedgerUnreadable, SpendLedgerV2  # noqa: E402

OWNER_CEILING_USD = 15.0


class ProxyStateV2(pp.ProxyState):
    """The frozen proxy state with the run cap checked first: a refusal there must not leave a reservation."""

    def check(self) -> Optional[str]:
        reserve = self.reserve()
        if self.run_cap_usd is not None and self.spent_usd + reserve > self.run_cap_usd:
            return (f"this run has spent ${self.spent_usd:.4f} over {len(self.calls)} "
                    f"calls; the next could cost up to ${reserve:.4f} and its cap is "
                    f"${self.run_cap_usd:.2f}. Stopping below it.")
        try:
            self.ledger.check(reserve)                         # writes the reservation when it authorises
        except TotalCapReached as stop:                         # LedgerUnreadable is one
            return str(stop)
        return None


def serve(upstream: str, api_key: str, port: int, ledger: SpendLedgerV2, run_cap_usd: Optional[float],
          decoding: Dict[str, Any], allowed: Sequence[str] = fo.ALLOWED) -> Tuple[ThreadingHTTPServer, ProxyStateV2]:
    if not isinstance(ledger, SpendLedgerV2):
        raise TypeError("flash_only_proxy_v2 needs a SpendLedgerV2; the version-1 ledger belongs to flash_only_proxy.py")
    state = ProxyStateV2(upstream, api_key, ledger, run_cap_usd, decoding)
    server = ThreadingHTTPServer(("127.0.0.1", port), fo.guarded_handler(state, allowed))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Flash-only metering proxy with the fail-closed version-2 ledger.")
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--total-cap-usd", required=True, type=float)
    parser.add_argument("--run-cap-usd", type=float, default=None)
    parser.add_argument("--cap-scope", default=None)
    parser.add_argument("--run-id", default="proxy")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--upstream", default=mp.DEFAULT_UPSTREAM)
    parser.add_argument("--decoding-json", default='{"thinking": {"type": "disabled"}}')
    parser.add_argument("--new-ledger", action="store_true", help="create the ledger file if it does not exist")
    args = parser.parse_args(argv)
    if not (0 < args.total_cap_usd <= OWNER_CEILING_USD):
        print("refusing: --total-cap-usd must be between 0 and the owner's 15 USD", file=sys.stderr)
        return 2
    decoding = json.loads(args.decoding_json)
    if not isinstance(decoding, dict):
        print("refusing: --decoding-json must be a JSON object", file=sys.stderr)
        return 2
    try:
        ledger = SpendLedgerV2(args.ledger, total_cap_usd=args.total_cap_usd, run_id=args.run_id,
                               cap_scope=args.cap_scope, create=args.new_ledger)
    except (LedgerUnreadable, ValueError) as error:             # before the key is touched
        print(f"refusing: {error}", file=sys.stderr)
        return 2
    server, state = serve(args.upstream, mp.load_key(), args.port, ledger, args.run_cap_usd, decoding)
    print("flash-only proxy v2 on http://127.0.0.1:%d/v1 -> %s; allowed models %s; total cap $%.2f (scope %r), "
          "already spent or reserved in scope $%.4f; ledger %s" % (
              server.server_address[1], args.upstream, ", ".join(fo.ALLOWED), args.total_cap_usd, args.cap_scope,
              ledger.scoped_usd(), "spend-ledger-v2"), flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
        print(json.dumps(state.summary(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
