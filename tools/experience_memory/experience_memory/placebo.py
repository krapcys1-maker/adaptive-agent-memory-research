"""A token-matched placebo block, so that a user can run the same controlled comparison as the lab.

The placebo has the wrapper and the item layout of the memory block, with neutral filler lines in place of the
walkthroughs, and about the same number of tokens. Any gain of the memory block over the placebo is then a gain of
its content, not of a longer prompt. Rule (V5B ``placebo_items``):

- repeat the filler lines in order; with ``n`` lines, the first ``ceil(n / 2)`` form item 0 and the rest item 1;
- for ``n = 2, 3, ...`` count the tokens of the wrapped block; at the first ``n`` that reaches the target, return
  the block with ``n`` or ``n - 1`` lines, whichever is closer to the target (``n`` on a tie);
- stop at ``max_lines`` lines (399 in V5B) and return the longest block tried. The result records the target, so
  a block that fell short is visible (``n_tokens < target_tokens``).

V5B always had two items. ``n_items`` (default 2; :meth:`ExperienceMemory.placebo_for` passes the number of shown
items) splits the lines over that many items, the first items taking one line more when the lines do not divide
evenly; for two items this is the V5B split. An empty memory block gets an empty placebo, because the memory arm
then falls back to the no-memory prompt.

The token counter must be the tokenizer of the model under test (V5B: vLLM ``/tokenize`` of Qwen3-4B); a
whitespace count is fine for tests but not for an experiment.
"""
from __future__ import annotations

from typing import Sequence

from .formatting import Formatter, MemoryBlock, TokenCounter, get_formatter

# Same lines as the lab's instrument/placebo.txt (no line names an object, a receptacle, a room, an action or a task).
DEFAULT_FILLER = (
    "This line is a placeholder and carries no information.",
    "Nothing is recorded in this slot.",
    "The text here is neutral filler of fixed wording.",
    "No experience is stored at this position.",
    "This entry is intentionally left without content.",
    "Placeholder text continues on the next line.",
    "There is nothing to learn from this line.",
    "This slot holds filler only.",
)


def placebo_texts(target_tokens: int, count_tokens: TokenCounter, *, formatter: Formatter | None = None,
                  filler: Sequence[str] = DEFAULT_FILLER, max_lines: int = 399, n_items: int = 2) -> list[str]:
    """The filler item texts whose wrapped block is closest to ``target_tokens`` (rule in the module docstring)."""
    fmt = formatter or get_formatter()
    lines = [ln for ln in filler if ln.strip() and not ln.startswith("#")]
    if not lines:
        raise ValueError("the filler has no usable line")
    if n_items < 1:
        raise ValueError("n_items must be at least 1")

    def items(n_lines: int) -> list[str]:
        out = [lines[i % len(lines)] for i in range(n_lines)]
        q, r = divmod(len(out), n_items)
        texts, start = [], 0
        for i in range(n_items):
            size = q + (1 if i < r else 0)
            texts.append("\n".join(out[start:start + size]))
            start += size
        return texts

    prev = items(1)
    prev_n = count_tokens(fmt.wrap(prev))
    for n_lines in range(2, max_lines + 1):
        cur = items(n_lines)
        c = count_tokens(fmt.wrap(cur))
        if c >= target_tokens:
            return cur if (c - target_tokens) <= (target_tokens - prev_n) else prev
        prev, prev_n = cur, c
    return prev


def placebo_block(memory: MemoryBlock | int, count_tokens: TokenCounter, *, formatter: Formatter | None = None,
                  filler: Sequence[str] = DEFAULT_FILLER, max_lines: int = 399,
                  n_items: int | None = None) -> MemoryBlock:
    """A placebo block token-matched to ``memory`` (a :class:`MemoryBlock` or a target token count).

    Pass the formatter that rendered the memory block, so that the placebo uses the same layout. ``n_items``
    defaults to the number of items of ``memory`` (2 when a token count is given).
    """
    fmt = formatter or get_formatter()
    if isinstance(memory, MemoryBlock):
        if not memory.text:
            return MemoryBlock(text="", item_ids=(), formatter=f"placebo/{fmt.name}", n_tokens=0, target_tokens=0)
        target = count_tokens(memory.text)
        if n_items is None:
            n_items = len(memory.item_ids) or 2  # a block without item ids (for example a placebo): two items
    else:
        target = int(memory)
        if n_items is None:
            n_items = 2
    text = fmt.wrap(placebo_texts(target, count_tokens, formatter=fmt, filler=filler, max_lines=max_lines,
                                  n_items=n_items))
    return MemoryBlock(text=text, item_ids=(), formatter=f"placebo/{fmt.name}", n_tokens=count_tokens(text),
                       target_tokens=target)
