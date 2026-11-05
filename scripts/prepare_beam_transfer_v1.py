"""Lossless BEAM format split, with reader/evaluator separation; no model calls."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'data/lab/beam-transfer-format-v1'
ROLES={'user','assistant'}
ABILITIES={'abstention','contradiction_resolution','event_ordering','information_extraction',
           'instruction_following','knowledge_update','multi_session_reasoning',
           'preference_following','summarization','temporal_reasoning'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def rows(path,values):
    with path.open('x',encoding='utf-8',newline='\n') as f:
        for value in values:f.write(json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n')


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def read_rows(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]


def messages(history):
    """Yield raw messages and exact structural locations, without interpreting text."""
    if not isinstance(history,list) or not history:raise ValueError('Nonempty plan list required.')
    for pi,plan in enumerate(history):
        if not isinstance(plan,dict) or len(plan)!=1:raise ValueError('One plan key per container required.')
        name,batches=next(iter(plan.items()))
        if not isinstance(name,str) or not name.startswith('plan-') or not isinstance(batches,list):raise ValueError('Unexpected plan schema.')
        for bi,batch in enumerate(batches):
            if not isinstance(batch,dict) or not isinstance(batch.get('turns'),list):raise ValueError('Batch turns required.')
            for ti,turn in enumerate(batch['turns']):
                if not isinstance(turn,list) or not turn:raise ValueError('Nonempty message group required.')
                for mi,msg in enumerate(turn):
                    if not isinstance(msg,dict) or msg.get('role') not in ROLES or not isinstance(msg.get('content'),str) or not msg['content'].strip():raise ValueError('Unexpected role/content schema.')
                    if 'time_anchor' in msg and not isinstance(msg['time_anchor'],str):raise ValueError('Explicit time anchor must be a string.')
                    yield [pi,name,bi,ti,mi],msg


def project_history(history,conversation_id):
    reader=[];audit=[]
    for i,(location,msg) in enumerate(messages(history)):
        sid=f'{conversation_id}-M{i:06d}'
        reader.append({'id':sid,'conversation_id':conversation_id,'sequence':i,'role':msg['role'],
                       'text':msg['content'],'time_anchor_raw':msg.get('time_anchor')})
        audit.append({'id':sid,'location':location,'metadata':{k:v for k,v in msg.items() if k not in {'role','content','time_anchor'}},
                      'had_time_anchor':'time_anchor' in msg})
    if not reader:raise ValueError('No history messages.')
    return reader,audit


def project_questions(probes,conversation_id):
    if not isinstance(probes,dict) or set(probes)!=ABILITIES:raise ValueError('Every declared BEAM ability required; no subset selection.')
    reader=[];labels=[]
    for ability,items in probes.items():
        if not isinstance(items,list) or len(items)!=2:raise ValueError('Exactly two probes per ability required.')
        for within,item in enumerate(items):
            if not isinstance(item,dict) or not isinstance(item.get('question'),str) or not item['question'].strip():raise ValueError('Question text required.')
            if 'rubric' not in item or not item['rubric']:raise ValueError('Evaluator rubric required.')
            qid=f'{conversation_id}-Q{len(reader):04d}'
            reader.append({'id':qid,'conversation_id':conversation_id,'question':item['question']})
            labels.append({'id':qid,'conversation_id':conversation_id,'ability':ability,'within_ability':within,
                           'annotations':{k:v for k,v in item.items() if k!='question'}})
    return reader,labels


def prepare(source,output,expected_conversations):
    source=source.resolve();output=output.resolve()
    if not 1<=expected_conversations<=10:raise ValueError('Expected conversation count must be1through10.')
    if output.is_relative_to(ROOT) or output==source or output.is_relative_to(source):raise ValueError('Private outputs must be outside Git and source trees.')
    dirs=sorted([p for p in source.iterdir() if p.is_dir()],key=lambda p:int(p.name) if p.name.isdigit() else 100000)
    if any(not p.name.isdigit() or not 1<=int(p.name)<=10 for p in dirs):raise ValueError('Unexpected conversation directory.')
    if len(dirs)!=expected_conversations or len({int(p.name) for p in dirs})!=len(dirs):raise ValueError('Missing/extra conversation; no silent partial run.')
    if expected_conversations==10 and {int(p.name) for p in dirs}!=set(range(1,11)):raise ValueError('Full tier requires IDs1through10.')
    source_files=[p/name for p in dirs for name in ['chat_trunecated.json','probing_questions/probing_questions.json']]
    if any(not p.is_file() for p in source_files):raise ValueError('Missing conversation/probe input file.')
    before={p.relative_to(source).as_posix():sha(p) for p in source_files}
    output.mkdir(parents=True,exist_ok=False)
    for name in ['reader','evaluation','audit']:(output/name).mkdir()
    full_history=[];full_audit=[];questions=[];labels=[];locations={}
    for directory in dirs:
        cid='BEAM10M-'+str(int(directory.name))
        h=load(directory/'chat_trunecated.json');p=load(directory/'probing_questions/probing_questions.json')
        rh,ah=project_history(h,cid);rq,eq=project_questions(p,cid)
        # Verify exact message/annotation reconstruction before persisting.
        for (location,msg),r,a in zip(messages(h),rh,ah,strict=True):
            rebuilt={'role':r['role'],'content':r['text'],**a['metadata']}
            if a['had_time_anchor']:rebuilt['time_anchor']=r['time_anchor_raw']
            if msg!=rebuilt or location!=a['location']:raise ValueError('Message reconstruction failed.')
        for r,e in zip(rq,eq,strict=True):
            if p[e['ability']][e['within_ability']]!={'question':r['question'],**e['annotations']}:raise ValueError('Probe reconstruction failed.')
        full_history.extend(rh);full_audit.extend(ah);questions.extend(rq);labels.extend(eq)
        locations[cid]={'messages':len(rh),'questions':len(rq)}
    rows(output/'reader/history.jsonl',full_history);rows(output/'reader/questions.jsonl',questions)
    rows(output/'audit/message-provenance.jsonl',full_audit);rows(output/'evaluation/labels.jsonl',labels)
    if read_rows(output/'reader/history.jsonl')!=full_history or read_rows(output/'reader/questions.jsonl')!=questions or read_rows(output/'audit/message-provenance.jsonl')!=full_audit or read_rows(output/'evaluation/labels.jsonl')!=labels:raise ValueError('Persisted readback differs.')
    if any(sha(source/name)!=h for name,h in before.items()):raise ValueError('Source input changed.')
    manifest={'adapter':'beam-transfer-format-v1','source_revision':'b2da22eac88bb0874c64665f13457eb99835774a',
        'source_files_sha256':before,'output_files_sha256':{p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*.jsonl'))},
        'conversations':len(dirs),'full_tier_conversations':10,'full_tier':len(dirs)==10,
        'coverage':locations,'messages':len(full_history),'questions':len(questions),
        'source_roles':dict(Counter(r['role'] for r in full_history)),
        'probe_abilities':dict(Counter(r['ability'] for r in labels)),
        'reader_question_keys':['id','conversation_id','question'],
        'stream_order_is_not_calendar_or_fact_validity':True,'construction_metadata_excluded_from_reader':True,
        'exact_message_and_probe_reconstruction':True,'persisted_readback_exact':True,
        'new_model_calls':0,'memory_candidate_evaluated':False,'benchmark_score':None}
    write(output/'manifest.json',manifest)
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-conversations',type=int,required=True)
    args=p.parse_args()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():raise ValueError('Freeze adapter code before real-data preparation.')
    result=prepare(args.source,args.output,args.expected_conversations)
    result['execution_source']={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'script_sha256':sha(Path(__file__)),'plan_sha256':sha(PUBLIC/'PLAN.md'),'clean_tree':True}
    # Source receipt is separate so the format-only manifest remains reproducible.
    write(args.output/'execution.json',result['execution_source'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
