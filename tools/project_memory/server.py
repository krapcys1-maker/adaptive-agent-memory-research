#!/usr/bin/env python3
"""Minimal dependency-free MCP stdio server for project memory.

Protocol messages are newline-delimited JSON-RPC. Nothing except protocol
messages is written to stdout; diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.project_memory.memory_store import (  # noqa: E402
    CONTEXT_STATE_SHARE,
    MemoryError,
    MemoryStore,
)


SERVER_INFO = {"name": "adaptive-agent-project-memory", "version": "0.1.0"}


def _tool(
    name: str,
    description: str,
    schema: dict[str, Any],
    *,
    read_only: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {"type": "object", "additionalProperties": False, **schema},
        "annotations": {
            "readOnlyHint": read_only,
            "destructiveHint": False,
            "idempotentHint": read_only,
            "openWorldHint": False,
        },
    }


TOOLS = [
    _tool(
        "memory_status",
        "Inspect project-memory health, counts, index state, and whether any model API is required.",
        {"properties": {}},
        read_only=True,
    ),
    _tool(
        "memory_search",
        "Search active structured memories and project research documents using local full-text search.",
        {
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "kinds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional exact kinds such as memory:decision or document.",
                },
                "expand": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "Expand the query through memory/glossary.json so a question asked in "
                        "one language can reach records written in another. Set false to see "
                        "raw lexical behaviour."
                    ),
                },
            },
            "required": ["query"],
        },
        read_only=True,
    ),
    _tool(
        "memory_context",
        "Build a compact context bundle from current state, memories, and research files for a task.",
        {
            "properties": {
                "query": {"type": "string"},
                "char_budget": {"type": "integer", "minimum": 1000, "maximum": 50000, "default": 12000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 12},
                "state_share": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": CONTEXT_STATE_SHARE,
                    "description": (
                        "Largest share of the budget the canonical state summary may take. "
                        "The remainder is reserved for retrieved evidence."
                    ),
                },
            },
            "required": ["query"],
        },
        read_only=True,
    ),
    _tool(
        "memory_get",
        "Retrieve one structured memory by stable ID, including whether it is still active.",
        {"properties": {"memory_id": {"type": "string"}}, "required": ["memory_id"]},
        read_only=True,
    ),
    _tool(
        "memory_timeline",
        "List recent append-only memory events in reverse chronological order.",
        {
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
                "kind": {"type": "string", "default": ""},
            }
        },
        read_only=True,
    ),
    _tool(
        "memory_add",
        "Append a durable typed project memory. Use source_refs for factual findings and decisions.",
        {
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["candidate", "constraint", "decision", "failure", "finding", "hypothesis", "procedure", "question", "session"],
                },
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "body": {"type": "string", "default": ""},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "enum": ["unknown", "low", "medium", "high"], "default": "unknown"},
                "status": {"type": "string", "default": "active"},
                "related_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["kind", "title", "summary"],
        },
        read_only=False,
    ),
    _tool(
        "memory_supersede",
        "Replace an active memory with a new version while retaining provenance and full history.",
        {
            "properties": {
                "memory_id": {"type": "string"},
                "reason": {"type": "string"},
                "title": {"type": "string", "default": ""},
                "summary": {"type": "string", "default": ""},
                "body": {"type": "string", "default": ""},
                "tags": {"type": "array", "items": {"type": "string"}},
                "source_refs": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "string", "default": ""},
                "status": {"type": "string", "default": ""},
            },
            "required": ["memory_id", "reason"],
        },
        read_only=False,
    ),
    _tool(
        "memory_rebuild_index",
        "Rebuild the disposable local SQLite FTS index from Git-tracked source files.",
        {"properties": {}},
        read_only=False,
    ),
]


class McpServer:
    def __init__(self, store: MemoryStore):
        self.store = store

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        handlers: dict[str, Callable[[], Any]] = {
            "memory_status": lambda: self.store.status(),
            "memory_search": lambda: self.store.search(
                arguments.get("query", ""),
                arguments.get("limit", 10),
                arguments.get("kinds"),
                arguments.get("expand", True),
            ),
            "memory_context": lambda: self.store.context(
                arguments.get("query", ""),
                arguments.get("char_budget", 12000),
                arguments.get("limit", 12),
                arguments.get("state_share", CONTEXT_STATE_SHARE),
            ),
            "memory_get": lambda: self.store.get(arguments.get("memory_id", "")),
            "memory_timeline": lambda: self.store.timeline(
                arguments.get("limit", 20), arguments.get("kind", "")
            ),
            "memory_add": lambda: self.store.add(**arguments),
            "memory_supersede": lambda: self.store.supersede(**arguments),
            "memory_rebuild_index": lambda: self.store.rebuild_index(),
        }
        if name not in handlers:
            raise MemoryError(f"unknown tool: {name}")
        return handlers[name]()

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            return None
        if method == "initialize":
            requested = request.get("params", {}).get("protocolVersion", "2024-11-05")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": requested,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": SERVER_INFO,
                    "instructions": "Search memory before research; append durable findings with provenance; supersede instead of deleting.",
                },
            }
        if method == "ping":
            result: Any = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request.get("params", {})
            value = self.call_tool(params.get("name", ""), params.get("arguments") or {})
            result = {
                "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
                "structuredContent": {"result": value},
                "isError": False,
            }
        elif method in {"resources/list", "prompts/list"}:
            result = {"resources": []} if method == "resources/list" else {"prompts": []}
        elif method in {"logging/setLevel", "shutdown"}:
            result = {}
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _resolve_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    claude_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if claude_root:
        return Path(claude_root).resolve()
    return Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    args = parser.parse_args()
    server = McpServer(MemoryStore(_resolve_root(args.root)))

    for line in sys.stdin:
        if not line.strip():
            continue
        request_id: Any = None
        try:
            request = json.loads(line)
            request_id = request.get("id") if isinstance(request, dict) else None
            if not isinstance(request, dict):
                raise MemoryError("request must be a JSON object")
            response = server.handle(request)
            if response is not None:
                print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
        except Exception as exc:  # server boundary: convert failures into MCP errors
            traceback.print_exc(file=sys.stderr)
            if request_id is not None:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": f"error: {exc}"}],
                        "isError": True,
                    },
                }
                print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
