from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.project_memory.memory_store import MemoryStore
from tools.project_memory.server import McpServer


class ProjectMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "memory").mkdir()
        (self.root / "memory" / "CURRENT_STATE.md").write_text(
            "# State\nResearch temporal and emotional memory.", encoding="utf-8"
        )
        (self.root / "notes.md").write_text(
            "# Retrieval note\nLexical search is the initial baseline.", encoding="utf-8"
        )
        self.store = MemoryStore(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_add_search_and_provenance(self) -> None:
        event = self.store.add(
            kind="finding",
            title="Append-only evidence",
            summary="Immutable evidence protects provenance.",
            source_refs=["paper:example"],
            confidence="medium",
        )
        hits = self.store.search("immutable provenance")
        self.assertEqual(event["id"], hits[0]["id_or_path"])
        self.assertEqual("memory:finding", hits[0]["kind"])
        loaded = self.store.get(event["id"])
        self.assertTrue(loaded["is_active"])
        self.assertEqual(["paper:example"], loaded["event"]["source_refs"])

    def test_supersede_preserves_history_and_hides_old_record(self) -> None:
        old = self.store.add(
            kind="decision",
            title="Use vector-only retrieval",
            summary="Vector search is sufficient.",
        )
        new = self.store.supersede(
            memory_id=old["id"],
            reason="Lexical matches remain important.",
            summary="Use a lexical baseline before hybrid retrieval.",
        )
        self.assertFalse(self.store.get(old["id"])["is_active"])
        self.assertTrue(self.store.get(new["id"])["is_active"])
        self.assertEqual(old["id"], new["supersedes"])
        self.assertEqual(2, len(self.store.timeline()))
        self.assertFalse(any(hit["id_or_path"] == old["id"] for hit in self.store.search("vector")))

    def test_documents_and_context_are_indexed(self) -> None:
        hits = self.store.search("lexical baseline")
        self.assertTrue(any(hit["id_or_path"] == "notes.md" for hit in hits))
        context = self.store.context("emotional retrieval", char_budget=2000)
        self.assertTrue(context["context"].startswith("# State"))
        self.assertLessEqual(context["characters_used"], 2000)

    def test_malformed_event_is_reported_without_losing_valid_events(self) -> None:
        self.store.initialize()
        self.store.events_path.write_text(
            '{"id":"PM-valid","operation":"create","kind":"finding","title":"A","summary":"B"}\nnot-json\n',
            encoding="utf-8",
        )
        status = self.store.status()
        self.assertEqual(1, status["events"])
        self.assertEqual(1, len(status["event_errors"]))

    def test_concurrent_writers_do_not_lose_events(self) -> None:
        def write(number: int) -> str:
            event = MemoryStore(self.root).add(
                kind="session",
                title=f"Concurrent session {number}",
                summary=f"Writer {number} completed.",
            )
            return event["id"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            identifiers = list(executor.map(write, range(12)))
        events, errors = self.store.load_events()
        self.assertEqual(12, len(events))
        self.assertEqual(12, len(set(identifiers)))
        self.assertEqual([], errors)
        self.assertEqual(12, self.store.status()["active_memories"])

    def test_mcp_surface_and_tool_call(self) -> None:
        server = McpServer(self.store)
        listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertIn("memory_search", names)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "memory_status", "arguments": {}},
            }
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertFalse(payload["model_api_required"])


if __name__ == "__main__":
    unittest.main()
