"""Fresh descriptive runs on an explicit memory snapshot; never historical backfill.

No API model is called. Dense retrieval is optional and must use an existing
cache with local_files_only=True. New output directories only; the memory log
and all historical result files are preserved. Index caches are disposable.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from unittest import mock

import run_association_graph_e3 as association
import run_corpus_h1_address_probe as address
import run_corpus_h1_baseline as baseline
import run_cross_language_e1 as xlang

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="explicit source snapshot, not a historical-rerun claim")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dense-cache", type=Path, help="existing FastEmbed cache; downloads are disabled")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output must be a new directory")
    memory = args.root / "memory/events.jsonl"
    before = digest(memory)
    args.output.mkdir(parents=True)
    metadata = {"measurement": "fresh-snapshot, not historical reconstruction",
                "snapshot_git_head": revision(args.root), "runner_git_head": revision(ROOT),
                "memory_sha256": before, "model_api_calls": 0, "model_downloads": 0,
                "dense_status": "not_requested", "runs": {}}

    def save(name, result):
        (args.output / (name + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
        metadata["runs"][name] = {"status": "completed", "records": len(result.get("records", []))}
        print(name, "records=" + str(len(result.get("records", []))), flush=True)

    save("xlang-e1", xlang.run(args.root))
    save("association-e3", association.run(args.root))
    corpus = args.root / "data/lab/corpus-h1"
    save("h1-baseline", baseline.run(corpus))
    save("h1-address", address.run(corpus, 1000))
    if args.dense_cache:
        import fastembed
        import run_cross_language_e2 as dense
        original = fastembed.TextEmbedding
        dense.CACHE = args.dense_cache
        metadata["fastembed_version"] = importlib.metadata.version("fastembed")
        metadata["dense_model"] = dense.MODEL
        metadata["dense_pooling_caveat"] = "Installed FastEmbed warns this model alias changed pooling after 0.5.1; these fresh numbers are not a replication of older dense results."

        def offline_model(**kwargs):
            return original(**kwargs, local_files_only=True, providers=["CPUExecutionProvider"])

        try:
            with mock.patch.object(fastembed, "TextEmbedding", offline_model):
                save("xlang-e2", dense.run(args.root))
            metadata["dense_status"] = "completed-existing-cache-offline"
        except (OSError, ValueError) as exc:
            metadata["dense_status"] = "unavailable-offline-cache-" + type(exc).__name__
    metadata["memory_unchanged"] = digest(memory) == before
    (args.output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not metadata["memory_unchanged"]:
        raise ValueError("source memory changed during measurement")
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
