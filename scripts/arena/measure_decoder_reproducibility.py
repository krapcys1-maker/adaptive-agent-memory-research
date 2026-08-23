"""Is the arena's decoder reproducible at temperature 0? Measured, not assumed.

Why this exists
---------------
The frozen contract detects query-time state mutation by asking one probe twice
and comparing the answers. That test silently assumes a reproducible decoder: if
the model can return two different strings for one input, a read-only system
looks like a mutating one.

Two CUPMem runs at temperature 0 disagreed. The first repeated a probe
identically; the second did not, and the contract rejected an adapter whose
state fingerprint was byte-identical either side of the query. Inferring the
decoder's behaviour from a system that makes dozens of chained calls is the wrong
instrument, so this asks the provider directly.

It costs a few hundred tokens and answers a question the whole arena rests on:
whether a frozen run is reproducible, and whether a difference between two arms
can be attributed to the systems at all.

What it does not measure
------------------------
Whether *this* result generalises to another provider, another model, or the
same model next month. Reproducibility is a property of a deployment, so the
model, the date and the sample size are recorded with the number.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import ARENA_DECODING, FixedDecoding  # noqa: E402

#: Three shapes, because reproducibility can depend on what is being generated.
#: The third mirrors what every system in the arena actually asks for: a short
#: structured object, where one differing field changes a parsed decision.
PROBES = {
    "short_factual": "Reply with only the capital city of France. One word.",
    "free_form": ("In two sentences, describe why a memory system should keep "
                  "the record that a fact was superseded."),
    "structured_json": (
        'Output JSON only: {"status": one of SUPPORTED|OUTDATED|UNRESOLVED, '
        '"reason": "one short sentence"}. '
        'The stored fact is "billing staging is https://a.internal:8443" from day 1. '
        'A later record says "billing staging is now https://c.internal:8443" on day 9. '
        'The question asks which host a billing deploy should target today.'
    ),
}


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--out",
                        default=str(ROOT / "data/lab/arena/decoder-reproducibility.json"))
    args = parser.parse_args()

    from openai import OpenAI

    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url))

    results: dict[str, dict] = {}
    for name, prompt in PROBES.items():
        draws = [
            client.chat.completions.create(
                model=args.model, messages=[{"role": "user", "content": prompt}],
            ).choices[0].message.content or ""
            for _ in range(args.repeats)
        ]
        counts = Counter(draws)
        results[name] = {
            "repeats": args.repeats,
            "distinct_outputs": len(counts),
            # The share of draws equal to the most common one. 1.0 is a decoder
            # that repeated itself; anything less is variance the contract's
            # mutation check would read as a store that learned.
            "modal_share": round(max(counts.values()) / args.repeats, 4),
            "reproducible": len(counts) == 1,
            "samples": [text[:400] for text in sorted(counts)][:3],
        }

    ledger = client.ledger
    record = {
        "artifact": "arena-decoder-reproducibility",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": ("does the arena's fixed decoding make a repeated identical "
                     "request return an identical answer"),
        "why_it_matters": (
            "the frozen contract detects query-time state mutation by repeating a "
            "probe and comparing outputs. Without a reproducible decoder that test "
            "cannot separate a store that learned from a decoder that drew "
            "differently, and it rejected an adapter whose state digest was "
            "identical either side of the query"
        ),
        "model": args.model,
        "base_url": args.base_url,
        "decoding": ARENA_DECODING,
        "results": results,
        "reproducible_everywhere": all(r["reproducible"] for r in results.values()),
        "usage": ledger,
        "scope": ("one provider, one model, one day, "
                  f"{args.repeats} draws per probe. Reproducibility is a property "
                  "of a deployment, not of a temperature setting"),
    }
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")

    for name, result in results.items():
        print(f"{name:16s} distinct {result['distinct_outputs']}/{result['repeats']}  "
              f"modal share {result['modal_share']}  "
              f"reproducible {result['reproducible']}")
    print(f"usage {ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
