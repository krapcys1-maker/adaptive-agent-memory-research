"""BASE vs TREATMENT prompt-construction tests for the PER_SESSION_REFERENCE_DATE_AT_EXTRACTION
patch to the pinned mem0ai==1.0.6 install (external/venvs/mem0).

Full provenance -- pinned version, original file hashes, patched file hashes,
the unified diff, and a description confirming exactly two changes and no
others -- lives in
data/lab/arena/base-plus-x-v1/vendor-patch/manifest.json, checked into the
repo, independent of the gitignored venv.

These tests exercise only prompt CONSTRUCTION (no LLM call, no network, no
spend): they import the patched `mem0.memory.utils` module directly by path,
which pulls in only `hashlib`, `re` and `mem0.configs.prompts` (pure string
constants plus `datetime`) -- not the heavy `mem0/__init__.py` dependency
chain (openai, qdrant-client, ...). Runs under the default test environment;
no dedicated venv required for these specific assertions.

    BASE:      reference_date=None       -> byte-identical to the pinned,
                                              unpatched 1.0.6 prompt constants
    TREATMENT: reference_date=2022-11-17 -> the prompt's date line changes to
                                              that date, and nothing else changes
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

from mem0.configs.prompts import AGENT_MEMORY_EXTRACTION_PROMPT, USER_MEMORY_EXTRACTION_PROMPT  # noqa: E402
from mem0.memory.utils import get_fact_retrieval_messages  # noqa: E402

MESSAGE = "user: I took a red-eye flight on JetBlue from San Francisco to Boston today.\n"
TREATMENT_DATE = "2022-11-17"


def test_base_reference_date_none_is_byte_identical_to_pinned_prompt() -> None:
    """BASE: no reference_date -> output equals the raw 1.0.6 prompt constant, unmodified."""
    system_prompt, _ = get_fact_retrieval_messages(MESSAGE, is_agent_memory=False, reference_date=None)
    assert system_prompt == USER_MEMORY_EXTRACTION_PROMPT

    agent_prompt, _ = get_fact_retrieval_messages(MESSAGE, is_agent_memory=True, reference_date=None)
    assert agent_prompt == AGENT_MEMORY_EXTRACTION_PROMPT


def test_base_omitting_the_argument_matches_explicit_none() -> None:
    """Callers that never pass reference_date (every pre-patch call site) see no change."""
    explicit_none, _ = get_fact_retrieval_messages(MESSAGE, is_agent_memory=False, reference_date=None)
    omitted, _ = get_fact_retrieval_messages(MESSAGE, is_agent_memory=False)
    assert explicit_none == omitted


def test_treatment_prompt_contains_the_session_reference_date() -> None:
    """TREATMENT: the extraction prompt's date line reflects the real session date."""
    system_prompt, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=TREATMENT_DATE)
    assert f"Today's date is {TREATMENT_DATE}." in system_prompt
    assert "2026" not in system_prompt, "the frozen, wrong, process-start date must be fully replaced"


def test_treatment_changes_only_the_reference_date_line() -> None:
    """Everything outside the date line is byte-identical between BASE and TREATMENT."""
    base_prompt, _ = get_fact_retrieval_messages(MESSAGE, is_agent_memory=False, reference_date=None)
    treatment_prompt, _ = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=TREATMENT_DATE)

    base_line = next(line for line in base_prompt.splitlines() if line.startswith("- Today's date is"))
    treatment_line = next(
        line for line in treatment_prompt.splitlines() if line.startswith("- Today's date is"))
    assert base_line != treatment_line

    assert base_prompt.replace(base_line, "X") == treatment_prompt.replace(treatment_line, "X")


def test_treatment_user_prompt_unchanged() -> None:
    """The patch touches only the system prompt; the user prompt (the actual message) is untouched."""
    _, base_user = get_fact_retrieval_messages(MESSAGE, is_agent_memory=False, reference_date=None)
    _, treatment_user = get_fact_retrieval_messages(
        MESSAGE, is_agent_memory=False, reference_date=TREATMENT_DATE)
    assert base_user == treatment_user == f"Input:\n{MESSAGE}"
