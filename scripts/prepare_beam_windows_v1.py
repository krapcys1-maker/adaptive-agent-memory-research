"""All-source BEAM snapshots and gold-free query packets; no inference/labels."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from tools import source_windows_v1 as W
import run_memory_benchmark as L

PUBLIC=ROOT/'data/lab/beam-source-windows-v1'
CONFIG={'max_text_bytes':1600,'overlap_bytes':160,'query_term_limit':24,'candidate_limit':16,
        'max_message_bytes':6000,'max_seconds':1800,'max_output_bytes':8_000_000_000}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def append(path,value):
    with path.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False)+'\n')


def rows(path):
    with path.open(encoding='utf-8') as f:
        for line in f:yield json.loads(line)


def source(row):
    if set(row)!={'id','conversation_id','sequence','role','text','time_anchor_raw'}:raise ValueError('Reader history must have exactly the frozen gold-free projection.')
    return W.Source(row['id'],row['conversation_id'],row['text'],row['role'],row['sequence'],row['time_anchor_raw'])


def prepare(prepared,output):
    if output.resolve().is_relative_to(ROOT) or output.resolve().is_relative_to(prepared.resolve()):raise ValueError('Use a new private output outside Git/input trees.')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('Freeze source/config before full construction.')
    config=json.loads((PUBLIC/'config.json').read_text(encoding='utf-8'))
    if config!=CONFIG:raise ValueError('Frozen config differs from code.')
    manifest=json.loads((prepared/'manifest.json').read_text(encoding='utf-8'))
    known=json.loads((ROOT/'data/lab/beam-transfer-format-v2/preparation.json').read_text(encoding='utf-8'))
    if sha(prepared/'manifest.json')!=known['private_manifest_sha256'] or not manifest['full_tier'] or manifest['messages']!=187734 or manifest['questions']!=200:raise ValueError('Complete frozen BEAM format-v2 input required.')
    history=prepared/'reader/history.jsonl';questions=prepared/'reader/questions.jsonl'
    for name,path in [('reader/history.jsonl',history),('reader/questions.jsonl',questions)]:
        if sha(path)!=manifest['output_files_sha256'][name]:raise ValueError('Frozen reader input drift.')
    output.mkdir(parents=True,exist_ok=False)
    for name in ['sources','indexes']:(output/name).mkdir()
    started=time.monotonic()
    def budget():
        if time.monotonic()-started>CONFIG['max_seconds']:raise TimeoutError('Preparation deadline exceeded.')
        if sum(p.stat().st_size for p in output.rglob('*') if p.is_file())>CONFIG['max_output_bytes']:raise RuntimeError('Preparation disk cap exceeded.')
    scopes=[f'BEAM10M-{i}' for i in range(1,11)];counts=Counter();cutoffs={}
    identity={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'clean_tree':True,
        'sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(W.__file__),Path(L.__file__),PUBLIC/'PLAN.md',PUBLIC/'config.json']}}
    write(output/'started.json',{'source':identity,'config':CONFIG,'input_sha256':{'history':sha(history),'questions':sha(questions)},'new_model_calls':0})
    with ExitStack() as stack:
        handles={s:stack.enter_context((output/'sources'/f'{s}.jsonl').open('x',encoding='utf-8',newline='\n')) for s in scopes}
        for i,row in enumerate(rows(history)):
            s=source(row)
            if s.scope not in handles or s.id!=f'{s.scope}-M{counts[s.scope]:06d}' or s.known_sequence!=counts[s.scope]:raise ValueError('Source order/identity/scope differs.')
            handles[s.scope].write(json.dumps(row,ensure_ascii=False)+'\n');counts[s.scope]+=1;cutoffs[s.scope]=s.known_sequence
            if i%1000==0:budget()
    if sum(counts.values())!=187734 or set(counts)!=set(scopes):raise ValueError('Incomplete source roster.')
    indexes=[]
    for scope in scopes:
        before=time.monotonic();path=output/'indexes'/f'{scope}.sqlite'
        result=W.build_snapshot(path,(source(r) for r in rows(output/'sources'/f'{scope}.jsonl')),
            scope=scope,known_at=cutoffs[scope],max_text_bytes=CONFIG['max_text_bytes'],overlap_bytes=CONFIG['overlap_bytes'])
        indexes.append(result|{'file':path.relative_to(output).as_posix(),'bytes':path.stat().st_size,'wall_seconds':time.monotonic()-before,'sha256':sha(path)})
        print(f"{scope}: {result['sources']} sources / {result['windows']} windows",flush=True);budget()
    query_stats=[];seen=set()
    with ExitStack() as stack:
        readers={s:stack.enter_context(W.Snapshot(output/'indexes'/f'{s}.sqlite',scope=s,known_at=cutoffs[s])) for s in scopes}
        for row in rows(questions):
            if set(row)!={'id','conversation_id','question'} or row['id'] in seen or row['conversation_id'] not in readers:raise ValueError('Question metadata/roster differs.')
            seen.add(row['id']);scope=row['conversation_id'];terms=L.query_tokens(row['question']);used=terms[:CONFIG['query_term_limit']]
            before=time.monotonic();windows=readers[scope].search(used,scope=scope,known_at=cutoffs[scope],limit=CONFIG['candidate_limit'])
            packet=W.render_packet(row['question'],windows,scope=scope,known_at=cutoffs[scope],max_message_bytes=CONFIG['max_message_bytes'])
            empty=W.render_packet(row['question'],[],scope=scope,known_at=cutoffs[scope],max_message_bytes=CONFIG['max_message_bytes'])
            append(output/'query-packets.jsonl',row|{'known_at':cutoffs[scope],'terms':used,'terms_truncated':len(terms)>len(used),
                'candidate_windows':[W.asdict(w) for w in windows],'retrieval_packet':packet,'no_memory_packet':empty})
            query_stats.append({'id':row['id'],'conversation_id':scope,'candidate_windows':len(windows),'shown_windows':len(packet['shown_ids']),
                'omitted_candidates':len(packet['omitted_ids']),'partial_sources':packet['partial_sources'],'terms_truncated':len(terms)>len(used),
                'message_bytes':packet['message_bytes'],'wall_seconds':time.monotonic()-before})
            budget()
    if len(query_stats)!=200:raise ValueError('Every question must have an accounted packet.')
    if sha(history)!=manifest['output_files_sha256']['reader/history.jsonl'] or sha(questions)!=manifest['output_files_sha256']['reader/questions.jsonl']:raise ValueError('Input changed during preparation.')
    report={'source':identity,'config':CONFIG,'sources':sum(counts.values()),'windows':sum(r['windows'] for r in indexes),'indexes':indexes,
        'questions':len(query_stats),'query_stats':query_stats,'source_partitions_sha256':{s:sha(output/'sources'/f'{s}.jsonl') for s in scopes},
        'query_packets_sha256':sha(output/'query-packets.jsonl'),'elapsed_seconds':time.monotonic()-started,
        'total_output_bytes':sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),'new_model_calls':0,'benchmark_score':None,
        'claim':'All-source access and ordinary lexical retrieval preparation, not graph capture or memory accuracy.'}
    budget();write(output/'manifest.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['source','indexes','query_stats','source_partitions_sha256']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['prepared','output']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();prepare(args.prepared,args.output)
