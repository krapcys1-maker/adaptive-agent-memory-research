#!/usr/bin/env python3
"""Command-line fallback for the project memory store."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.project_memory.memory_store import ALLOWED_KINDS, MemoryError, MemoryStore  # noqa: E402


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local provider-neutral project memory")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("status")
    commands.add_parser("rebuild")

    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--kind", action="append", dest="kinds")

    context = commands.add_parser("context")
    context.add_argument("query")
    context.add_argument("--char-budget", type=int, default=12000)

    timeline = commands.add_parser("timeline")
    timeline.add_argument("--limit", type=int, default=20)
    timeline.add_argument("--kind", default="")

    get = commands.add_parser("get")
    get.add_argument("memory_id")

    add = commands.add_parser("add")
    add.add_argument("--kind", required=True, choices=sorted(ALLOWED_KINDS))
    add.add_argument("--title", required=True)
    add.add_argument("--summary", required=True)
    add.add_argument("--body", default="")
    add.add_argument("--tag", action="append", dest="tags")
    add.add_argument("--source", action="append", dest="source_refs")
    add.add_argument("--confidence", default="unknown", choices=["unknown", "low", "medium", "high"])
    add.add_argument("--status", default="active")

    supersede = commands.add_parser("supersede")
    supersede.add_argument("memory_id")
    supersede.add_argument("--reason", required=True)
    supersede.add_argument("--title", default="")
    supersede.add_argument("--summary", default="")
    supersede.add_argument("--body", default="")
    supersede.add_argument("--tag", action="append", dest="tags")
    supersede.add_argument("--source", action="append", dest="source_refs")
    supersede.add_argument("--confidence", default="")
    supersede.add_argument("--status", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    store = MemoryStore(args.root)
    try:
        if args.command == "status":
            result = store.status()
        elif args.command == "rebuild":
            result = store.rebuild_index()
        elif args.command == "search":
            result = store.search(args.query, args.limit, args.kinds)
        elif args.command == "context":
            result = store.context(args.query, args.char_budget)
        elif args.command == "timeline":
            result = store.timeline(args.limit, args.kind)
        elif args.command == "get":
            result = store.get(args.memory_id)
        elif args.command == "add":
            result = store.add(
                kind=args.kind,
                title=args.title,
                summary=args.summary,
                body=args.body,
                tags=args.tags,
                source_refs=args.source_refs,
                confidence=args.confidence,
                status=args.status,
            )
        elif args.command == "supersede":
            result = store.supersede(
                memory_id=args.memory_id,
                reason=args.reason,
                title=args.title,
                summary=args.summary,
                body=args.body,
                tags=args.tags,
                source_refs=args.source_refs,
                confidence=args.confidence,
                status=args.status,
            )
        else:
            raise AssertionError(args.command)
        _print(result)
        return 0
    except (MemoryError, OSError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
