"""Versioned cache correction: require lexical relation content and specificity.

The v1 state, log and query contracts are unchanged. The two rules below depend
on literal sentence shells, never a benchmark relation, question or answer key.
"""
import re

from tools.structured_memory_v1 import Memory as MemoryV1

FUNCTION_WORDS = frozenset('a an the is are was were be been of to in with for at by '
                           'jest są był była być w z na do od'.split())


def informative(template):
    fixed = template.before+' '+template.between+' '+template.after
    return any(word.casefold() not in FUNCTION_WORDS for word in re.findall(r'[^\W\d_]+', fixed))


def specificity(template):
    return len((template.before+template.between+template.after).encode('utf-8'))


class Memory(MemoryV1):
    def _apply(self, event):
        super()._apply(event)
        self.templates = [t for t in self.templates if informative(t)]

    def cached(self, sid):
        matches = [(specificity(t), c) for t in self.templates if (c := t.match(self.sources[sid]))]
        if not matches:
            return None
        best = max(rank for rank, _ in matches)
        candidates = {(c.subject, c.predicate, c.object): c for rank,c in matches if rank == best}
        return next(iter(candidates.values())) if len(candidates) == 1 else None
