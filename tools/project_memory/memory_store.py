"""Append-only project memory with a rebuildable SQLite FTS5 index.

The Git-tracked JSONL and Markdown files are the source of truth. SQLite is
only a cache and may be deleted or rebuilt at any time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import sqlite3
import sys
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
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

# Version 2 fields. See memory/SCHEMA.md and
# docs/04-systems/temporal-memory-model-comparison-v0.md.
#
# `valid_to` and `expired_at` are deliberately NOT written. They are derived at
# read time from the superseding event by upcast.derive_temporal_view. Storing
# them would create a second source for one fact, which is exactly the drift the
# derived design exists to prevent, and an append-only log cannot update them on
# the record they end anyway.
ALLOWED_CLAIM_CLASSES = {"dispositional", "state", "unclassified"}
ALLOWED_SUPERSESSION_KINDS = {"succession", "correction", "unclassified"}
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
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
    "primary-work",
    "work",
}
EXCLUDED_PREFIXES = {
    "data/snapshots",
    "external/repos",
    "sources/papers",
}
MAX_INDEXED_FILE_BYTES = 5 * 1024 * 1024

# How long a lock may be held before it is broken regardless of who holds it.
# Deliberately far above any legitimate write: the previous 120-second rule stole
# locks from writers that were merely slow, which is the two-writer hazard the
# lock exists to prevent. See issue #28.
LOCK_ABANDONED_SECONDS = 3600

# Largest share of a context bundle that the canonical state summary may occupy.
# The remainder is reserved for retrieved evidence so that a growing
# CURRENT_STATE.md cannot silently crowd out every search hit.
CONTEXT_STATE_SHARE = 0.4
CONTEXT_SEPARATOR = "\n\n"
CONTEXT_TRUNCATION_MARKER = "\n[truncated]"

# Word characters only and Unicode-aware, so Polish diacritics tokenise as words
# rather than splitting on them.
GLOSSARY_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


class MemoryError(ValueError):
    """Raised when a memory operation is invalid."""


def _process_is_alive(pid: int) -> bool:
    """Whether a process id is still running, without signalling it.

    On POSIX, ``os.kill(pid, 0)`` is the standard existence probe. **On Windows
    it is not**: Python's ``os.kill`` treats any signal other than the two
    console-control events as a request to call ``TerminateProcess``, so probing
    with signal 0 would kill the very process being checked. Windows therefore
    uses ``OpenProcess`` through ctypes, which is stdlib and keeps this module
    dependency-free.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        ERROR_INVALID_PARAMETER = 87
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        # Access denied means the process exists but belongs to someone else.
        # Only an invalid parameter means no such process.
        return kernel32.GetLastError() != ERROR_INVALID_PARAMETER
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _unlink_lock(lock_path: Path, attempts: int = 40) -> None:
    """Remove a lock file, tolerating a concurrent reader.

    Windows refuses to delete a file another handle has open. Verifying
    ownership means reading the lock on every contention, which widens the
    window where a releasing writer and a checking writer overlap. A brief
    retry is the correct handling of that race rather than a workaround: the
    reader closes within microseconds, and giving up would leave a stale lock
    behind — the exact failure this hardening exists to avoid.
    """
    for _ in range(attempts):
        try:
            lock_path.unlink(missing_ok=True)
            return
        except PermissionError:
            time.sleep(0.01)
    # Last attempt, deliberately unguarded: if it still fails the caller must
    # see the error rather than silently continue without the lock released.
    lock_path.unlink(missing_ok=True)


def _lock_owner() -> dict[str, Any]:
    return {"pid": os.getpid(), "host": socket.gethostname(), "acquired_at": _utc_now()}


