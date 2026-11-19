"""Rendering of the memory block, with pluggable formats.

The default format, ``walkthrough_v5b``, is the rendering of the measured V5B ``retrieved_task`` arm
(instrument ``tools/alfworld_ladder/agent.py``, functions ``render`` and ``wrap``):

    Retrieved Item 0:
    Task: <goal>.
    [Observation 1: '<initial observation>', Action 1: '<action 1>']
    [Observation 2: '<observation after action 1>', Action 2: '<action 2>']
    ...
    Final observation: '<observation after the last action>'

    Retrieved Item 1:
    ...

Observations have their whitespace collapsed and are cut to 240 characters; actions and goals are kept as they are.
This is the same ``[Observation i: ..., Action i: ...]`` format in which the agent sees its own history, so the
block differs from the placebo in content, not in layout.

A new format (for example the abstract "plan" format the lab tests in V6) is a class with a ``name``, a
``render_item`` and a ``wrap`` method, registered with :func:`register_formatter`. It is NOT a measured
configuration until the lab has measured it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence, runtime_checkable

from .bank import Trajectory

TokenCounter = Callable[[str], int]


@runtime_checkable
class Formatter(Protocol):
    name: str

    def render_item(self, item: Trajectory) -> str:
        """The text of one bank item."""

    def wrap(self, texts: Sequence[str]) -> str:
        """Join item texts into the block. The placebo uses the same layout with filler texts."""


class WalkthroughFormatter:
    """The V5B ``retrieved_task`` rendering (see the module docstring)."""

    name = "walkthrough_v5b"

    def __init__(self, obs_chars: int = 240) -> None:
        self.obs_chars = obs_chars

    def _cut(self, text: str) -> str:
        return " ".join(text.split())[: self.obs_chars]

    def render_item(self, item: Trajectory) -> str:
        obs = [self._cut(item.initial_observation)] + [self._cut(s.observation) for s in item.steps]
        lines = [f"Task: {item.goal}."]
        for i, s in enumerate(item.steps):
            lines.append(f"[Observation {i + 1}: '{obs[i]}', Action {i + 1}: '{s.action}']")
        lines.append(f"Final observation: '{obs[-1]}'")
        return "\n".join(lines)

    def wrap(self, texts: Sequence[str]) -> str:
        return "\n\n".join(f"Retrieved Item {i}:\n{t}" for i, t in enumerate(texts))


_REGISTRY: dict[str, Callable[[], Formatter]] = {WalkthroughFormatter.name: WalkthroughFormatter}


def register_formatter(name: str, factory: Callable[[], Formatter], *, replace: bool = False) -> None:
    """Make a format available by name. Refuses to overwrite a registered name unless ``replace=True``."""
    if name in _REGISTRY and not replace:
        raise ValueError(f"formatter {name!r} is already registered")
    _REGISTRY[name] = factory


def get_formatter(name: str = WalkthroughFormatter.name) -> Formatter:
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise KeyError(f"unknown formatter {name!r}; registered: {sorted(_REGISTRY)}") from None


def available_formatters() -> list[str]:
    return sorted(_REGISTRY)


@dataclass(frozen=True)
class MemoryBlock:
    """A rendered memory block and what it shows.

    ``text`` is the block (the ``{retrieved_exp}`` of the prompt wrapper). ``item_ids`` are the shown items in order;
    ``dropped_ids`` are retrieved items left out to respect the token budget. ``n_tokens`` is the block's token
    count when a counter was given, else ``None``.
    """

    text: str
    item_ids: tuple[str, ...]
    formatter: str
    dropped_ids: tuple[str, ...] = ()
    n_tokens: int | None = None

    @property
    def is_empty(self) -> bool:
        return not self.item_ids


def build_memory_block(items: Sequence[Trajectory], formatter: Formatter | None = None, *,
                       token_budget: int | None = None, count_tokens: TokenCounter | None = None) -> MemoryBlock:
    """Render ``items`` (best first) into one block.

    Without a budget (the measured V5B setting) every item is shown. With ``token_budget`` the lowest-ranked items
    are dropped, whole, until the block fits; an item is never cut in the middle. If not even the first item fits,
    the block is empty: use the no-memory prompt then. A budget that is never binding gives the V5B block exactly.
    """
    fmt = formatter or get_formatter()
    if token_budget is not None and count_tokens is None:
        raise ValueError("a token_budget needs a count_tokens function (the tokenizer of the model you prompt)")
    if token_budget is not None and token_budget < 0:
        raise ValueError("token_budget must be non-negative")

    def render(texts: list[str]) -> tuple[str, int | None]:
        text = fmt.wrap(texts) if texts else ""
        if count_tokens is None:
            return text, None
        return text, (count_tokens(text) if text else 0)

    shown = list(items)
    texts = [fmt.render_item(it) for it in shown]
    text, n = render(texts)
    dropped: list[str] = []
    while token_budget is not None and shown and n is not None and n > token_budget:
        dropped.insert(0, shown.pop().item_id)
        texts.pop()
        text, n = render(texts)
    return MemoryBlock(text=text, item_ids=tuple(it.item_id for it in shown), formatter=fmt.name,
                       dropped_ids=tuple(dropped), n_tokens=n)
