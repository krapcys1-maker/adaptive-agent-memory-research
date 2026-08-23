"""Operational fit for CUPMem: does the real system confirm the adapter's assumptions?

Accuracy is not measured here and a wrong answer does not fail this run. The
question is only whether the eight assumptions the adapter encodes survive
contact with the real implementation rather than with the double it was
written against:

    reset  ingest  query  return shape  abstention  evidence  cost  mutation

Everything the adapter reports about the real system is recorded, including
what it cannot observe. "Cannot report token usage" is a finding about
CUPMem, not a defect in the run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import synthetic_fixture, validate_adapter  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter  # noqa: E402


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


def build_engine(model_path: Path, model: str, base_url: str):
    """Construct the real engine. Import failure here is itself the verdict."""
    from cup_mem.llm_layer.client import LLMClient
    from cup_mem.pipeline import CupMemEngine

    llm = LLMClient(model=model, api_key=load_key(), base_url=base_url)
    return CupMemEngine(llm=llm, embedding_model_path=str(model_path))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cupmem-root", required=True)
    p.add_argument("--embedding-model-path",
                   default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    p.add_argument("--model", default="deepseek-chat")
    p.add_argument("--base-url", default="https://api.deepseek.com/v1")
    p.add_argument("--out", default=str(ROOT / "data/lab/arena/cupmem-operational-fit.json"))
    args = p.parse_args()

    sys.path.insert(0, str(Path(args.cupmem_root).resolve()))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    engine = build_engine(Path(args.embedding_model_path), args.model, args.base_url)
    result = validate_adapter(CUPMemAdapter(engine), synthetic_fixture())

    record = {
        "artifact": "cupmem-operational-fit",
        "system": "CUPMem",
        "against": "the real implementation, not the double",
        "measured": "adapter assumptions only; accuracy deliberately not scored",
        "embedding_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "target_model": args.model,
        "result": result,
    }
    Path(args.out).write_text(json.dumps(record, indent=2, default=str) + "\n",
                              encoding="utf-8")

    print(f"admissible          {result['admissible']}")
    print(f"query_mutates_state {result['query_mutates_state']}")
    print(f"repeat differed     {result['repeated_query_differed']}")
    print(f"cost fully known    {result['cost_fully_known']}")
    print(f"cost is lower bound {result['cost_is_lower_bound']}")
    for problem in result["problems"]:
        print(f"  problem: {problem}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
