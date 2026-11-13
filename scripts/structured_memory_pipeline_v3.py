"""Explicit cache amendment; unchanged v2 prompts and v1 source/state contracts."""
from pathlib import Path

import structured_memory_pipeline_v1 as V1
import structured_memory_pipeline_v2 as V2
from tools.structured_memory_v2 import Memory

ORIGINAL_IDENTITY = V2.identity


def identity():
    result = ORIGINAL_IDENTITY()
    for p in [Path(__file__), V1.ROOT/'tools/structured_memory_v2.py', V1.DATA/'V3-CACHE-AMENDMENT.md']:
        result['sha256'][p.relative_to(V1.ROOT).as_posix()] = V1.file_sha(p)
    result['amendment'] = 'v3-literal-shell-specificity'
    return result


def install():
    V2.install()
    V1.identity = identity
    V1.Memory = Memory


if __name__ == '__main__':
    install()
    V1.main()
