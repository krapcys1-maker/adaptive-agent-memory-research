"""Prompt text around the memory block, as in the measured V5B arms.

The wrapper and the action instruction are AdaMEM's ALFWorld prompts (yunx-z/AdaMEM, Apache-2.0,
``agent_system/environments/prompts/alfworld.py``), as used by the lab's instrument
``tools/alfworld_ladder/agent.py``. The format reminder was added by the lab in V5 and is the same in every arm.

In V5B the prompt of every step is ``<base prompt with history> + suffix + FORMAT_REMINDER``, where the suffix is
:data:`ACTION_INSTR` for the no-memory arm and ``MEMORY_WRAPPER.format(retrieved_exp=block)`` for the memory and
placebo arms. The block is fixed for the whole episode.
"""
from __future__ import annotations

from .formatting import MemoryBlock

ACTION_INSTR = """
Now it's your turn to take an action.
You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.
Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags.
"""

MEMORY_WRAPPER = """
Here are some task solving trajectories on similar tasks:

Retrieved Experiences:
{retrieved_exp}

Now it's your turn to take an action.
You should first reason step-by-step about the current situation. This reasoning process MUST be enclosed within <think> </think> tags.
Once you've finished your reasoning, you should choose an admissible action for current step and present it within <action> </action> tags.
"""

FORMAT_REMINDER = "\nReminder: end your answer with exactly one admissible action inside <action> </action> tags.\n"


def prompt_suffix(block: MemoryBlock | None, *, format_reminder: bool = True) -> str:
    """The text to append after the base prompt: the wrapped block, or the plain action instruction if there is no
    block (``None`` or an empty block), then the format reminder."""
    if block is None or not block.text:
        suffix = ACTION_INSTR
    else:
        suffix = MEMORY_WRAPPER.format(retrieved_exp=block.text)
    return suffix + (FORMAT_REMINDER if format_reminder else "")
