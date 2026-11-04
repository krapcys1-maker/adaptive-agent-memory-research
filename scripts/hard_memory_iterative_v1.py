"""Bounded local-only iterative search on the spent external development variant."""
from __future__ import annotations

import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess

import hard_memory_external_v1 as H

DATA=H.ROOT/'data/lab/hard-memory-iterative-v1'
ROUNDS=6
SCHEMA={'type':'object','properties':{'value':{'type':'string'},'queries':{'type':'array','items':{'type':'string'},'maxItems':2}},
        'required':['value','queries'],'additionalProperties':False}
SYSTEM=('You solve counterfactual multi-step questions using only the numbered memory records shown. '
 'Later source numbers override earlier assertions about the same relation. Never substitute world knowledge. '
 'If every required relation is supported, return the concise final value and an empty queries list. '
 'Otherwise return value UNKNOWN and up to two specific next search queries for missing links. '
 'Build a next query around the intermediate entity actually found in the shown records and the missing relation; '
 'do not just repeat the original compound question. Search queries are tool requests, not newly accepted facts. '
 'Return JSON with exactly value (string) and queries (list of strings), without explanation.')


def source():
    identity=H.source()
    for path in [Path(__file__),DATA/'PLAN.md']:
        identity['sha256'][path.relative_to(H.ROOT).as_posix()]=H.digest(path)
    return identity


def parse(response):
    if response.get('done_reason')=='length':return None,[]
    try:obj=json.loads(response['text'])
    except (ValueError,TypeError):return None,[]
    if not isinstance(obj,dict) or set(obj)!={'value','queries'}:return None,[]
    if not isinstance(obj['value'],str) or not isinstance(obj['queries'],list) or len(obj['queries'])>2:return None,[]
    if any(not isinstance(q,str) or not q.strip() or len(q)>512 for q in obj['queries']):return None,[]
    return obj['value'].strip() or None,[q.strip() for q in obj['queries']]


def context(ids,by_id,budget):
    selected=[];text=''
    for ident in dict.fromkeys(ids):
        if ident not in by_id:raise ValueError('Search returned an unknown archive ID.')
        candidate=selected+[ident]
        rendered='\n'.join(f'[{i}] {by_id[i]["text"]}' for i in sorted(candidate,key=lambda i:by_id[i]['ordinal']))
        if len(rendered.encode())<=budget:selected,text=candidate,rendered
    return sorted(selected,key=lambda i:by_id[i]['ordinal']),text


def reader_messages(question,shown,searched):
    return [{'role':'system','content':SYSTEM},{'role':'user','content':'RECORDED MEMORY:\n'+(shown or '(none)')+
        '\nORIGINAL QUESTION: '+question+'\nPreviously searched: '+json.dumps([q[:160] for q in sorted(searched)[-4:]],ensure_ascii=False)+
        '\nReturn JSON with value and queries.'}]


def searcher(archive):
    mk=H.P.bridge.load_kernel();epoch=datetime(2026,1,1,tzinfo=timezone.utc)
    index=mk.build_index([mk.Item(r['id'],'event','world_knowledge',(epoch+timedelta(seconds=r['ordinal'])).isoformat(),r['text']) for r in archive],H.NOW)
    profile=dict(mk.PROFILES['lexical'],timeout_ms=float('inf'),require_zone=True,k=12,lex_tau=1e-9,min_evidence=0,names=False)
    def search(query):
        result=mk.retrieve(index,query,'note',H.NOW,profile)
        if result.get('error') or result['status']=='degraded':raise ValueError('Follow-up search failed.')
        return [item.id for item in result['items']]
    return search


