"""Persistent retrieval metadata and source recall, independent of benchmarks.

Raw sources use structured_memory_v1's canonical log. This separate append-only
log stores validated metadata derivations and explicit revisions. Neither an
instruction address nor a lookup creates an asserted fact or grants authority.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.structured_memory_v1 import Memory, digest, key
from tools.retrieval_metadata_v2 import canonical_proposal

ROLES=('user_message','agent_note','tool_result','unknown')


class EvidenceMemory:
    def __init__(self,raw_path,metadata_path):
        self.raw_path,self.metadata_path=Path(raw_path),Path(metadata_path)
        if self.raw_path.resolve()==self.metadata_path.resolve():
            raise ValueError('Raw and derived logs require separate files.')

    def _load(self,raw):
        latest={}; head='0'*64; count=0
        if not self.metadata_path.exists(): return latest,head,count
        with self.metadata_path.open(encoding='utf-8') as stream:
            for line in stream:
                row=json.loads(line); body=row['event']; sid=body['source']
                if row['previous']!=head or row['sha256']!=digest(body):
                    raise ValueError('Corrupt metadata log.')
                if sid not in raw.sources or body['source_sha256']!=digest(asdict(raw.sources[sid])):
                    raise ValueError('Metadata no longer matches its raw source.')
                expected=latest.get(sid,{}).get('attachment')
                if body['supersedes']!=expected or body['source_role'] not in ROLES:
                    raise ValueError('Invalid metadata revision or source role.')
                if canonical_proposal(raw.sources[sid],body['proposal'])!=body['proposal']:
                    raise ValueError('Metadata is not grounded to canonical source spelling.')
                head=digest(row); latest[sid]=dict(body,attachment=head); count+=1
        return latest,head,count

    def attach(self,sid,proposal,*,source_role='unknown',provenance='',supersedes=None):
        if source_role not in ROLES or not isinstance(provenance,str) or not provenance.strip():
            raise ValueError('Caller-provided source role and derivation provenance are required.')
        # Share the raw writer's exclusive lock: source writes and metadata
        # revisions cannot race. Acquiring it does not append a raw event.
        with Memory(self.raw_path,writable=True) as raw:
            source=raw.sources[sid]
            grounded=canonical_proposal(source,proposal)
            latest,head,count=self._load(raw)
            old=latest.get(sid)
            if old and old['proposal']==grounded and old['source_role']==source_role and old['provenance']==provenance:
                return {'attachment':old['attachment'],'added':False}
            if (old['attachment'] if old else None)!=supersedes:
                raise ValueError('Changing metadata requires its exact superseded attachment ID.')
            body={'source':sid,'source_sha256':digest(asdict(source)),'proposal':grounded,
                  'source_role':source_role,'provenance':provenance,'supersedes':supersedes,
                  'semantics':'retrieval_metadata'}
            row={'previous':head,'sha256':digest(body),'event':body}
            self.metadata_path.parent.mkdir(parents=True,exist_ok=True)
            with self.metadata_path.open('a',encoding='utf-8',newline='\n') as stream:
                stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')
                stream.flush(); os.fsync(stream.fileno())
            return {'attachment':digest(row),'added':True}

    def recall(self,scope,entity,property,*,known_at,limit=3):
        if isinstance(known_at,bool) or not isinstance(known_at,int) or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=50:
            raise ValueError('Integer availability time and a bounded recall limit are required.')
        with Memory(self.raw_path) as raw:
            latest,head,count=self._load(raw); found=[]
            for sid,metadata in latest.items():
                source=raw.sources[sid]
                if source.scope!=scope or source.recorded>known_at: continue
                addresses=[a for a in metadata['proposal']['addresses'] if key(a['entity'])==key(entity) and a['property']==property]
                if not addresses: continue
                found.append({'source':sid,'recorded':source.recorded,'valid_from':source.start,
                    'valid_to':source.valid_to,'source_role':metadata['source_role'],'text':source.text,
                    'kinds':sorted({a['kind'] for a in addresses}),'attachment':metadata['attachment']})
            found.sort(key=lambda r:(-r['recorded'],r['source']))
            return {'status':'found' if found else 'no_history','semantics':'retrieval_metadata',
                    'records':found[:limit],'truncated':len(found)>limit}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,required=True); parser.add_argument('--metadata',type=Path,required=True)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('attach')
    p.add_argument('--source',required=True); p.add_argument('--proposal',type=Path,required=True)
    p.add_argument('--source-role',choices=ROLES,default='unknown'); p.add_argument('--provenance',required=True)
    p.add_argument('--supersedes')
    p=sub.add_parser('recall')
    for name in ['scope','entity','property']: p.add_argument('--'+name,required=True)
    p.add_argument('--known-at',type=int,required=True); p.add_argument('--limit',type=int,default=3)
    args=parser.parse_args(argv); memory=EvidenceMemory(args.raw,args.metadata)
    if args.command=='attach':
        result=memory.attach(args.source,json.loads(args.proposal.read_text(encoding='utf-8')),
                             source_role=args.source_role,provenance=args.provenance,supersedes=args.supersedes)
    else:
        result=memory.recall(args.scope,args.entity,args.property,known_at=args.known_at,limit=args.limit)
    print(json.dumps(result,ensure_ascii=True,indent=2)); return 0


if __name__=='__main__': raise SystemExit(main())
