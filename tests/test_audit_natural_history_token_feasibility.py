import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("token_feas", ROOT / "scripts" / "audit_natural_history_token_feasibility.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_commonmark_sections_ignore_fenced_heading_and_support_setext():
    text = """Intro
=====

Parent body.

```text
# not a heading
```

## Child

Child body.
"""
    rows = MODULE.markdown_units(text)
    assert [row["locator"] for row in rows] == ["Intro#1", "Intro > Child#1"]
    assert "Parent body." in rows[0]["search_text"]
    assert "# not a heading" in rows[0]["search_text"]
    assert "Child body." not in rows[0]["search_text"]


def test_memory_event_allowlist_excludes_governance_fields():
    row = {
        "id": "PM-secret", "title": "Title", "summary": "Summary", "body": "Body", "tags": ["one", "two"],
        "kind": "finding", "status": "active", "created_at": "secret-time", "source_refs": ["secret-path"],
    }
    text = MODULE.memory_event_text(row)
    assert text == "Title: Title\nSummary: Summary\nBody: Body\nTags: one, two"
    assert "secret" not in text


def test_primary_eligibility_excludes_api_and_current_state_factor():
    assert MODULE.eligible_class("docs/00-project/scope.md") == "canonical_research"
    assert MODULE.eligible_class("memory/CURRENT_STATE.md") == "registered_summary_secondary"
    assert MODULE.eligible_class("data/lab/api-screening/run/report.md") is None
    assert MODULE.eligible_class("data/lab/example/report.md") == "reviewed_lab_summary"
