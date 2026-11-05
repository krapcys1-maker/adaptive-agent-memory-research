"""Same post-hoc computation as v1 with memoized read-only anchor lookups.

The first CPU-only diagnostic repeatedly recompiled literal name regexes for
every candidate path. This optional wrapper speeds up the same computation
without changing any primary model input/output, store, score or inference
source. No further model calls.
"""
import diagnose_structured_memory_v1 as D

ORIGINAL_MEMORY = D.V5.Memory
ORIGINAL_OLDEST = D.Oldest


class MemoAnchors:
    def anchors(self, scope, question, *, known_at):
        if not hasattr(self,'anchor_cache'):
            self.anchor_cache = {}
        cache_key = (scope,question,known_at)
        if cache_key not in self.anchor_cache:
            self.anchor_cache[cache_key] = super().anchors(scope,question,known_at=known_at)
        return self.anchor_cache[cache_key]


class Memory(MemoAnchors, ORIGINAL_MEMORY):
    pass


class Oldest(MemoAnchors, ORIGINAL_OLDEST):
    pass


if __name__=='__main__':
    D.V5.Memory = Memory
    D.Oldest = Oldest
    D.main()
