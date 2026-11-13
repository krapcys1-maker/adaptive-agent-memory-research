"""Replay BEAM format/source separation and estimate input scale; no models."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_beam_transfer_v2 as B


def audit(source,output):
    manifest=B.load(output/'manifest.json')
    for label,base,field in [('source',source,'source_files_sha256'),('output',output,'output_files_sha256')]:
        if any(B.sha(base/p)!=h for p,h in manifest[field].items()):raise ValueError(label+' hash drift')
    h=B.read_rows(output/'reader/history.jsonl');a=B.read_rows(output/'audit/message-provenance.jsonl')
    q=B.read_rows(output/'reader/questions.jsonl');g=B.read_rows(output/'evaluation/labels.jsonl')
    if len(h)!=len(a) or len(q)!=len(g):raise ValueError('Sidecar length mismatch.')
    if len({r['id'] for r in h})!=len(h) or len({r['id'] for r in q})!=len(q):raise ValueError('Duplicate reader IDs.')
    if any(set(r)!={'id','conversation_id','sequence','role','text','time_anchor_raw'} for r in h):raise ValueError('Reader history key leak.')
    if any(set(r)!={'id','conversation_id','question'} for r in q):raise ValueError('Reader question key leak.')
    dirs=sorted([p for p in source.iterdir() if p.is_dir()],key=lambda p:int(p.name))
    if manifest['conversations']!=len(dirs) or manifest['full_tier']!=(len(dirs)==10 and {int(p.name) for p in dirs}==set(range(1,11))):raise ValueError('Full-tier coverage claim differs.')
    expected_source_files={str(d.name)+'/'+n for d in dirs for n in ['chat_trunecated.json','probing_questions/probing_questions.json']}
    if set(manifest['source_files_sha256'])!=expected_source_files:raise ValueError('Unexpected input roster.')
    seen_h=0;seen_q=0;stats=[];lens=[];roles=Counter();time_types=Counter();abilities=Counter();original_metadata_keys=Counter()
    for directory in dirs:
        cid='BEAM10M-'+str(int(directory.name))
        hh=[r for r in h if r['conversation_id']==cid];aa=[r for r in a if r['id'].startswith(cid+'-M')]
        original=B.load(directory/'chat_trunecated.json');source_messages=list(B.messages(original))
        if len(hh)!=len(aa) or len(hh)!=len(source_messages):raise ValueError('History message dropped or added.')
        scoped_keys=set();scoped_unique_bytes=0
        for i,((location,msg),r,p) in enumerate(zip(source_messages,hh,aa,strict=True)):
            if r['id']!=f'{cid}-M{i:06d}' or p['id']!=r['id'] or p['location']!=location or r['sequence']!=i:raise ValueError('Message identity/order differs.')
            expected_meta={k:v for k,v in msg.items() if k not in {'role','content','time_anchor'}}
            if p['metadata']!=expected_meta or p['had_time_anchor']!=('time_anchor' in msg):raise ValueError('Raw metadata provenance differs.')
            rebuilt={'role':r['role'],'content':r['text'],**p['metadata']}
            if p['had_time_anchor']:rebuilt['time_anchor']=r['time_anchor_raw']
            if msg!=rebuilt:raise ValueError('Raw message content/role/time differs.')
            raw=r['text'].encode();n=len(raw);lens.append(n);roles[r['role']]+=1
            key=(r['role'],hashlib.sha256(raw).digest())
            if key not in scoped_keys:scoped_unique_bytes+=n
            scoped_keys.add(key);time_types[type(msg['time_anchor']).__name__ if 'time_anchor' in msg else 'absent']+=1
            original_metadata_keys.update(p['metadata'].keys())
        qq=[r for r in q if r['conversation_id']==cid];gg=[r for r in g if r['conversation_id']==cid]
        probes=B.load(directory/'probing_questions/probing_questions.json')
        expected_q=[];expected_g=[]
        for ability,items in probes.items():
            if ability not in B.ABILITIES or len(items)!=2:raise ValueError('Ability roster differs.')
            for within,item in enumerate(items):
                qid=f'{cid}-Q{len(expected_q):04d}'
                expected_q.append({'id':qid,'conversation_id':cid,'question':item['question']})
                expected_g.append({'id':qid,'conversation_id':cid,'ability':ability,'within_ability':within,'annotations':{k:v for k,v in item.items() if k!='question'}})
                abilities[ability]+=1
        if len(qq)!=20 or qq!=expected_q or gg!=expected_g:raise ValueError('Probe/annotation content/order differs.')
        stats.append({'conversation_id':cid,'messages':len(hh),'questions':len(qq),
            'unique_role_text_keys':len(scoped_keys),'duplicate_role_text_opportunities':len(hh)-len(scoped_keys),
            'unique_text_bytes':scoped_unique_bytes})
        seen_h+=len(hh);seen_q+=len(qq)
    if seen_h!=len(h) or seen_q!=len(q) or manifest['messages']!=len(h) or manifest['questions']!=len(q):raise ValueError('Out-of-scope/unaccounted reader rows.')
    if dict(roles)!=manifest['source_roles'] or dict(abilities)!=manifest['probe_abilities']:raise ValueError('Role/ability counts differ.')
    lens.sort()
    return {'failures':[],'messages_reconstructed':seen_h,'probes_reconstructed':seen_q,
        'conversations':len(dirs),'full_tier':manifest['full_tier'],'source_roles':dict(roles),'probe_abilities':dict(abilities),
        'raw_time_anchor_types':dict(time_types),'construction_metadata_excluded':dict(original_metadata_keys),
        'per_conversation':stats,'input_text_bytes':sum(lens),
        'message_utf8_bytes':{'p50':lens[math.ceil(.5*len(lens))-1],'p95':lens[math.ceil(.95*len(lens))-1],
                              'p99':lens[math.ceil(.99*len(lens))-1],'max':max(lens)},
        'messages_text_alone_over_existing_h1_4500byte_cap':sum(n>4500 for n in lens),
        'scoped_role_text_unique_count':sum(r['unique_role_text_keys'] for r in stats),
        'scoped_role_text_duplicate_opportunities':sum(r['duplicate_role_text_opportunities'] for r in stats),
        'count_semantics':'Descriptive raw scoped/role exact-text uniqueness. Per-message model capture would process this many distinct keys if all needed interpretation; not a universal call lower bound, semantic cache validation, token count or authorized model run.',
        'manifest_sha256':B.sha(output/'manifest.json'),'new_model_calls':0,'benchmark_score':None,
        'review':'Authored format/integrity replay only; no independent semantic or end-to-end memory claim.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','output','destination']:p.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());destination=args.pop('destination');result=audit(**args)
    B.write(destination,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['per_conversation']},indent=2))
