"""One object for the measured configuration: bank + goal-similarity retrieval (k = 2) + a formatter."""
from __future__ import annotations

from dataclasses import dataclass

from .bank import ExperienceBank
from .formatting import Formatter, MemoryBlock, TokenCounter, build_memory_block, get_formatter
from .placebo import placebo_block
from .retrieval import GoalSimilarityRetriever, Retrieval


@dataclass(frozen=True)
class Shown:
    """The memory chosen for one episode: the block to insert and the retrieval record to log."""

    block: MemoryBlock
    retrieval: Retrieval

    def log_record(self) -> dict:
        """What was shown, for an episode log (item ids, scores, exclusions, block size)."""
        r = self.retrieval
        return {"query_id": r.query_id, "seed": r.seed, "formatter": self.block.formatter,
                "shown": list(self.block.item_ids), "dropped_for_budget": list(self.block.dropped_ids),
                "scores": [round(p.score, 4) for p in r.picks], "top1_similarity": round(r.top1_similarity, 4),
                "excluded": list(r.excluded_ids), "block_tokens": self.block.n_tokens}


class ExperienceMemory:
    """Defaults are the V5B ``retrieved_task`` arm: k = 2, goal Jaccard, the walkthrough format, no token budget."""

    def __init__(self, bank: ExperienceBank, *, k: int = 2, formatter: Formatter | str | None = None,
                 token_budget: int | None = None, count_tokens: TokenCounter | None = None) -> None:
        self.bank = bank
        self.retriever = GoalSimilarityRetriever(k=k)
        self.formatter = get_formatter(formatter) if isinstance(formatter, str) else (formatter or get_formatter())
        self.token_budget = token_budget
        self.count_tokens = count_tokens

    def for_task(self, goal: str, *, query_id: str, query_family: str | None, seed: int = 0) -> Shown:
        r = self.retriever.retrieve(self.bank, goal, query_id=query_id, query_family=query_family, seed=seed)
        block = build_memory_block(r.items, self.formatter, token_budget=self.token_budget,
                                   count_tokens=self.count_tokens)
        return Shown(block=block, retrieval=r)

    def placebo_for(self, shown: Shown | MemoryBlock, count_tokens: TokenCounter | None = None) -> MemoryBlock:
        """A filler block with the same layout and about the same token count as the shown block."""
        counter = count_tokens or self.count_tokens
        if counter is None:
            raise ValueError("a placebo needs count_tokens (the tokenizer of the model under test)")
        block = shown.block if isinstance(shown, Shown) else shown
        return placebo_block(block, counter, formatter=self.formatter)
