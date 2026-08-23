from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from tools.project_memory import cli
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

    def test_long_state_summary_cannot_starve_retrieved_evidence(self) -> None:
        (self.root / "memory" / "CURRENT_STATE.md").write_text(
            "# State\n" + ("Temporal and emotional memory diagnostics. " * 2000),
            encoding="utf-8",
        )
        for index in range(6):
            (self.root / f"evidence-{index}.md").write_text(
                f"# Evidence {index}\nEmotional retrieval evidence number {index}.",
                encoding="utf-8",
            )
        self.store.rebuild_index()

        context = self.store.context("emotional retrieval", char_budget=4000)

        self.assertLessEqual(context["characters_used"], 4000)
        state = next(
            section
            for section in context["sections"]
            if section["id_or_path"] == "memory/CURRENT_STATE.md"
        )
        self.assertTrue(state["truncated"])
        self.assertLessEqual(state["characters"], int(4000 * context["state_share"]))

        retrieved = [
            section
            for section in context["sections"]
            if section["id_or_path"] != "memory/CURRENT_STATE.md"
        ]
        self.assertTrue(retrieved, "search hits must reach the bundle")
        self.assertTrue(
            all(section["characters"] > 0 for section in retrieved),
            "every retrieved section must receive part of the budget",
        )

    def test_truncated_sections_are_marked_rather_than_cut_silently(self) -> None:
        (self.root / "memory" / "CURRENT_STATE.md").write_text(
            "# State\n" + ("Consolidation and replay. " * 1000), encoding="utf-8"
        )
        self.store.rebuild_index()
        context = self.store.context("consolidation replay", char_budget=1000)
        self.assertIn("[truncated]", context["context"])

    def test_context_without_hits_still_returns_state(self) -> None:
        context = self.store.context("no matching terms whatsoever", char_budget=2000)
        self.assertTrue(context["context"].startswith("# State"))
        self.assertLessEqual(context["characters_used"], 2000)

    def test_status_exposes_head_and_canonical_digest(self) -> None:
        first = self.store.status()
        self.assertEqual(64, len(first["events_sha256"]))
        self.assertIn("git_head", first)

        unchanged = self.store.status()
        self.assertEqual(first["events_sha256"], unchanged["events_sha256"])

        self.store.add(
            kind="decision",
            title="Concurrent append",
            summary="A second agent appended an event.",
        )
        after = self.store.status()
        self.assertNotEqual(
            first["events_sha256"],
            after["events_sha256"],
            "an append must change the canonical digest so a stale reader can notice",
        )

    def test_glossary_expands_a_foreign_query_to_reach_english_records(self) -> None:
        """A question asked in one language must reach records written in another.

        PMLAB-XLANG-E1 measured Recall@10 of 0.156 for Polish queries against
        this English store, with 26 of 45 returning no candidates at all.
        """
        (self.root / "memory" / "glossary.json").write_text(
            json.dumps({"terms": {"pamieci": "memory", "wyszukiwanie": "retrieval"}}),
            encoding="utf-8",
        )
        (self.root / "note-en.md").write_text(
            "# Retrieval note\nLexical retrieval over durable memory.", encoding="utf-8"
        )
        store = MemoryStore(self.root)
        store.rebuild_index()

        self.assertEqual([], store.search("wyszukiwanie pamieci", expand=False))
        self.assertTrue(store.search("wyszukiwanie pamieci", expand=True))

    def test_expansion_leaves_a_query_without_glossary_terms_unchanged(self) -> None:
        (self.root / "memory" / "glossary.json").write_text(
            json.dumps({"terms": {"pamieci": "memory"}}), encoding="utf-8"
        )
        store = MemoryStore(self.root)
        self.assertEqual("lexical baseline", store.expand_query("lexical baseline"))

    def test_expansion_does_not_repeat_a_term_already_present(self) -> None:
        (self.root / "memory" / "glossary.json").write_text(
            json.dumps({"terms": {"pamieci": "memory"}}), encoding="utf-8"
        )
        store = MemoryStore(self.root)
        self.assertEqual("memory pamieci", store.expand_query("memory pamieci"))

    def test_a_missing_glossary_is_not_an_error(self) -> None:
        store = MemoryStore(self.root)
        self.assertEqual("wyszukiwanie", store.expand_query("wyszukiwanie"))
        self.assertIsInstance(store.search("lexical"), list)

    def test_generated_work_directories_are_not_indexed(self) -> None:
        for name in ("work", "primary-work"):
            generated = self.root / "data" / "lab" / "benchmark" / name
            generated.mkdir(parents=True)
            (generated / "duplicate.txt").write_text(
                "This generated corpus copy must not pollute durable project memory.", encoding="utf-8"
            )
        report = self.store.rebuild_index()
        self.assertEqual(2, report["documents"])
        self.assertFalse(any(hit["id_or_path"].endswith("duplicate.txt") for hit in self.store.search("generated corpus copy")))

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

    def test_cli_forces_unicode_safe_output(self) -> None:
        class LegacyStream:
            def __init__(self) -> None:
                self.configuration: dict[str, str] = {}

            def reconfigure(self, **configuration: str) -> None:
                self.configuration = configuration

        stdout = LegacyStream()
        stderr = LegacyStream()
        with patch.object(cli.sys, "stdout", stdout), patch.object(cli.sys, "stderr", stderr):
            cli._configure_standard_streams()
        self.assertEqual({"encoding": "utf-8", "errors": "backslashreplace"}, stdout.configuration)
        self.assertEqual({"encoding": "utf-8", "errors": "backslashreplace"}, stderr.configuration)


if __name__ == "__main__":
    unittest.main()
