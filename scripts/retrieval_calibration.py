#!/usr/bin/env python3
"""AAM-E3A: calibrate a relevance threshold for own-history memory on an account's real published notes.

For every note, the three most similar EARLIER notes by embedding cosine are put to a blind judge ("would being reminded of the
earlier note help the author who is writing this one?", 0 to 2), together with one random earlier note per note as a negative
control. From the judgments: how often a retrieved note is relevant at each cosine, which threshold keeps the injected notes
relevant, and what share of notes would receive any memory at all. Pair-level judgments hold indices, cosines and ratings, never
text, and stay local; the analysis prints aggregates only.

Usage:
  python scripts/retrieval_calibration.py run items.jsonl --out judgments.jsonl --base-url http://127.0.0.1:8798/v1 --model deepseek-v4-pro [--workers 12]
  python scripts/retrieval_calibration.py analyse judgments.jsonl [--json OUT.json] [--md OUT.md]
The run needs the optional sentence-transformers package with a local copy of the embedding model, and an OpenAI-compatible endpoint
(a local metering proxy for a paid API) or --backend ollama.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_backends as backends  # noqa: E402
import published_notes_baseline as pnb  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

TOP_K = 3
CONTROL_SEED = 2026
TAUS = (0.5, 0.55, 0.6, 0.65, 0.7)
BINS = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.01)
PRECISION_NEEDED = 0.80       # share of injected notes rated 1 or 2 that makes a threshold usable
COVERAGE_NEEDED = 0.10        # share of notes that must receive at least one injected note
CONTROL_ZERO_NEEDED = 0.90    # share of random negative controls the judge must rate 0, or the judge is declared unreliable
JUDGE_SYSTEM = "You are a careful editor. Reply with one line only."
JUDGE_OPTS = {"temperature": 0.0, "top_p": 1.0, "num_predict": 20}
JUDGE_SEED = 11
RELEVANCE = re.compile(r"(?im)^\W*relevance\W*[:=]\s*([0-2])\b")


def candidate_pairs(vectors: Sequence[Sequence[float]], k: int = TOP_K) -> List[dict]:
    """Per note (the first has no history) its k most similar earlier notes by cosine; ties go to the more recent."""
    pairs = []
    for i in range(1, len(vectors)):
        sims = sorted(((pnb.dot(vectors[i], vectors[j]), j) for j in range(i)), key=lambda p: (-p[0], -p[1]))[:k]
        pairs += [{"i": i, "j": j, "cos": round(c, 4), "kind": "top%d" % rank} for rank, (c, j) in enumerate(sims, 1)]
    return pairs


def control_pairs(vectors: Sequence[Sequence[float]], taken: Sequence[dict], seed: int = CONTROL_SEED) -> List[dict]:
    """One random earlier note per note (never one of its top-k), as a negative control for the judge."""
    rng = sim.Lcg(seed)
    skip = {(p["i"], p["j"]) for p in taken}
    out = []
    for i in range(TOP_K + 1, len(vectors)):
        options = [j for j in range(i) if (i, j) not in skip]
        j = options[rng.next() % len(options)]
        out.append({"i": i, "j": j, "cos": round(pnb.dot(vectors[i], vectors[j]), 4), "kind": "control"})
    return out


def judge_prompt(new_note: str, earlier_note: str) -> str:
    return ("Two notes by the same author, written on different days.\n\nNEW NOTE (the one being written):\n%s\n\nEARLIER NOTE (written before it):\n%s\n\n"
            "If the author were writing the new note, would being reminded of the earlier note help?\nScore:\n"
            "0 = unrelated, or only a very loose connection\n1 = the same general area but a different point\n"
            "2 = the same specific story, claim or question, or a direct follow-up\n\nReply with one line in the form RELEVANCE: <0-2>."
            % (new_note, earlier_note))


def parse_relevance(raw: str) -> Optional[int]:
    match = RELEVANCE.search(raw)
    return int(match.group(1)) if match else None


def key(pair: dict) -> Tuple:
    return (pair["i"], pair["j"], pair["kind"])


def run(items: Sequence[sbm.Item], vectors: Sequence[Sequence[float]], out: Path, generate: backends.Generate, workers: int = 8, log=print) -> int:
    top = candidate_pairs(vectors)
    pairs = top + control_pairs(vectors, top)
    done = set()
    if out.exists():
        done = {key(json.loads(line)) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()}
    todo = [p for p in pairs if key(p) not in done]
    lock, written = threading.Lock(), 0

    def one(pair: dict) -> dict:
        raw = str(generate(JUDGE_SYSTEM, judge_prompt(items[pair["i"]].text, items[pair["j"]].text), JUDGE_SEED, JUDGE_OPTS)["text"])
        return dict(pair, relevance=parse_relevance(raw), raw=raw.strip()[:60])

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool, out.open("a", encoding="utf-8") as handle:
        for future in as_completed([pool.submit(one, p) for p in todo]):
            row = future.result()
            with lock:
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                written += 1
                if written % 100 == 0:
                    log("judged %d/%d" % (written, len(todo)))
    return written


def wilson(successes: int, total: int, z: float = 1.96) -> Optional[Tuple[float, float]]:
    if not total:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return round(centre - half, 4), round(centre + half, 4)


def share(count: int, total: int) -> Optional[float]:
    return round(count / total, 4) if total else None


def analyse(judgments: Sequence[dict], n_notes: Optional[int] = None) -> dict:
    scored = [j for j in judgments if j.get("relevance") is not None]
    top = [j for j in scored if j["kind"].startswith("top")]
    controls = [j for j in scored if j["kind"] == "control"]
    n_notes = n_notes or (max(j["i"] for j in judgments) + 1 if judgments else 0)
    with_history = max(1, n_notes - 1)
    bins = []
    for low, high in zip(BINS, BINS[1:]):
        inside = [j for j in top + controls if low <= j["cos"] < high]
        bins.append({"cos_from": low, "cos_to": min(high, 1.0), "pairs": len(inside), "rated_0": share(sum(j["relevance"] == 0 for j in inside), len(inside)),
                     "rated_1": share(sum(j["relevance"] == 1 for j in inside), len(inside)),
                     "rated_2": share(sum(j["relevance"] == 2 for j in inside), len(inside))})
    thresholds = {}
    for tau in TAUS:
        injected = [j for j in top if j["cos"] >= tau]
        notes_served = len({j["i"] for j in injected})
        useful = sum(j["relevance"] >= 1 for j in injected)
        thresholds[str(tau)] = {"injected_pairs": len(injected), "notes_served": notes_served, "coverage": share(notes_served, with_history),
                                "mean_injected_per_note": round(len(injected) / with_history, 3),
                                "precision_rated_1_or_2": share(useful, len(injected)), "precision_interval": wilson(useful, len(injected)),
                                "precision_rated_2": share(sum(j["relevance"] == 2 for j in injected), len(injected)),
                                "noise_rated_0": share(sum(j["relevance"] == 0 for j in injected), len(injected))}
    usable = [tau for tau in TAUS if thresholds[str(tau)]["precision_rated_1_or_2"] is not None
              and thresholds[str(tau)]["precision_rated_1_or_2"] >= PRECISION_NEEDED and thresholds[str(tau)]["coverage"] >= COVERAGE_NEEDED]
    zero = share(sum(j["relevance"] == 0 for j in controls), len(controls))
    return {"notes": n_notes, "judged_pairs": len(scored), "unparsed": len(judgments) - len(scored),
            "controls": {"pairs": len(controls), "rated_0": zero, "judge_reliable": None if zero is None else zero >= CONTROL_ZERO_NEEDED,
                         "mean_cosine": round(sum(j["cos"] for j in controls) / len(controls), 4) if controls else None},
            "calibration_by_cosine": bins, "by_threshold": thresholds,
            "rule": {"precision_needed": PRECISION_NEEDED, "coverage_needed": COVERAGE_NEEDED, "control_zero_needed": CONTROL_ZERO_NEEDED},
            "lowest_usable_threshold": usable[0] if usable else None}


def fmt(value: Optional[float]) -> str:
    return "-" if value is None else "%.3f" % value


def report(result: dict) -> str:
    c = result["controls"]
    out = ["# AAM-E3A retrieval calibration", "", "Notes: %d; judged pairs: %d (unparsed replies: %d); random negative controls rated 0: %s of %d (judge reliable: %s)." % (
        result["notes"], result["judged_pairs"], result["unparsed"], fmt(c["rated_0"]), c["pairs"], c["judge_reliable"]), "",
        "## Relevance by cosine", "", "| cosine | pairs | rated 0 | rated 1 | rated 2 |", "|---|---|---|---|---|"]
    out += ["| %.2f-%.2f | %d | %s | %s | %s |" % (b["cos_from"], b["cos_to"], b["pairs"], fmt(b["rated_0"]), fmt(b["rated_1"]), fmt(b["rated_2"])) for b in result["calibration_by_cosine"]]
    out += ["", "## Injection at a threshold (up to three most similar earlier notes with cosine at least tau)", "",
            "| tau | injected | notes served | coverage | per note | precision (1 or 2) | interval | rated 2 | noise (0) |", "|---|---|---|---|---|---|---|---|---|"]
    for tau, t in result["by_threshold"].items():
        out.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (tau, t["injected_pairs"], t["notes_served"], fmt(t["coverage"]), fmt(t["mean_injected_per_note"]),
                                                                       fmt(t["precision_rated_1_or_2"]), t["precision_interval"], fmt(t["precision_rated_2"]), fmt(t["noise_rated_0"])))
    out += ["", "Lowest threshold with precision of at least %.2f and coverage of at least %.2f: **%s**" % (
        result["rule"]["precision_needed"], result["rule"]["coverage_needed"], result["lowest_usable_threshold"])]
    return "\n".join(out) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate a relevance threshold for own-history memory on real published notes.")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("items")
    run_p.add_argument("--out", type=Path, required=True)
    run_p.add_argument("--model", default="deepseek-v4-pro")
    run_p.add_argument("--backend", choices=("ollama", "openai"), default="openai")
    run_p.add_argument("--base-url", default="http://127.0.0.1:8798/v1")
    run_p.add_argument("--embedding-model", default="sentence-transformers/all-MiniLM-L6-v2")
    run_p.add_argument("--workers", type=int, default=8)
    an_p = sub.add_parser("analyse")
    an_p.add_argument("judgments", type=Path)
    an_p.add_argument("--json", type=Path, default=None)
    an_p.add_argument("--md", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            with open(args.items, encoding="utf-8") as handle:
                items = sbm.parse_items(handle)
            vectors = pnb.embed_texts([i.text for i in items], args.embedding_model)
            generate = backends.ollama_generate(args.model) if args.backend == "ollama" else backends.openai_generate(args.base_url, args.model)
            print("done: %d new judgments" % run(items, vectors, args.out, generate, args.workers, log=lambda line: print(line, flush=True)))
            return 0
        judgments = [json.loads(line) for line in args.judgments.read_text(encoding="utf-8").splitlines() if line.strip()]
        result = analyse(judgments)
        result["provenance"] = {"judgments_sha256": hashlib.sha256(args.judgments.read_bytes()).hexdigest(),
                                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    except (OSError, ValueError, ImportError, backends.SpendCapRefused) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    text = report(result)
    if args.md:
        args.md.write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