def _breakable_reason(lock_path: Path) -> str:
    """Why this lock may be broken, or an empty string meaning it may not.

    The previous rule broke any lock older than 120 seconds. That steals the
    lock from a writer that is merely slow — a paused agent, a machine under
    load, a debugger, a large index rebuild — and lets two writers append at
    once, which is precisely what the lock exists to prevent.

    Ownership is now verified instead of inferred from age. A lock is broken
    only when its owner is provably gone on this host, or when it is so old that
    leaving it would deadlock the store regardless of who holds it.
    """
    age = time.time() - lock_path.stat().st_mtime
    try:
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        pid = int(owner["pid"])
        host = str(owner["host"])
    except (OSError, ValueError, KeyError, TypeError):
        # A lock written by an older version, or truncated mid-write. Nothing
        # can be verified about it, so only the long ceiling applies.
        if age > LOCK_ABANDONED_SECONDS:
            return f"unreadable owner record, age {age:.0f}s exceeds the {LOCK_ABANDONED_SECONDS}s ceiling"
        return ""

    if host != socket.gethostname():
        # A different machine's process id means nothing here, which is the
        # case on a shared or synced filesystem.
        if age > LOCK_ABANDONED_SECONDS:
            return f"held by host {host!r}, age {age:.0f}s exceeds the {LOCK_ABANDONED_SECONDS}s ceiling"
        return ""

    if not _process_is_alive(pid):
        return f"owner pid {pid} on this host is gone"
    if age > LOCK_ABANDONED_SECONDS:
        return f"owner pid {pid} still alive but has held it {age:.0f}s"
    return ""


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
        self.glossary_path = self.memory_dir / "glossary.json"
        self._glossary_cache: dict[str, str] | None = None
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
                os.write(descriptor, json.dumps(_lock_owner()).encode("utf-8"))
                os.close(descriptor)
                break
            except FileExistsError:
                try:
                    reason = _breakable_reason(lock_path)
                except FileNotFoundError:
                    continue
                if reason:
                    # A broken lock is a real event, not routine cleanup. Two
                    # writers appending concurrently is exactly the hazard this
                    # lock exists to prevent, so say so loudly rather than
                    # silently proceeding.
                    print(
                        f"WARNING: breaking {lock_path.name}: {reason}",
                        file=sys.stderr,
                        flush=True,
                    )
                    _unlink_lock(lock_path)
                    continue
                if time.monotonic() >= deadline:
                    raise MemoryError(f"memory lock is busy: {lock_path.name}")
                time.sleep(0.05)
        try:
            yield
        finally:
            _unlink_lock(lock_path)

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
        valid_from: str = "",
        claim_class: str = "unclassified",
    ) -> dict[str, Any]:
        kind = _clean_string(kind, "kind", True).lower()
        if kind not in ALLOWED_KINDS:
            raise MemoryError(f"kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}")
        confidence = _clean_string(confidence, "confidence", True).lower()
        if confidence not in ALLOWED_CONFIDENCE:
            raise MemoryError("confidence must be unknown, low, medium, or high")
        claim_class = _clean_string(claim_class, "claim_class", True).lower()
        if claim_class not in ALLOWED_CLAIM_CLASSES:
            raise MemoryError(
                f"claim_class must be one of: {', '.join(sorted(ALLOWED_CLAIM_CLASSES))}"
            )
        written_at = _utc_now()
        valid_from = _clean_string(valid_from, "valid_from") or written_at
        if not TIMESTAMP_PATTERN.match(valid_from):
            raise MemoryError("valid_from must be ISO-8601 UTC as YYYY-MM-DDTHH:MM:SSZ")
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
            "created_at": written_at,
            "valid_from": valid_from,
            "claim_class": claim_class,
            "supersedes": None,
            "supersession_kind": None,
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
        supersession_kind: str = "unclassified",
        valid_from: str = "",
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
        supersession_kind = _clean_string(supersession_kind, "supersession_kind", True).lower()
        if supersession_kind not in ALLOWED_SUPERSESSION_KINDS:
            raise MemoryError(
                f"supersession_kind must be one of: {', '.join(sorted(ALLOWED_SUPERSESSION_KINDS))}"
            )
        written_at = _utc_now()
        valid_from = _clean_string(valid_from, "valid_from") or written_at
        if not TIMESTAMP_PATTERN.match(valid_from):
            raise MemoryError("valid_from must be ISO-8601 UTC as YYYY-MM-DDTHH:MM:SSZ")
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
            "created_at": written_at,
            "valid_from": valid_from,
            "claim_class": previous.get("claim_class", "unclassified"),
            "supersedes": memory_id,
            "supersession_kind": supersession_kind,
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
                # The glossary is retrieval machinery, not research content. Indexing
                # it makes it match the very foreign-language queries it exists to
                # translate, so it returns itself as a hit.
                if path in (self.events_path, self.glossary_path):
                    continue
                if path.stat().st_size > MAX_INDEXED_FILE_BYTES:
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

    def _glossary(self) -> dict[str, str]:
        """Load the operational query glossary, cached after the first read."""
        if self._glossary_cache is None:
            try:
                document = json.loads(self.glossary_path.read_text(encoding="utf-8-sig"))
                terms = document.get("terms", {})
                self._glossary_cache = {
                    str(k).lower(): str(v) for k, v in terms.items() if k and v
                }
            except (OSError, json.JSONDecodeError, AttributeError):
                self._glossary_cache = {}
        return self._glossary_cache

    def expand_query(self, query: str) -> str:
        """Append English project vocabulary for any glossary term in the query.

        The lexical index matches tokens, so a question asked in one language
        cannot reach records written in another. PMLAB-XLANG-E1 measured
        Recall@10 at 0.156 for Polish queries against this English store, with
        26 of 45 returning no candidates at all; expansion lifted it to 0.867.

        Only terms actually present in the glossary contribute, so a query that
        contains none is returned unchanged and English queries are unaffected.
        """
        glossary = self._glossary()
        if not glossary:
            return query
        additions: list[str] = []
        for token in GLOSSARY_TOKEN.findall(query.lower()):
            english = glossary.get(token)
            if english:
                additions.extend(english.split())
        if not additions:
            return query
        present = set(GLOSSARY_TOKEN.findall(query.lower()))
        seen: set[str] = set()
        extra = [
            term
            for term in additions
            if term.lower() not in present and not (term in seen or seen.add(term))
        ]
        return f"{query} {' '.join(extra)}" if extra else query

    def search(
        self,
        query: str,
        limit: int = 10,
        kinds: list[str] | str | None = None,
        expand: bool = True,
    ) -> list[dict[str, Any]]:
        self._ensure_index()
        cleaned = _clean_string(query, "query", True)
        fts_query = self._fts_query(self.expand_query(cleaned) if expand else cleaned)
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

    @staticmethod
    def _fair_shares(lengths: list[int], budget: int) -> list[int]:
        """Split ``budget`` across ``lengths`` so no single piece can starve the rest.

        Pieces shorter than an equal share release their surplus to the others, so
        the budget stays fully used whenever there is content to fill it.
        """
        shares = [0] * len(lengths)
        remaining = budget
        pending = [index for index, length in enumerate(lengths) if length > 0]
        while pending and remaining > 0:
            per_piece = remaining // len(pending)
            if per_piece == 0:
                break
            for index in list(pending):
                take = min(per_piece, lengths[index] - shares[index])
                shares[index] += take
                remaining -= take
                if shares[index] >= lengths[index]:
                    pending.remove(index)
        # Hand out any indivisible remainder in stable order.
        for index in list(pending):
            if remaining <= 0:
                break
            take = min(remaining, lengths[index] - shares[index])
            shares[index] += take
            remaining -= take
        return shares

    def context(
        self,
        query: str,
        char_budget: int = 12000,
        limit: int = 12,
        state_share: float = CONTEXT_STATE_SHARE,
    ) -> dict[str, Any]:
        char_budget = max(1000, min(int(char_budget), 50000))
        state_share = max(0.0, min(float(state_share), 1.0))

        current_state = self.memory_dir / "CURRENT_STATE.md"
        state_text = (
            current_state.read_text(encoding="utf-8-sig") if current_state.exists() else ""
        )

        hits = self.search(query, limit=limit)
        records, _, _ = self.current_records()
        retrieved: list[tuple[str, str]] = []
        for hit in hits:
            if hit["kind"] == "document" and hit["id_or_path"] == "memory/CURRENT_STATE.md":
                continue
            if hit["kind"].startswith("memory:"):
                event = records.get(hit["id_or_path"], {})
                source_text = ", ".join(event.get("source_refs", [])) or "none recorded"
                retrieved.append(
                    (
                        hit["id_or_path"],
                        f"# Memory {event.get('id')} [{event.get('kind')}]\n"
                        f"Title: {event.get('title')}\nSummary: {event.get('summary')}\n"
                        f"Body: {event.get('body', '')}\nConfidence: {event.get('confidence')}\n"
                        f"Sources: {source_text}",
                    )
                )
            else:
                retrieved.append(
                    (
                        hit["id_or_path"],
                        f"# Document {hit['id_or_path']}\nTitle: {hit['title']}\nExcerpt: {hit['excerpt']}",
                    )
                )

        labelled: list[tuple[str, str]] = []
        if state_text:
            labelled.append(("memory/CURRENT_STATE.md", state_text))
        labelled.extend(retrieved)
        if not labelled:
            return {
                "query": query,
                "char_budget": char_budget,
                "characters_used": 0,
                "state_share": state_share,
                "context": "",
                "sections": [],
                "hits": hits,
            }

        separator_cost = len(CONTEXT_SEPARATOR) * (len(labelled) - 1)
        content_budget = max(0, char_budget - separator_cost)

        # The canonical state summary is capped so that retrieved evidence always
        # keeps a share of the budget. Without this cap a long CURRENT_STATE.md
        # consumes the whole bundle and every search hit contributes nothing.
        if state_text and retrieved:
            state_cap = int(content_budget * state_share)
            state_allocation = min(len(state_text), state_cap)
            hit_shares = self._fair_shares(
                [len(text) for _, text in retrieved], content_budget - state_allocation
            )
            allocations = [state_allocation, *hit_shares]
        else:
            allocations = self._fair_shares([len(text) for _, text in labelled], content_budget)

        output: list[str] = []
        sections: list[dict[str, Any]] = []
        for (identifier, text), allowance in zip(labelled, allocations):
            if allowance <= 0:
                sections.append(
                    {
                        "id_or_path": identifier,
                        "characters": 0,
                        "of": len(text),
                        "truncated": True,
                        "included": False,
                    }
                )
                continue
            truncated = allowance < len(text)
            if truncated and allowance > len(CONTEXT_TRUNCATION_MARKER):
                body = text[: allowance - len(CONTEXT_TRUNCATION_MARKER)] + CONTEXT_TRUNCATION_MARKER
            else:
                body = text[:allowance]
            output.append(body)
            sections.append(
                {
                    "id_or_path": identifier,
                    "characters": len(body),
                    "of": len(text),
                    "truncated": truncated,
                    "included": True,
                }
            )

        rendered = CONTEXT_SEPARATOR.join(output)
        return {
            "query": query,
            "char_budget": char_budget,
            "characters_used": len(rendered),
            "state_share": state_share,
            "context": rendered,
            "sections": sections,
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
            "git_head": self._git_head(),
            "events_sha256": self._events_digest(),
            "model_api_required": False,
        }

    def _git_head(self) -> str:
        """Return the current commit, so a caller can detect that the repository moved."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=3,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return "unavailable"
        if result.returncode != 0:
            return "unavailable"
        return result.stdout.strip() or "unavailable"

    def _events_digest(self) -> str:
        """Hash the canonical log so a caller can detect a concurrent append.

        Two agents may operate on one repository. Writes are serialized by the
        event lock, but a reader that took a snapshot has no other way to notice
        that the log grew underneath it.
        """
        digest = hashlib.sha256()
        try:
            with self.events_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    digest.update(chunk)
        except OSError:
            return "unavailable"
        return digest.hexdigest()