def execute(prepared,output,*,factory=None,require_clean=True):
    config=H.cfg();identity=source()
    if require_clean and not identity['clean_tree']:raise ValueError('Commit repair protocol first.')
    preparation,initial=H.load_inputs(prepared)
    initial={p['id']:p for p in initial if p['arm']=='B'}
    archive=H.records(prepared/'archive.jsonl');by_id={r['id']:r for r in archive};questions=H.records(prepared/'questions.jsonl')
    search=searcher(archive)
    output.mkdir(parents=True,exist_ok=False)
    H.P.write(output/'manifest.json',{'execution':identity,'purpose':'Post-hoc same-public-question repair; not held-out transfer',
        'preparation':preparation,'max_rounds':ROUNDS,'max_calls':603,'max_seconds':1200,'context_bytes':4500,
        'system':SYSTEM,'output_schema':SCHEMA,'model':config['local_model'],'model_digest':config['local_digest']})
    local=dict(H.R.local_config(config),max_calls=603,max_seconds=1200,
               options={'temperature':0,'num_ctx':4096,'num_predict':256})
    client=factory(local,output) if factory else H.P.LocalReader(local,output)
    completed=False
    try:
        H.P.write(output/'environment.json',client.preflight())
        cohort=json.loads((H.R.REFERENCE/'manifest.json').read_text())['config']
        for i,token in enumerate(config['positive_controls']):
            messages=H.P.reader_messages(cohort,'control_value','What is the control_value?',{'context':f'The control_value is {token}.'},[])
            if H.value(client.ask(f'positive-{i}',messages,7))!=token:raise RuntimeError('Positive control failed; no retry.')
        for question in questions:
            ident=question['id'];retained=initial[ident]['shown_ids'];shown=initial[ident]['context'];searched={question['question'].casefold()}
            answer=None
            for turn in range(ROUNDS):
                key=f'{ident}:{turn}'
                messages=reader_messages(question['question'],shown,searched)
                response=client.ask(key,messages,17+int(ident[1:]),output_schema=SCHEMA)
                answer,queries=parse(response)
                new_queries=[q for q in queries if q.casefold() not in searched]
                trace={'key':key,'id':ident,'round':turn,'value':answer,'queries':queries,'shown_ids':retained,
                       'context_sha256':H.P.sha(shown),'fresh_queries':new_queries}
                H.P.append(output/'trace.jsonl',trace)
                if answer is None or answer.upper()!='UNKNOWN' or not new_queries or turn==ROUNDS-1:break
                new_ids=[]
                for query in new_queries:
                    searched.add(query.casefold());new_ids.extend(search(query))
                retained,shown=context(new_ids+retained,by_id,4500)
            H.P.append(output/'answers.jsonl',{'id':ident,'value':answer,'rounds':turn+1,'last_key':key})
        H.P.write(output/'completion.json',client.finish())
        if source()['sha256']!=identity['sha256']:raise RuntimeError('Repair source changed during execution.')
        completed=True
    except Exception as exc:
        H.P.write(output/'failure.json',{'type':type(exc).__name__,'message':'Repair stopped without retry.'})
    finally:client.release()
    answers=H.records(output/'answers.jsonl')
    complete=completed and len(answers)==len(questions) and {r['id'] for r in answers}=={r['id'] for r in questions}
    H.P.write(output/'finished.json',{'complete':complete,'answered_questions':len(answers),
        'calls':len(H.records(output/'attempts.jsonl')),'model_judge_calls':0,'paid_calls':0})
    return complete


