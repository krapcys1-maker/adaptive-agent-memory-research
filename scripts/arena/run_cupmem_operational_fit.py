"""Operational fit for CUPMem: does the real system confirm the adapter's assumptions?

Accuracy is not measured here and a wrong answer does not fail this run. The
question is only whether the assumptions the adapter encodes survive contact
with the real implementation rather than with the double it was written against:

    reset  leakage  session grouping  session_time  answer shape
    abstention  evidence  cost  mutation

Two verdicts are produced and kept apart, because they answer different
questions and one has been mistaken for the other before:

    validate_adapter    the frozen contract. Admissible, or not.
    operational_fit     the nine assumptions, checked against real state.

The first run of this file reported `admissible: True` for an adapter that had
ingested nothing at all, because the contract can only see what an adapter
returns and the adapter returned well-formed answers drawn from an empty store.
Admissible is not good, and it is not even *ran*.

Everything the adapter reports about the real system is recorded, including what
it cannot observe. "Cannot report token usage" is a finding about CUPMem, not a
defect in the run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import synthetic_fixture, validate_adapter  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter  # noqa: E402
from arena.cupmem_probe import CUPMemStateProbe  # noqa: E402
from arena.decoding import ARENA_DECODING, FixedDecoding  # noqa: E402
from arena.operational_fit import WriteSpy, operational_fit  # noqa: E402
from arena.record_source_provenance import describe  # noqa: E402

#: DeepSeek list price per million tokens, recorded so the projection below can
#: be checked rather than believed. Cost is bounded before the fact because a
#: background run once died after 29 calls with no result file and the spend was
#: still real.
PRICE_PER_MTOK = {"input": 0.27, "output": 1.10}

#: Refuse to start above this. The fixture is four records and six queries; a
#: projection an order of magnitude past the last measured run means something
#: is wrong with the run, not with the ceiling.
SPEND_CEILING_USD = 0.50


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


def build_engine(model_path: Path, model: str, base_url: str):
    """Construct the real engine. Import failure here is itself the verdict."""
    from openai import OpenAI

    from cup_mem.llm_layer.client import LLMClient
    from cup_mem.pipeline import CupMemEngine

    # Decoding is held constant by wrapping their provider client, so nothing in
    # `cup_mem/` differs from the commit the provenance record names.
    llm = LLMClient(
        model=model, api_key=load_key(), base_url=base_url,
        openai_cls=lambda **kwargs: FixedDecoding(OpenAI(**kwargs)),
    )
    return CupMemEngine(llm=llm, embedding_model_path=str(model_path))


def spend(cost_summary: dict) -> float:
    """Dollars for a Cost summary, or 0.0 for a field the system cannot report.

    Zeroing an unknown is exactly the collapse this project forbids, so the
    caller is given `cost_fully_known` alongside and must not read this figure
    without it.
    """
    fields = cost_summary or {}
    inp = (fields.get("input_tokens") or {}).get("value") or 0
    out = (fields.get("output_tokens") or {}).get("value") or 0
    return round(inp / 1e6 * PRICE_PER_MTOK["input"] + out / 1e6 * PRICE_PER_MTOK["output"], 6)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cupmem-root", default=str(ROOT / "external/repos/icedreamc__STALE"))
    p.add_argument("--embedding-model-path",
                   default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    p.add_argument("--model", default="deepseek-chat")
    p.add_argument("--base-url", default="https://api.deepseek.com/v1")
    p.add_argument("--out", default=str(ROOT / "data/lab/arena/cupmem-operational-fit.json"))
    p.add_argument("--projected-usd", type=float, default=0.12,
                   help="expected spend; the run refuses to start above the ceiling")
    args = p.parse_args()

    if args.projected_usd > SPEND_CEILING_USD:
        raise SystemExit(
            f"projected ${args.projected_usd:.2f} exceeds the ${SPEND_CEILING_USD:.2f} "
            "ceiling; raise it deliberately or find out why the projection grew"
        )

    root = Path(args.cupmem_root).resolve()
    sys.path.insert(0, str(root))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    engine = build_engine(Path(args.embedding_model_path), args.model, args.base_url)
    fixture = synthetic_fixture()

    # Operational fit first: it needs the write spy, and it establishes whether
    # the store was ever populated. Running the contract validator first would
    # repeat the original mistake of reading a verdict off an empty store.
    fit = operational_fit(
        CUPMemAdapter(engine), fixture,
        probe=CUPMemStateProbe(engine),
        spy_factory=lambda: WriteSpy(engine),
    )

    # The frozen contract's own verdict, run unmodified on a fresh pass.
    contract = validate_adapter(CUPMemAdapter(engine), fixture)

    usage = engine.llm.get_usage_summary()
    decoding_overrides = getattr(engine.llm.client, "overrides", None)

    record = {
        "artifact": "cupmem-operational-fit",
        "system": "CUPMem",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "against": "the real implementation, not the double",
        "measured": "adapter assumptions only; accuracy deliberately not scored",
        "source": describe(root, "cup_mem", ("*.py",)) | {"files": "<see cupmem-source-provenance.json>"},
        "embedding_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "target_model": args.model,
        "decoding": ARENA_DECODING,
        "decoding_overridden_by_system": decoding_overrides,
        "response_cache": engine.llm.cache_dir,
        "operational_fit": fit,
        "frozen_contract": contract,
        "run_usage": {
            "total_calls": usage.get("total_calls"),
            "cache_hits": usage.get("cache_hits"),
            "logical_usage": usage.get("logical_usage"),
            "billed_usage": usage.get("billed_usage"),
            "by_phase": {k: v.get("calls") for k, v in (usage.get("by_phase") or {}).items()},
        },
        "spend_usd": {
            "run_total": round(
                (usage.get("billed_usage", {}).get("prompt_tokens", 0) / 1e6
                 * PRICE_PER_MTOK["input"])
                + (usage.get("billed_usage", {}).get("completion_tokens", 0) / 1e6
                   * PRICE_PER_MTOK["output"]), 6),
            "price_per_mtok": PRICE_PER_MTOK,
            "note": "list price at run time; a projection, not an invoice",
        },
    }
    Path(args.out).write_text(json.dumps(record, indent=2, default=str) + "\n",
                              encoding="utf-8")

    print(f"operational fit    {fit['fit']}")
    for failure in fit["failures"]:
        print(f"  FAIL {failure}")
    for unknown in fit["unverifiable"]:
        print(f"  ???? {unknown}")
    print(f"  mutation         {fit['observed']['query_mutation']['reading']}")
    print(f"  sessions written {fit['observed']['session_writes']}")
    print(f"frozen contract    admissible={contract['admissible']}")
    for problem in contract["problems"]:
        print(f"  problem: {problem}")
    print(f"calls {usage.get('total_calls')}  "
          f"billed {usage.get('billed_usage')}  "
          f"${record['spend_usd']['run_total']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
