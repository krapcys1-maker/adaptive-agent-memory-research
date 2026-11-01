#!/usr/bin/env python3
"""HYDE_QUERY_REFORMULATION: Mechanism H. Before calling Mem0's search(), generate
a short hypothetical memory-note sentence that WOULD plausibly answer the question,
and use that generated text (not the literal question) as the search query.

Source: HyDE (Gao et al., ACL 2023, arXiv:2212.10496) -- "Precise Zero-Shot Dense
Retrieval without Relevance Labels." This transplant tests the PURE (faithful)
variant: retrieval uses only the hypothetical's embedding, not a blend with the
literal question, matching the published technique.

Why this candidate, over the read-side annotation/verification tier tried before
it (Mechanisms D-G): a $0 diagnostic across every BASE-wrong unit observed so far
in this project found the dominant failure mode is retrieval ABSENCE (needed fact
missing from the top-10 the reader sees), not "evidence present but misread" --
the failure class CoVe/RARR/self-consistency-style verification requires to fire.
A follow-up $0 check against two already-ingested stores (Mechanism D's and E's)
found that in at least 2 of those absence cases, the missing fact WAS present in
the full store (not a write-time extraction loss) and moved from entirely absent
to rank 1 when queried with a better-phrased (hand-written) hypothetical in place
of the literal question -- a strong, confirmed precondition for this specific
technique. Independent support: LongMemEval's own primary-source construction
methodology (arXiv:2410.10813, appendix A.1) states evidence sessions are built to
"convey the evidence statement indirectly" rather than in the question's own
words -- literal question/fact phrasing mismatch is a by-construction property of
this exact benchmark, not a rare edge case.

Known risk (own archaeology, not yet observed): a hallucinated hypothetical could
steer retrieval away from the correct memory ("hallucination-guided retrieval
drift") -- this exploratory test's archaeology specifically checks for that
failure shape on any regression.
"""

from __future__ import annotations

import hashlib
from typing import Any

#: Fixed before any output was seen. Deliberately asks for a short, plausible,
#: first-person NOTE in the register Mem0's own compact facts use -- not a
#: confident factual claim -- so the hypothetical's embedding lands near how a
#: real answer-bearing memory would actually be phrased.
HYDE_PROMPT = (
    "You are guessing how a fact might be casually recorded in someone's personal "
    "memory notes, if the note existed. Given a question, write ONE short, "
    "first-person, present/past-tense sentence in a plausible answer's style -- "
    "not a real answer, not a hedge, not a question, no meta-commentary. Guess "
    "naturally, the way a person might mention it in conversation. Output only "
    "the one sentence, nothing else."
)

HYDE_PARAMS = {"temperature": 0, "max_tokens": 60}


def hyde_prompt_hash() -> str:
    return hashlib.sha256(HYDE_PROMPT.encode()).hexdigest()


def hyde_user_message(question: str) -> str:
    return f"Question: {question}"


def render_top10(raw_results: list[dict[str, Any]]) -> list[str]:
    """Same rendering every other AAMR mechanism uses: bare 'memory' text, in
    the order Mem0's search() returned it, blanks dropped."""
    return [str(r.get("memory", "")).strip() for r in raw_results
           if str(r.get("memory", "")).strip()]


def _self_check() -> None:
    raw = [{"id": "a", "memory": "  some fact  "}, {"id": "b", "memory": ""},
          {"id": "c", "memory": "another fact"}]
    assert render_top10(raw) == ["some fact", "another fact"]
    assert hyde_user_message("How many cats?") == "Question: How many cats?"
    assert len(hyde_prompt_hash()) == 64
    print("self-check OK: 3/3 cases correct")


if __name__ == "__main__":
    _self_check()