def score(prepared,output,freeze):
    H.committed(freeze);frozen=json.loads(freeze.read_text())
    if any(H.digest(output/r['name'])!=r['sha256'] for r in frozen['files']):raise ValueError('Frozen raw repair artifacts changed.')
    if not json.loads((output/'finished.json').read_text())['complete']:raise ValueError('Incomplete repair.')
    preparation,_=H.load_inputs(prepared)
    if H.digest(prepared/'gold.jsonl')!=next(r['sha256'] for r in preparation['inputs'] if r['name']=='gold'):raise ValueError('Gold changed.')
    answers=H.records(output/'answers.jsonl');response_rows=H.records(output/'responses.jsonl');responses={r['key']:r for r in response_rows}
    attempts=H.records(output/'attempts.jsonl');requests={r['key']:r for r in attempts};trace_rows=H.records(output/'trace.jsonl')
    if len(responses)!=len(response_rows) or len(requests)!=len(attempts):raise ValueError('Duplicate raw calls.')
    if len(answers)!=H.cfg()['n_questions'] or len({r['id'] for r in answers})!=len(answers):raise ValueError('Repair denominator differs.')
    questions={r['id']:r['question'] for r in H.records(prepared/'questions.jsonl')}
    _,initial=H.load_inputs(prepared);initial={r['id']:r for r in initial if r['arm']=='B'}
    archive=H.records(prepared/'archive.jsonl');by_id={r['id']:r for r in archive};search=searcher(archive)
    expected_calls={f'positive-{i}' for i in range(3)};reconstructed=0
    for row in answers:
        ident=row['id'];retained=initial[ident]['shown_ids'];shown=initial[ident]['context'];searched={questions[ident].casefold()}
        steps=[r for r in trace_rows if r['id']==ident]
        if len(steps)!=row['rounds'] or not 1<=len(steps)<=ROUNDS:raise ValueError('Round coverage differs.')
        for turn,step in enumerate(steps):
            key=f'{ident}:{turn}';expected_calls.add(key);answer,queries=parse(responses[key]);fresh=[q for q in queries if q.casefold() not in searched]
            expected={'key':key,'id':ident,'round':turn,'value':answer,'queries':queries,'shown_ids':retained,
                      'context_sha256':H.P.sha(shown),'fresh_queries':fresh}
            if step!=expected:raise ValueError('Search trace differs from reconstruction.')
            request=requests[key];body=request['request']
            if body['messages']!=reader_messages(questions[ident],shown,searched) or request['request_sha256']!=H.P.sha(body):raise ValueError('Repair reader request differs.')
            if body['format']!=SCHEMA or body['options']!={'temperature':0,'num_ctx':4096,'num_predict':256,'seed':17+int(ident[1:])}:raise ValueError('Repair settings differ.')
            reconstructed+=1
            stop=answer is None or answer.upper()!='UNKNOWN' or not fresh or turn==ROUNDS-1
            if stop!=(turn==len(steps)-1):raise ValueError('Round stopping rule differs.')
            if not stop:
                new_ids=[]
                for query in fresh:searched.add(query.casefold());new_ids.extend(search(query))
                retained,shown=context(new_ids+retained,by_id,4500)
        if row['last_key']!=steps[-1]['key']:raise ValueError('Final round differs.')
    if set(responses)!=expected_calls or set(requests)!=expected_calls or len(trace_rows)!=reconstructed:raise ValueError('Repair call coverage differs.')
    gold={r['id']:r['answers'] for r in H.records(prepared/'gold.jsonl')};scored=[]
    for row in answers:
        if parse(responses[row['last_key']])[0]!=row['value']:raise ValueError('Final answer differs from raw response.')
        scored.append({'id':row['id'],**H.metrics(row['value'],gold[row['id']]),'rounds':row['rounds'],
                       'unknown':str(row['value']).upper()=='UNKNOWN','invalid':row['value'] is None})
    return {'complete':True,'n':len(scored),'exact':sum(r['exact'] for r in scored),
        'mean_f1':sum(r['f1'] for r in scored)/len(scored),'unknown':sum(r['unknown'] for r in scored),
        'invalid':sum(r['invalid'] for r in scored),'total_primary_rounds':sum(r['rounds'] for r in scored),
        'requests_and_search_rounds_reconstructed':reconstructed,
        'per_question':scored,'scope':'Post-hoc repair on the same spent public 100 questions, local only; no generalisation claim.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['run','score'])
    ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--raw-freeze',type=Path);args=ap.parse_args()
    if args.mode=='run':return 0 if execute(args.prepared,args.output) else 1
    result=score(args.prepared,args.output,args.raw_freeze.resolve());H.P.write(args.output/'scores.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='per_question'}));return 0


if __name__=='__main__':raise SystemExit(main())
