#!/usr/bin/env python3
"""$0 diagnostic (no paid calls): for a handful of already-ingested banks from
past mechanism runs, dump the FULL stored memory set (not just top-10) and
report whether it contains anything related to a hand-picked keyword set for
the fact the reader was missing. Distinguishes "absent from top-10 due to a
ranking/query-phrasing mismatch" (HyDE-fixable) from "absent from the whole
store" (a write-time Mem0 extraction miss that no read-side or query-side
mechanism could fix). Uses only memory.get_all() -- no LLM call, no spend.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

CHECKS = [
    ("data/lab/arena/raw/retrieval-confidence-v1-store", "mechd-0a995998",
     ["clothing", "pick up", "pickup", "return", "store", "dry clean", "tailor", "alteration"]),
    ("data/lab/arena/raw/sibling-entity-v1-store", "meche-10d9b85a",
     ["workshop", "lecture", "conference", "april", "seminar"]),
    ("data/lab/arena/raw/sibling-entity-v1-store", "meche-0ea62687",
     ["mpg", "mile", "gallon", "fuel", "gas mileage"]),
    ("data/lab/arena/raw/sibling-entity-v1-store", "meche-1568498a",
     ["chess", "kg2", "kg3", "bd5"]),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--model", default="deepseek-chat")
    args = parser.parse_args()

    os.environ["MEM0_TELEMETRY"] = "False"
    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))
    from mem0 import Memory
    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import load_key
    from arena.provider_proxy import serve

    ledger = SpendLedger(total_cap_usd=0.001, run_id="absence-check-noop-",
                         cap_scope="absence-check-noop-")
    _server, meter = serve("https://api.deepseek.com", load_key(), 0, ledger, 0.001)
    port = _server.server_address[1]

    seen_stores: dict[str, "Memory"] = {}
    for store_path, bank, keywords in CHECKS:
        if store_path not in seen_stores:
            store = (ROOT / store_path).resolve()
            seen_stores[store_path] = Memory.from_config({
                "llm": {"provider": "openai", "config": {
                    "model": args.model, "api_key": "routed-through-the-arena-proxy",
                    "openai_base_url": f"http://127.0.0.1:{port}/v1"}},
                "embedder": {"provider": "huggingface", "config": {
                    "model": str(Path(args.embedding_model_path).resolve())}},
                "vector_store": {"provider": "qdrant", "config": {
                    "collection_name": "arena_pilot", "embedding_model_dims": 384,
                    "path": str(store), "on_disk": True}},
            })
        memory = seen_stores[store_path]
        all_items = memory.get_all(user_id=bank)
        results = all_items.get("results", all_items) if isinstance(all_items, dict) else all_items
        texts = [str(r.get("memory", "")) for r in results if isinstance(r, dict)]
        print(f"=== {bank} ({store_path}) -- {len(texts)} total stored items ===")
        hits = [t for t in texts if any(k.lower() in t.lower() for k in keywords)]
        if hits:
            print(f"  KEYWORD HITS ({len(hits)}):")
            for h in hits:
                print("   -", h)
        else:
            print(f"  NO keyword hits for {keywords} across all {len(texts)} stored items -- "
                  "TRUE ABSENCE (not a top-10 ranking miss; fact never survived Mem0's own "
                  "write-time extraction into this store at all).")
        print()

    print("cost incurred (should be 0.0):", ledger.scoped_usd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
