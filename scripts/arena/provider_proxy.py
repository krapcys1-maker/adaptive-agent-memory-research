#!/usr/bin/env python3
"""A metering proxy, so a system that runs in its own process is still capped.

`FixedDecoding` wraps the provider client in-process. That works for a system the
arena imports and constructs — CUPMem — and reaches nothing at all for a system
that is a server: Hindsight runs its own process, builds its own client and would
spend without the ledger ever seeing it.

A cap the run can walk around is a report, not a cap. So the interception moves
down a layer: the system is pointed at `http://127.0.0.1:PORT/v1`, and this
forwards to the real provider while doing exactly what the in-process wrapper
does — enforce the arena's decoding, record what the system asked for beside what
was enforced, price every response, and refuse the request that would cross
either ceiling.

Refusal is HTTP 402 with a JSON body, because a system given a network error
retries and a system given a payment error usually stops. Either way the request
was never forwarded, so the money was never spent.

What it does not do
-------------------
It does not read or alter message content, and it does not cache. The only
mutation is the decoding block, recorded per call. Anything it cannot parse as
JSON is forwarded untouched and counted as a call with unknown tokens — unknown,
never zero.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import ARENA_DECODING, PRICE_PER_MTOK  # noqa: E402
from arena.spend_ledger import SpendLedger, TotalCapReached  # noqa: E402


class ProxyState:
    """Everything the handler needs, and the lock that keeps the count honest."""

    def __init__(self, upstream: str, api_key: str, ledger: SpendLedger,
                 run_cap_usd: float | None, decoding: dict[str, Any],
                 first_call_reserve_usd: float = 0.02) -> None:
        self.upstream = upstream.rstrip("/")
        self.api_key = api_key
        self.ledger = ledger
        self.run_cap_usd = run_cap_usd
        self.decoding = dict(decoding)
        self.first_call_reserve = first_call_reserve_usd
        self.calls: list[dict[str, Any]] = []
        self.refusals = 0
        self.lock = threading.Lock()

    # ------------------------------------------------------------------- money

    def call_cost(self, prompt: int, completion: int) -> float:
        return (prompt / 1e6 * PRICE_PER_MTOK["input"]
                + completion / 1e6 * PRICE_PER_MTOK["output"])

    @property
    def spent_usd(self) -> float:
        return sum(call["usd"] for call in self.calls)

    def reserve(self) -> float:
        seen = [call["usd"] for call in self.calls]
        return max(seen) * 1.5 if seen else self.first_call_reserve

    def check(self) -> str | None:
        """The reason to refuse, or None. Called with the lock held."""
        reserve = self.reserve()
        try:
            self.ledger.check(reserve)
        except TotalCapReached as stop:
            return str(stop)
        if self.run_cap_usd is not None and self.spent_usd + reserve > self.run_cap_usd:
            return (f"this run has spent ${self.spent_usd:.4f} over {len(self.calls)} "
                    f"calls; the next could cost up to ${reserve:.4f} and its cap is "
                    f"${self.run_cap_usd:.2f}. Stopping below it.")
        return None

    def snapshot(self) -> dict[str, int]:
        """Running totals, taken atomically. The one surface a meter must have.

        Adapters take deltas of this to price a single operation, so it is a
        method rather than a list: the remote meter lives in another process and
        cannot hand out its calls without shipping them over HTTP per probe.
        """
        with self.lock:
            return {
                "calls": len(self.calls),
                "prompt_tokens": sum(c["prompt_tokens"] for c in self.calls),
                "completion_tokens": sum(c["completion_tokens"] for c in self.calls),
            }

    def summary(self) -> dict[str, Any]:
        overrides = [c for c in self.calls if c["overridden"]]
        prompt = sum(c["prompt_tokens"] for c in self.calls)
        completion = sum(c["completion_tokens"] for c in self.calls)
        return {
            "calls": len(self.calls),
            "refused_calls": self.refusals,
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "usd": round(self.spent_usd, 6),
            "unknown_usage_calls": sum(1 for c in self.calls if c["usage_known"] is False),
            "arena_enforced_decoding": self.decoding,
            "decoding_overrides": len(overrides),
            "decoding_override_values": sorted(
                {json.dumps(c["overridden"], sort_keys=True) for c in overrides}),
            "native_requested_decoding": sorted(
                {json.dumps(c["requested"], sort_keys=True) for c in self.calls}),
        }


def make_handler(state: ProxyState):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args: Any) -> None:  # noqa: A003
            pass  # the ledger is the log

        def _refuse(self, reason: str) -> None:
            body = json.dumps({"error": {
                "type": "arena_spend_cap",
                "message": reason,
                "note": "the request was never forwarded, so nothing was spent",
            }}).encode()
            self.send_response(402)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""

            with state.lock:
                reason = state.check()
                if reason is not None:
                    state.refusals += 1
            if reason is not None:
                self._refuse(reason)
                return

            requested: dict[str, Any] = {}
            overridden: dict[str, Any] = {}
            try:
                payload = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = None

            if isinstance(payload, dict):
                requested = {k: payload.get(k) for k in state.decoding}
                overridden = {k: payload[k] for k in state.decoding
                              if k in payload and payload[k] != state.decoding[k]}
                payload.update(state.decoding)
                raw = json.dumps(payload).encode()

            request = urllib.request.Request(
                f"{state.upstream}{self.path}", data=raw, method="POST",
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {state.api_key}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    status, body = response.status, response.read()
            except urllib.error.HTTPError as failure:
                status, body = failure.code, failure.read()
            except Exception as failure:  # noqa: BLE001
                status = 502
                body = json.dumps({"error": {"type": "arena_proxy_upstream",
                                             "message": str(failure)}}).encode()

            prompt = completion = 0
            usage_known: bool | None = None
            try:
                usage = (json.loads(body) or {}).get("usage") or {}
                prompt = int(usage.get("prompt_tokens", 0) or 0)
                completion = int(usage.get("completion_tokens", 0) or 0)
                usage_known = bool(usage)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError, TypeError):
                # A streamed or unparseable body. The call happened, so it is
                # counted; its tokens are unknown, which is not the same as zero.
                usage_known = False

            usd = state.call_cost(prompt, completion)
            with state.lock:
                state.calls.append({
                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "path": self.path, "status": status,
                    "model": (payload or {}).get("model") if isinstance(payload, dict) else None,
                    "requested": requested, "enforced": dict(state.decoding),
                    "overridden": overridden,
                    "prompt_tokens": prompt, "completion_tokens": completion,
                    "usage_known": usage_known, "usd": usd,
                })
                state.ledger.record(usd, model=(payload or {}).get("model")
                                    if isinstance(payload, dict) else None,
                                    prompt_tokens=prompt, completion_tokens=completion,
                                    usage_known=usage_known, via="proxy")

            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/arena/summary":
                body = json.dumps(state.summary(), indent=2).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def serve(upstream: str, api_key: str, port: int, ledger: SpendLedger,
          run_cap_usd: float | None) -> tuple[ThreadingHTTPServer, ProxyState]:
    state = ProxyState(upstream, api_key, ledger, run_cap_usd, ARENA_DECODING)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(state))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, state


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", default="https://api.deepseek.com")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--run-id", default="proxy")
    parser.add_argument("--cap-usd", type=float, default=3.0)
    parser.add_argument("--total-cap-usd", type=float, default=10.0)
    parser.add_argument("--cap-scope", default=None,
                        help="prefix naming this experiment; the total cap counts "
                             "only runs under it, not everything ever spent")
    args = parser.parse_args()

    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=args.run_id,
                         cap_scope=args.cap_scope)
    server, state = serve(args.upstream, load_key(), args.port, ledger, args.cap_usd)
    print(f"arena proxy on http://127.0.0.1:{args.port}/v1 -> {args.upstream}; "
          f"run cap ${args.cap_usd}, night cap ${args.total_cap_usd}, "
          f"already spent ${ledger.total_usd():.4f}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
        print(json.dumps(state.summary(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
