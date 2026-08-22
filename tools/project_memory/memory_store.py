"""Append-only project memory with a rebuildable SQLite FTS5 index.

The Git-tracked JSONL and Markdown files are the source of truth. SQLite is
only a cache and may be deleted or rebuilt at any time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
ALLOWED_KINDS = {
    "candidate",
    "constraint",
    "decision",
    "failure",
    "finding",
    "hypothesis",
    "procedure",
    "question",
    "session",
}
ALLOWED_CONFIDENCE = {"unknown", "low", "medium", "high"}
TEXT_EXTENSIONS = {
    ".bib",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".git",
    ".index",
    ".venv",
    "__pycache__",
    "node_modules",
}
EXCLUDED_PREFIXES = {
    "data/snapshots",
    "external/repos",
    "sources/papers",
}
MAX_INDEXED_FILE_BYTES = 5 * 1024 * 1024


class MemoryError(ValueError):
    """Raised when a memory operation is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return f"PM-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8]}"


def _clean_string(value: Any, field: str, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise MemoryError(f"{field} must be a string")
    value = value.strip()
    if required and not value:
        raise MemoryError(f"{field} is required")
    return value


def _clean_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",") if part.strip()]
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise MemoryError(f"{field} must be a list of strings")
    return list(dict.fromkeys(item.strip() for item in value if item.strip()))


class MemoryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.memory_dir = self.root / "memory"
        self.events_path = self.memory_dir / "events.jsonl"
        self.index_dir = self.memory_dir / ".index"
        self.index_path = self.index_dir / "project_memory.sqlite3"
        self.lock_path = self.memory_dir / ".events.lock"
        self.index_lock_path = self.memory_dir / ".index.lock"

    def initialize(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.events_path.touch(exist_ok=True)

    @contextmanager
    def _exclusive_lock(self, lock_path: Path, timeout: float = 10.0):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + timeout
        while True:
            try:
                descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(descriptor, f"{os.getpid()} {_utc_now()}".encode("utf-8"))
                os.close(descriptor)
                break
            except FileExistsError:
                try:
                    if time.time() - lock_path.stat().st_mtime > 120:
                        lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise MemoryError(f"memory lock is busy: {lock_path.name}")
                time.sleep(0.05)
        try:
            yield
        finally:
            lock_path.unlink(missing_ok=True)

    def _append(self, event: dict[str, Any]) -> dict[str, Any]:
        self.initialize()
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with self._exclusive_lock(self.lock_path):
            with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        self.rebuild_index()
        return event

    def add(
        self,
        *,
        kind: str,
        title: str,
        summary: str,
        body: str = "",
        tags: list[str] | str | None = None,
        source_refs: list[str] | str | None = None,
        confidence: str = "unknown",
        status: str = "active",
        related_ids: list[str] | str | None = None,
    ) -> dict[str, Any]:
        kind = _clean_string(kind, "kind", True).lower()
        if kind not in ALLOWED_KINDS:
            raise MemoryError(f"kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}")
        confidence = _clean_string(confidence, "confidence", True).lower()
        if confidence not in ALLOWED_CONFIDENCE:
            raise MemoryError("confidence must be unknown, low, medium, or high")
        event = {
            "schema_version": SCHEMA_VERSION,
            "id": _new_id(),
            "operation": "create",
            "kind": kind,
            "title": _clean_string(title, "title", True),
            "summary": _clean_string(summary, "summary", True),
            "body": _clean_string(body, "body"),
            "tags": _clean_list(tags, "tags"),
            "source_refs": _clean_list(source_refs, "source_refs"),
            "confidence": confidence,
            "status": _clean_string(status, "status", True),
            "created_at": _utc_now(),
            "supersedes": None,
            "related_ids": _clean_list(related_ids, "related_ids"),
        }
        return self._append(event)

    def supersede(
        self,
        *,
        memory_id: str,
        reason: str,
        title: str = "",
        summary: str = "",
        body: str = "",
        tags: list[str] | str | None = None,
        source_refs: list[str] | str | None = None,
        confidence: str = "",
        status: str = "",
    ) -> dict[str, Any]:
        memory_id = _clean_string(memory_id, "memory_id", True)
        current = self.get(memory_id)
        if not current:
            raise MemoryError(f"unknown memory id: {memory_id}")
        if not current["is_active"]:
            raise MemoryError(f"memory is already superseded: {memory_id}")
        previous = current["event"]
        new_confidence = confidence.strip().lower() if confidence else previous["confidence"]
        if new_confidence not in ALLOWED_CONFIDENCE:
            raise MemoryError("confidence must be unknown, low, medium, or high")
        new_tags = _clean_list(tags, "tags") if tags is not None else previous.get("tags", [])
        new_sources = (
            _clean_list(source_refs, "source_refs")
            if source_refs is not None
            else previous.get("source_refs", [])
        )
        event = {
            "schema_version": SCHEMA_VERSION,
            "id": _new_id(),
            "operation": "supersede",
            "kind": previous["kind"],
            "title": _clean_string(title, "title") or previous["title"],
            "summary": _clean_string(summary, "summary") or previous["summary"],
            "body": _clean_string(body, "body") or previous.get("body", ""),
            "tags": new_tags,
            "source_refs": new_sources,
            "confidence": new_confidence,
            "status": _clean_string(status, "status") or previous["status"],
            "created_at": _utc_now(),
            "supersedes": memory_id,
            "supersession_reason": _clean_string(reason, "reason", True),
            "related_ids": previous.get("related_ids", []),
        }
        return self._append(event)

    def load_events(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        self.initialize()
        events: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        with self.events_path.open("r", encoding="utf-8-sig") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict) or not value.get("id"):
                        raise ValueError("event must be an object with an id")
                    events.append(value)
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append({"line": line_number, "error": str(exc)})
        return events, errors

    def current_records(self) -> tuple[dict[str, dict[str, Any]], set[str], list[dict[str, Any]]]:
        events, errors = self.load_events()
        records: dict[str, dict[str, Any]] = {}
        superseded: set[str] = set()
        for event in events:
            target = event.get("supersedes")
            if target:
                superseded.add(str(target))
            if event.get("operation") in {"create", "supersede"}:
                records[str(event["id"])] = event
        return records, superseded, errors

    def get(self, memory_id: str) -> dict[str, Any] | None:
        records, superseded, _ = self.current_records()
        event = records.get(memory_id)
        if not event:
            return None
        return {"event": event, "is_active": memory_id not in superseded}

    def timeline(self, limit: int = 20, kind: str = "") -> list[dict[str, Any]]:
        events, _ = self.load_events()
        if kind:
            events = [event for event in events if event.get("kind") == kind]
        return list(reversed(events[-max(1, min(limit, 200)) :]))

    def _iter_documents(self) -> Iterable[Path]:
        for directory, child_directories, filenames in os.walk(self.root):
            directory_path = Path(directory)
            relative_directory = directory_path.relative_to(self.root)
            kept: list[str] = []
            for name in child_directories:
                candidate = (relative_directory / name).as_posix()
                if name in EXCLUDED_PARTS:
                    continue
                if any(candidate == prefix or candidate.startswith(prefix + "/") for prefix in EXCLUDED_PREFIXES):
                    continue
                kept.append(name)
            child_directories[:] = kept
            for filename in filenames:
                path = directory_path / filename
                if path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                if path == self.events_path or path.stat().st_size > MAX_INDEXED_FILE_BYTES:
                    continue
                yield path

    def _manifest_signature(self) -> str:
        hasher = hashlib.sha256()
        if self.events_path.exists():
            stat = self.events_path.stat()
            hasher.update(f"events:{stat.st_size}:{stat.st_mtime_ns}".encode())
        for path in sorted(self._iter_documents()):
            stat = path.stat()
            hasher.update(str(path.relative_to(self.root)).encode("utf-8"))
            hasher.update(f":{stat.st_size}:{stat.st_mtime_ns}".encode())
        return hasher.hexdigest()

    def rebuild_index(self) -> dict[str, Any]:
        self.initialize()
        with self._exclusive_lock(self.index_lock_path):
            records, superseded, errors = self.current_records()
            documents = list(self._iter_documents())
            temporary = self.index_path.with_suffix(f".{os.getpid()}.tmp")
            temporary.unlink(missing_ok=True)
            connection = sqlite3.connect(temporary)
            try:
                connection.executescript(
                    """
                    PRAGMA journal_mode=OFF;
                    PRAGMA synchronous=OFF;
                    CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE VIRTUAL TABLE search_fts USING fts5(
                        kind UNINDEXED, key UNINDEXED, title, body, metadata,
                        tokenize='unicode61 remove_diacritics 2'
                    );
                    """
                )
                for memory_id, event in records.items():
                    if memory_id in superseded:
                        continue
                    metadata = json.dumps(
                        {
                            "confidence": event.get("confidence"),
                            "created_at": event.get("created_at"),
                            "source_refs": event.get("source_refs", []),
                            "status": event.get("status"),
                            "tags": event.get("tags", []),
                        },
                        ensure_ascii=False,
                    )
                    body = "\n".join(filter(None, [event.get("summary", ""), event.get("body", "")]))
                    connection.execute(
                        "INSERT INTO search_fts(kind, key, title, body, metadata) VALUES (?, ?, ?, ?, ?)",
                        (f"memory:{event.get('kind', 'unknown')}", memory_id, event.get("title", ""), body, metadata),
                    )
                indexed_documents = 0
                for path in documents:
                    try:
                        content = path.read_text(encoding="utf-8-sig", errors="replace")
                    except OSError:
                        continue
                    relative = path.relative_to(self.root).as_posix()
                    title = next(
                        (line.lstrip("# ").strip() for line in content.splitlines() if line.strip().startswith("#")),
                        path.name,
                    )
                    connection.execute(
                        "INSERT INTO search_fts(kind, key, title, body, metadata) VALUES (?, ?, ?, ?, ?)",
                        ("document", relative, title, content, json.dumps({"path": relative})),
                    )
                    indexed_documents += 1
                signature = self._manifest_signature()
                connection.executemany(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)",
                    [
                        ("schema_version", str(SCHEMA_VERSION)),
                        ("manifest_signature", signature),
                        ("built_at", _utc_now()),
                    ],
                )
                connection.commit()
            finally:
                connection.close()
            os.replace(temporary, self.index_path)
        return {
            "active_memories": len(records) - len(set(records) & superseded),
            "documents": indexed_documents,
            "event_errors": errors,
            "index": str(self.index_path),
        }

    def _ensure_index(self) -> None:
        self.initialize()
        if not self.index_path.exists():
            self.rebuild_index()
            return
        try:
            connection = sqlite3.connect(self.index_path)
            stored = connection.execute(
                "SELECT value FROM metadata WHERE key='manifest_signature'"
            ).fetchone()
            connection.close()
            if not stored or stored[0] != self._manifest_signature():
                self.rebuild_index()
        except sqlite3.DatabaseError:
            self.rebuild_index()

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
        if not tokens:
            raise MemoryError("query must contain at least one word or number")
        return " OR ".join(f'"{token}"' for token in tokens[:32])

    def search(self, query: str, limit: int = 10, kinds: list[str] | str | None = None) -> list[dict[str, Any]]:
        self._ensure_index()
        fts_query = self._fts_query(_clean_string(query, "query", True))
        limit = max(1, min(int(limit), 50))
        kind_filters = _clean_list(kinds, "kinds")
        sql = """
            SELECT kind, key, title,
                   snippet(search_fts, 3, '[', ']', ' ... ', 24) AS excerpt,
                   bm25(search_fts, 0.0, 0.0, 4.0, 1.0, 0.25) AS rank
            FROM search_fts
            WHERE search_fts MATCH ?
        """
        parameters: list[Any] = [fts_query]
        if kind_filters:
            placeholders = ",".join("?" for _ in kind_filters)
            sql += f" AND kind IN ({placeholders})"
            parameters.extend(kind_filters)
        sql += " ORDER BY rank LIMIT ?"
        parameters.append(limit)
        connection = sqlite3.connect(self.index_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(sql, parameters).fetchall()
        finally:
            connection.close()
        return [
            {
                "kind": row["kind"],
                "id_or_path": row["key"],
                "title": row["title"],
                "excerpt": row["excerpt"],
                "rank": round(float(row["rank"]), 6),
            }
            for row in rows
        ]

    def context(self, query: str, char_budget: int = 12000, limit: int = 12) -> dict[str, Any]:
        char_budget = max(1000, min(int(char_budget), 50000))
        pieces: list[str] = []
        current_state = self.memory_dir / "CURRENT_STATE.md"
        if current_state.exists():
            pieces.append(current_state.read_text(encoding="utf-8-sig"))
        hits = self.search(query, limit=limit)
        records, _, _ = self.current_records()
        for hit in hits:
            if hit["kind"] == "document" and hit["id_or_path"] == "memory/CURRENT_STATE.md":
                continue
            if hit["kind"].startswith("memory:"):
                event = records.get(hit["id_or_path"], {})
                source_text = ", ".join(event.get("source_refs", [])) or "none recorded"
                pieces.append(
                    f"# Memory {event.get('id')} [{event.get('kind')}]\n"
                    f"Title: {event.get('title')}\nSummary: {event.get('summary')}\n"
                    f"Body: {event.get('body', '')}\nConfidence: {event.get('confidence')}\n"
                    f"Sources: {source_text}"
                )
            else:
                pieces.append(
                    f"# Document {hit['id_or_path']}\nTitle: {hit['title']}\nExcerpt: {hit['excerpt']}"
                )
        output: list[str] = []
        used = 0
        for piece in pieces:
            separator = "\n\n" if output else ""
            available = char_budget - used - len(separator)
            if available <= 0:
                break
            output.append(piece[:available])
            used += len(separator) + min(len(piece), available)
        return {
            "query": query,
            "char_budget": char_budget,
            "characters_used": used,
            "context": "\n\n".join(output),
            "hits": hits,
        }

    def status(self) -> dict[str, Any]:
        index_report = self.rebuild_index()
        records, superseded, errors = self.current_records()
        git_state = "unavailable"
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=3,
                check=False,
            )
            git_state = "clean" if result.returncode == 0 and not result.stdout.strip() else "dirty"
        except (OSError, subprocess.SubprocessError):
            pass
        return {
            "root": str(self.root),
            "source_of_truth": str(self.events_path),
            "index": str(self.index_path),
            "schema_version": SCHEMA_VERSION,
            "events": len(records),
            "active_memories": len(records) - len(set(records) & superseded),
            "superseded_memories": len(set(records) & superseded),
            "indexed_documents": index_report["documents"],
            "event_errors": errors,
            "git_state": git_state,
            "model_api_required": False,
        }
