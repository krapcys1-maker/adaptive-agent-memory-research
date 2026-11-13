"""Complete a copied v3 prefix, preserving attempted quarantines and originals.

The earlier unmatched-source cutoff was reached at about half the archive.
This explicit continuation does not regenerate any previously attempted source.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

import structured_memory_pipeline_v1 as V1
import structured_memory_pipeline_v3 as V3
import nie_reader_pilot as P
from tools.structured_memory_v2 import Memory

BASE_IDENTITY = V3.identity


def identity():
    result = BASE_IDENTITY()
    for p in [Path(__file__), V1.DATA/'V4-COMPLETION.md']:
        result['sha256'][p.relative_to(V1.ROOT).as_posix()] = V1.file_sha(p)
    result['amendment'] = 'v4-no-regeneration-continuation-of-frozen-v3-prefix'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['archive','base-store','base-capture','store','output']:
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    V3.install()
    V1.identity = identity
    V1.start(args.output,'local14b',[args.archive,args.base_store,args.base_capture/'captures.jsonl',
                                    args.base_capture/'attempts.jsonl',args.base_capture/'responses.jsonl'])
    archive = P.read_rows(args.archive)
    earlier = P.read_rows(args.base_capture/'captures.jsonl')
    attempted = {r['id'] for r in earlier}
    if len(attempted) != len(earlier):
        raise ValueError('Duplicate source attempts in the inherited prefix.')
    # Exclusive copy: the old canonical store is never appended to or replaced.
    with args.store.open('xb') as stream:
        stream.write(args.base_store.read_bytes())
    for name in ['attempts.jsonl','responses.jsonl']:
        for row in P.read_rows(args.base_capture/name):
            if row['key'].startswith('extract-'):
                P.append(args.output/name,row)
    for row in earlier:
        P.append(args.output/'captures.jsonl',row)
    for row in P.read_rows(args.base_capture/'rejections.jsonl'):
        P.append(args.output/'rejections.jsonl',row)
    reader = V1.client('local14b',args.output,None)
    counts = Counter(r['method'] for r in earlier)
    new_model = 0
    try:
        P.write(args.output/'preflight.json',reader.preflight())
        V1.controls(reader,'local14b',args.output)
        with Memory(args.store,writable=True) as memory:
            if len(memory.sources) != len(archive) or any(memory.sources[r['id']].text != r['text'] or
                    memory.sources[r['id']].recorded != r['ordinal'] for r in archive):
                raise ValueError('Archive differs from the frozen prefix.')
            for row in archive:
                if row['id'] in attempted:
                    continue
                cached = memory.cached(row['id'])
                if cached is not None:
                    proposal = {'claims':[{k:v for k,v in asdict(cached).items() if k!='source'}]}
                    method, learn = 'template',False
                else:
                    if new_model >= 120:
                        raise RuntimeError('Explicit completion model cap reached.')
                    proposal = V1.ask(reader,'local14b','extract-'+row['id'],
                                      V1.extraction_messages(row['text'],memory.catalog))
                    method,learn = 'model',proposal.get('learn_template') is True
                    new_model += 1
                counts[method] += 1
                try:
                    memory.extract(row['id'],proposal,method=method,learn=learn)
                    status = 'accepted'
                except ValueError as exc:
                    status = 'quarantined'
                    P.append(args.output/'rejections.jsonl',{'id':row['id'],'reason':str(exc)})
                P.append(args.output/'captures.jsonl',{'id':row['id'],'method':method,'status':status})
            P.write(args.output/'capture-summary.json',{'sources':len(memory.sources),'claims':len(memory.claims),
                'templates':len(memory.templates),'catalog':sorted(memory.catalog),'counts':dict(counts),
                'quarantined':len(P.read_rows(args.output/'rejections.jsonl')),
                'inherited_model_attempts':counts['model']-new_model,'new_model_attempts':new_model,
                'store_sha256':V1.file_sha(args.store),'base_store_sha256':V1.file_sha(args.base_store),
                'base_prefix_preserved':args.store.read_bytes().startswith(args.base_store.read_bytes()),
                'scope':'mab-dev','policy':'ordered_single'})
        V1.finish(reader,args.output)
    finally:
        reader.release()


if __name__ == '__main__':
    main()
