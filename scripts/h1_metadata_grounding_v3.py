"""Deterministic projection of frozen v2 proposals; zero new model calls.

Preserve strict-case captures, their failed attempts and raw proposals. This
projection only maps a case variant to a literal source span with word bounds.
It cannot add an entity absent from the source or repair an invented property.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import h1_model_chains_v2 as V2
import structured_memory_pipeline_v1 as S
import nie_reader_pilot as P
from tools.structured_memory_v2 import Memory
from tools.retrieval_metadata_v2 import canonical_proposal

DATA=S.ROOT/'data/lab/h1-model-chains-v3'
BASE_IDENTITY=V2.identity


def identity():
    result=BASE_IDENTITY()
    for p in [Path(__file__),S.ROOT/'tools/retrieval_metadata_v2.py',DATA/'PLAN.md']:
        result['sha256'][p.relative_to(S.ROOT).as_posix()]=S.file_sha(p)
    result['candidate']='h1-v3-deterministic-literal-case-grounding'
    return result


def project(store,capture,output):
    output.mkdir(parents=True,exist_ok=False)
    if not identity()['clean_tree']: raise ValueError('Commit projection source first.')
    frozen=json.loads((capture/'raw-freeze.json').read_text(encoding='utf-8'))
    if any(S.file_sha(capture/name)!=sha for name,sha in frozen['files_sha256'].items()):
        raise ValueError('Original v2 capture changed.')
    P.write(output/'manifest.json',{'source':identity(),'input_sha256':{
        str(store.resolve()):S.file_sha(store),str((capture/'raw-freeze.json').resolve()):S.file_sha(capture/'raw-freeze.json')}})
    accepted={r['source']:r for r in P.read_rows(capture/'addresses.jsonl')}
    responses={r['key']:r['text'] for r in P.read_rows(capture/'responses.jsonl')}
    count=Counter()
    with Memory(store) as m:
        for sid,source in m.sources.items():
            base=accepted.get(sid)
            if base:
                proposal=base['proposal']; derivation=base['derivation']; prior=base['from_source']
            else:
                derivation,prior='new_generation',None
                try: proposal=json.loads(responses['address-'+sid])
                except (ValueError,TypeError,KeyError): proposal={}
            try:
                grounded=canonical_proposal(source,proposal)
                P.append(output/'addresses.jsonl',{'source':sid,'proposal':grounded,'derivation':derivation,
                    'from_source':prior,'raw_proposal_sha256':P.sha(proposal),'validation':'literal_case_v2'})
                count['accepted']+=1; count['addresses']+=len(grounded['addresses'])
                count['case_rescued_sources']+=sid not in accepted
                count['changed_proposals']+=grounded!=proposal
            except ValueError as exc:
                count['quarantined']+=1
                P.append(output/'rejections.jsonl',{'id':sid,'reason':str(exc)})
    P.write(output/'summary.json',{'counts':dict(count),'new_generations':0,
        'raw_store_sha256':S.file_sha(store),'base_capture_freeze_sha256':S.file_sha(capture/'raw-freeze.json')})
    P.write(output/'raw-freeze.json',{'files_sha256':{p.name:S.file_sha(p) for p in output.iterdir() if p.is_file()},
                                      'source':identity(),'scoring_has_not_run':True})


def read(**args):
    V2.identity=identity
    V2.read(**args)


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('project')
    for field in ['store','capture','output']: p.add_argument('--'+field,type=Path,required=True)
    p=sub.add_parser('read')
    for field in ['store','addresses','roles','questions','output','ledger']:
        p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--scope',required=True)
    args=vars(parser.parse_args()); command=args.pop('command'); globals()[command](**args)


if __name__=='__main__': main()
