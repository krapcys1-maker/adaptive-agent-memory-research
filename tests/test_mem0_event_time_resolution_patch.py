"""BASE/CONTROL vs TREATMENT prompt-construction tests for the
EVENT_TIME_RESOLUTION_AT_EXTRACTION patch, additive on top of the already
calibrated-INERT PER_SESSION_REFERENCE_DATE_AT_EXTRACTION patch to the pinned
mem0ai==1.0.6 install (external/venvs/mem0).

Full provenance -- pinned version, baseline/patched file hashes, the unified
diff, and a description confirming exactly one logical change -- lives in
data/lab/arena/event-time-resolution-calibration-v1/vendor-patch/manifest.json,
checked into the repo, independent of the gitignored venv.

These tests exercise only prompt CONSTRUCTION (no LLM call, no network, no
spend), same approach as tests/test_mem0_per_session_reference_date_patch.py.

    CONTROL:   reference_date=<correct session date>, resolve_relative_time=False
               -> byte-identical to PER_SESSION_REFERENCE_DATE_AT_EXTRACTION's
                  own (already-calibrated-INERT) treatment.
    TREATMENT: same reference_date, resolve_relative_time=True
               -> adds exactly one instruction bullet immediately after the
                  "Today's date is ..." line; nothing else changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MEM0_SITE_PACKAGES = ROOT / "external/venvs/mem0/Lib/site-packages"

if not MEM0_SITE_PACKAGES.exists():
    pytest.skip(
        "external/venvs/mem0 not present in this environment -- the patch's "
        "reproducibility does not depend on it (see vendor-patch/manifest.json), "
        "but these tests exercise the actual installed, patched module",
        allow_module_level=True,
    )

sys.path.insert(0, str(MEM0_SITE_PACKAGES))

from mem0.memory.utils import get_fact_retrieval_messages  # noqa: E402

MESSAGE = "user: I took a red-eye flight on JetBlue from San Francisco to Boston today.\n"
REFERENCE_DATE = "2022-11-17"


def test_control_default_matches_reference_date_only_baseline() -> None:
    """CONTROL: resolve_relative_time omitted/False -> identical to the prior,
    already-calibrated-INERT PER_SESSION_REFERENCE_DATE_AT_EXTRACTION treatment."""
    explicit_false, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=False)
    omitted, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE)
    assert explicit_false == omitted


def test_treatment_adds_exactly_one_instruction_bullet() -> None:
    """TREATMENT differs from CONTROL by exactly one inserted bullet line, nothing else."""
    control, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=False)
    treatment, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=True)

    control_lines = control.splitlines()
    treatment_lines = treatment.splitlines()
    assert len(treatment_lines) == len(control_lines) + 1

    date_idx = next(i for i, l in enumerate(control_lines) if l.startswith("- Today's date is"))
    assert treatment_lines[date_idx] == control_lines[date_idx]
    inserted = treatment_lines[date_idx + 1]
    assert inserted.startswith("- When a fact contains a relative time expression")
    assert "resolve it against the reference date above" in inserted
    assert "Do not invent a date" in inserted

    # everything else, before and after the insertion point, is byte-identical
    assert control_lines[:date_idx + 1] == treatment_lines[:date_idx + 1]
    assert control_lines[date_idx + 1:] == treatment_lines[date_idx + 2:]


def test_treatment_instruction_references_the_correct_reference_date() -> None:
    """The inserted instruction sits immediately after the correct session date, not a stale one."""
    treatment, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=True)
    assert f"- Today's date is {REFERENCE_DATE}.\n- When a fact contains" in treatment


def test_resolve_relative_time_alone_without_reference_date_does_not_fabricate_a_date() -> None:
    """resolve_relative_time=True with reference_date=None still inserts only the instruction
    text (which references 'the reference date above', i.e. whatever date line already exists);
    it must not inject any date value of its own."""
    treatment_no_refdate, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=None, resolve_relative_time=True)
    assert REFERENCE_DATE not in treatment_no_refdate
    assert "resolve it against the reference date above" in treatment_no_refdate


def test_treatment_user_prompt_unchanged() -> None:
    """The patch touches only the system prompt; the user prompt (the actual message) is untouched."""
    _, control_user = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=False)
    _, treatment_user = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=REFERENCE_DATE, resolve_relative_time=True)
    assert control_user == treatment_user == f"Input:\n{MESSAGE}"


def test_explicit_source_date_in_message_text_is_never_touched_by_the_patch() -> None:
    """Deterministic/parser-layer guard (no LLM call): _with_reference_date and
    _with_temporal_resolution_instruction only ever rewrite the SYSTEM prompt
    scaffolding string. The user's message text -- which may itself state an
    explicit absolute event date, e.g. "I flew on March 3" -- flows into the
    user_prompt untouched, byte-for-byte, regardless of reference_date or
    resolve_relative_time. Neither patched function is given the message text
    to operate on, so an explicit in-text event date structurally cannot be
    overwritten by the session reference_date at this layer -- that risk (see
    MECHANISM_REGIME_EVIDENCE_LEDGER.md Entry B) lives entirely in what the
    LLM chooses to write, not in deterministic code, and is out of scope for
    a no-LLM-call test."""
    message_with_its_own_explicit_date = (
        "user: I flew on March 3rd, which was well before Today's date is 2022-11-17. "
        "The trip itself happened last month.\n"
    )
    _, control_user = get_fact_retrieval_messages(
        message_with_its_own_explicit_date, is_agent_memory=False,
        reference_date=REFERENCE_DATE, resolve_relative_time=False)
    _, treatment_user = get_fact_retrieval_messages(
        message_with_its_own_explicit_date, is_agent_memory=False,
        reference_date=REFERENCE_DATE, resolve_relative_time=True)
    expected = f"Input:\n{message_with_its_own_explicit_date}"
    assert control_user == expected
    assert treatment_user == expected
    assert "March 3rd" in control_user and "March 3rd" in treatment_user


def test_agent_memory_branch_also_supports_the_treatment() -> None:
    """Both prompt branches (user memory, agent memory) accept the new parameter identically."""
    control, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=True, reference_date=REFERENCE_DATE, resolve_relative_time=False)
    treatment, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=True, reference_date=REFERENCE_DATE, resolve_relative_time=True)
    assert control != treatment
    assert "resolve it against the reference date above" in treatment
