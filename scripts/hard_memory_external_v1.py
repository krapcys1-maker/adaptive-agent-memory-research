"""Gold-separated external 262k multi-hop diagnostic; no answer repair or oracle."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import string
import subprocess

import flash_reader_client_v1 as F
import nie_reader_pilot as P
import reader_model_compare_v1 as R

ROOT=P.ROOT
DATA=ROOT/'data/lab/hard-memory-external-v1'
NOW='2026-11-04T00:00:00Z'


def cfg():return json.loads((DATA/'config.json').read_text(encoding='utf-8'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def records(path):return P.read_rows(path)


def source():
    paths=[Path(__file__),Path(F.__file__),Path(P.__file__),Path(R.__file__),Path(P.bridge.__file__),P.bridge.KERNEL,
           R.REFERENCE/'manifest.json',DATA/'config.json',DATA/'PLAN.md']
    return {'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'clean_tree':not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
            'sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in paths}}


def write_rows(path,rows):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        for row in rows:stream.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n')


def split_source(row):
    """Only preparation sees answer data. Reader input has an explicit allowlist."""
    archive=[{'id':f'F{i:06d}','ordinal':i,'text':line} for i,line in enumerate(row['context'].splitlines()) if line.strip()]
    questions=[{'id':f'Q{i:03d}','question':q} for i,q in enumerate(row['questions'])]
    gold=[{'id':f'Q{i:03d}','answers':answers} for i,answers in enumerate(row['answers'])]
    if not len(questions)==len(gold) or not questions:raise ValueError('Unaligned official questions/answers.')
    return archive,questions,gold


def packets(archive,questions,config):
    if any(set(q)!={'id','question'} for q in questions):raise ValueError('Only question text and opaque ID may reach inference.')
    if any(set(r)!={'id','ordinal','text'} for r in archive):raise ValueError('Archive must not contain gold labels or typed routing.')
    mk=P.bridge.load_kernel();epoch=datetime(2026,1,1,tzinfo=timezone.utc)
    index=mk.build_index([mk.Item(r['id'],'event','world_knowledge',
        (epoch+timedelta(seconds=r['ordinal'])).isoformat(),r['text']) for r in archive],NOW)
    by_id={r['id']:r for r in archive};output=[]
    for q in questions:
        for arm in ['N','K','B']:
            if arm=='N':result={'items':[],'status':'no-memory','reasons':[]}
            else:
                profile=dict(mk.PROFILES['lexical'],timeout_ms=float('inf'),require_zone=True)
                if arm=='B':profile.update(k=config['rank_k'],lex_tau=1e-9,min_evidence=0,names=False)
                result=mk.retrieve(index,q['question'],'note',NOW,profile)
                if result.get('error') or result['status']=='degraded':raise ValueError('Kernel refused offline retrieval.')
            ranked=[r.id for r in result['items']];shown=[];context=''
            for ident in ranked:
                candidate=shown+[ident]
                text='\n'.join(f'[{i}] {by_id[i]["text"]}' for i in sorted(candidate,key=lambda i:by_id[i]['ordinal']))
                if len(text.encode('utf-8'))<=config['max_context_bytes']:shown,context=candidate,text
            shown=sorted(shown,key=lambda i:by_id[i]['ordinal'])
            output.append({'key':q['id']+':'+arm,'id':q['id'],'arm':arm,'question':q['question'],'context':context,
                           'ranked_ids':ranked,'shown_ids':shown,'status':result['status']})
    return output


def prepare(source_path,output,*,require_clean=True):
    config=cfg();identity=source()
    if require_clean and not identity['clean_tree']:raise ValueError('Commit the execution source first.')
    if digest(source_path)!=config['source_sha256']:raise ValueError('Official dataset bytes differ.')
    import pyarrow.parquet as pq  # Optional local preparation dependency, never needed by CI/scoring.
    rows=[r for r in pq.read_table(source_path).to_pylist() if r['metadata']['source']==config['sub_dataset']]
    if len(rows)!=1 or len(rows[0]['questions'])!=config['n_questions']:raise ValueError('Complete hard variant required.')
    archive,questions,gold=split_source(rows[0]);output.mkdir(parents=True,exist_ok=False)
    write_rows(output/'archive.jsonl',archive);write_rows(output/'questions.jsonl',questions)
    write_rows(output/'gold.jsonl',gold)
    # Construct retrieval only from the reloaded, gold-free disk records.
    emitted=packets(records(output/'archive.jsonl'),records(output/'questions.jsonl'),config)
    if any(len(json.dumps(messages(p,config),ensure_ascii=False).encode())>config['max_api_message_bytes'] for p in emitted):
        raise ValueError('Prepared packet exceeds the committed message budget before inference.')
    write_rows(output/'packets.jsonl',emitted)
    P.write(output/'preparation.json',{'execution':identity,'source_sha256':digest(source_path),
        'variant':config['sub_dataset'],'context_characters':len(rows[0]['context']),
        'archive_records':len(archive),'questions':len(questions),'packet_count':len(emitted),
        'inputs':[{'name':name,'sha256':digest(output/(name+'.jsonl'))} for name in ['archive','questions','gold','packets']]})
    if source()['sha256']!=identity['sha256']:raise RuntimeError('Execution source changed.')


def load_inputs(prepared):
    manifest=json.loads((prepared/'preparation.json').read_text(encoding='utf-8'))
    expected={row['name']:row['sha256'] for row in manifest['inputs']}
    # Deliberately do not open or validate gold during generation.
    for name in ['archive','questions','packets']:
        if digest(prepared/(name+'.jsonl'))!=expected[name]:raise ValueError('Prepared reader input changed: '+name)
    questions=records(prepared/'questions.jsonl');rows=records(prepared/'packets.jsonl')
    if manifest['source_sha256']!=cfg()['source_sha256'] or len(questions)!=cfg()['n_questions']:raise ValueError('Source/denominator differs.')
    if len({q['id'] for q in questions})!=len(questions):raise ValueError('Duplicate question ID.')
    if any(set(q)!={'id','question'} for q in questions):raise ValueError('Forbidden question metadata.')
    expected_keys={q['id']+':'+a for q in questions for a in ['N','K','B']}
    if len(rows)!=len(expected_keys) or {r['key'] for r in rows}!=expected_keys:raise ValueError('Incomplete/duplicate packets.')
    return manifest,rows


def messages(packet,config):
    return [{'role':'system','content':config['reader_system']},
            {'role':'user','content':'RECORDED MEMORY:\n'+(packet['context'] or '(none)')+'\nQUESTION: '+packet['question']+'\nReturn JSON {"value":"..."}.'}]


def value(response):
    if response.get('done_reason')=='length':return None
    try:obj=json.loads(response['text'])
    except (ValueError,TypeError):return None
    if isinstance(obj,dict) and set(obj)=={'value'} and isinstance(obj['value'],str) and obj['value'].strip():return obj['value'].strip()
    return None


def run(prepared,output,backend,ledger,*,factory=None,require_clean=True):
    config=cfg();F.permitted(config);identity=source()
    if require_clean and not identity['clean_tree']:raise ValueError('Commit source before inference.')
    preparation,rows=load_inputs(prepared);arms=config['local_arms'] if backend=='local14b' else config['flash_arms']
    expected={r['key'] for r in rows if r['arm'] in arms}|{f'positive-{i}' for i in range(3)}
    output.mkdir(parents=True,exist_ok=False)
    P.write(output/'manifest.json',{'execution':identity,'backend':backend,'config':config,'preparation':preparation,
                                  'started_at':datetime.now(timezone.utc).isoformat()})
    if factory:client=factory(config,output)
    elif backend=='flash':client=F.FlashReader(config,output,ledger,'hard-MAB-262k')
    elif backend=='local14b':
        local=dict(R.local_config(config),max_calls=config['local_max_calls']);client=P.LocalReader(local,output)
    else:raise ValueError('Only authorized local/Flash backends are permitted.')
    completed=False
    try:
        P.write(output/'environment.json',client.preflight())
        for i,token in enumerate(config['positive_controls']):
            m=[{'role':'system','content':'Return JSON with only the key value.'},{'role':'user','content':f'The control value is {token}. What is it?'}]
            answer=client.ask(f'positive-{i}',m,17)
            if value(answer)!=token:raise RuntimeError('Positive control failed without retry.')
        for packet in rows:
            if packet['arm'] not in arms:continue
            # Reload persisted packets before each completion; never read archive/gold to repair an answer.
            current=[r for r in records(prepared/'packets.jsonl') if r['key']==packet['key']]
            if len(current)!=1 or current[0]!=packet:raise RuntimeError('Reader packet changed during inference.')
            response=client.ask(packet['key'],messages(packet,config),17+int(packet['id'][1:]))
            P.append(output/'answers.jsonl',{'key':packet['key'],'id':packet['id'],'arm':packet['arm'],
                'raw_value':value(response),'packet_sha256':P.sha(packet),'shown_ids':packet['shown_ids']})
        P.write(output/'completion.json',client.finish())
        if source()['sha256']!=identity['sha256']:raise RuntimeError('Source changed during inference.')
        completed=True
    except Exception as exc:
        P.write(output/'failure.json',{'type':type(exc).__name__,'http_status':getattr(exc,'code',None),
                                    'message':'Stopped without retry; retained evidence and reservations.'})
    finally:client.release()
    attempts=records(output/'attempts.jsonl');answers=records(output/'responses.jsonl')
    complete=completed and all(len(rows)==len(expected) and {r['key'] for r in rows}==expected for rows in [attempts,answers])
    P.write(output/'finished.json',{'complete':complete,'calls':len(attempts),'primary_calls':len(expected)-3,
        'raw_files':[{'name':p.name,'sha256':digest(p)} for p in sorted(output.glob('*.json*'))]})
    return complete


def normalize(text):
    text=text.lower().translate(str.maketrans('','',string.punctuation))
    return ' '.join(re.sub(r'\b(a|an|the)\b',' ',text).split())


def metrics(prediction,aliases):
    predicted=normalize(prediction or '');golds=[normalize(a) for a in aliases]
    def f1(gold):
        p,g=predicted.split(),gold.split();overlap=sum((Counter(p)&Counter(g)).values())
        return 2*overlap/(len(p)+len(g)) if p and g else float(p==g)
    return {'exact':any(predicted==g for g in golds),'f1':max(map(f1,golds)),
            'substring':any(bool(g) and g in predicted for g in golds)}


def committed(path):
    relative=path.relative_to(ROOT).as_posix()
    stored=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
    if stored!=path.read_bytes():raise ValueError('Required freeze is not committed byte-identically.')


def score(prepared,output,raw_freeze):
    freeze=json.loads(raw_freeze.read_text(encoding='utf-8'))
    # Gold join requires an independently persisted, committed raw-response freeze.
    committed(raw_freeze)
    if freeze['response_sha256']!=digest(output/'responses.jsonl'):raise ValueError('Raw response differs from freeze.')
    frozen_files={r['name']:r['sha256'] for r in freeze['files']}
    required_files={'attempts.jsonl','responses.jsonl','answers.jsonl','manifest.json','finished.json','completion.json','environment.json'}
    if not required_files<=set(frozen_files) or any(digest(output/name)!=sha for name,sha in frozen_files.items()):
        raise ValueError('Raw execution artifact differs from freeze.')
    finished=json.loads((output/'finished.json').read_text());manifest=json.loads((output/'manifest.json').read_text())
    if not finished['complete']:raise ValueError('An incomplete run cannot be scored as complete.')
    preparation,pack=load_inputs(prepared);by_key={r['key']:r for r in pack}
    expected_gold=next(x['sha256'] for x in preparation['inputs'] if x['name']=='gold')
    if digest(prepared/'gold.jsonl')!=expected_gold:raise ValueError('Gold changed after preparation.')
    gold={r['id']:r['answers'] for r in records(prepared/'gold.jsonl')}
    attempts=records(output/'attempts.jsonl');responses=records(output/'responses.jsonl');saved=records(output/'answers.jsonl')
    backend=manifest['backend'];config=manifest['config'];expected_arms=config['local_arms'] if backend=='local14b' else config['flash_arms']
    for name,sha in manifest['execution']['sha256'].items():
        if digest(ROOT/name)!=sha:raise ValueError('Execution source changed: '+name)
    expected={k for k,r in by_key.items() if r['arm'] in expected_arms}
    if len(saved)!=len(expected) or {r['key'] for r in saved}!=expected:raise ValueError('Saved answer coverage differs.')
    response_by_key={r['key']:r for r in responses};attempt_by_key={r['key']:r for r in attempts}
    expected_all=expected|{f'positive-{i}' for i in range(3)}
    if any(len(rows)!=len(expected_all) or {r['key'] for r in rows}!=expected_all for rows in (responses,attempts)):raise ValueError('Request/response coverage differs.')
    for i,token in enumerate(config['positive_controls']):
        if value(response_by_key[f'positive-{i}'])!=token:raise ValueError('Positive control differs.')
    scored=[]
    for row in saved:
        key=row['key'];packet=by_key[key];raw=response_by_key[key];attempt=attempt_by_key[key]
        required={'key':key,'id':packet['id'],'arm':packet['arm'],'raw_value':value(raw),'packet_sha256':P.sha(packet),'shown_ids':packet['shown_ids']}
        if row!=required:raise ValueError('Saved response accounting differs.')
        if attempt['request']['messages']!=messages(packet,config) or attempt['request_sha256']!=P.sha(attempt['request']):raise ValueError('Reader request differs from persisted input.')
        seed=17+int(packet['id'][1:])
        body={'model':'deepseek-flash','messages':messages(packet,config),'stream':False,'temperature':0,
              'max_tokens':64,'thinking':{'type':'disabled'},'response_format':{'type':'json_object'}} if backend=='flash' else {
              'model':config['local_model'],'messages':messages(packet,config),'stream':False,'format':'json','keep_alive':'5m',
              'options':dict(R.local_config(config)['options'],seed=seed)}
        if attempt['request']!=body:raise ValueError('Inference transport settings differ.')
        observed=metrics(value(raw),gold[row['id']])
        scored.append({'key':key,'id':row['id'],'arm':row['arm'],**observed,'unknown':str(value(raw)).upper()=='UNKNOWN',
                       'malformed_or_truncated':value(raw) is None,'shown_ids':packet['shown_ids'],'shown_bytes':len(packet['context'].encode())})
    arms={}
    for arm in expected_arms:
        part=[r for r in scored if r['arm']==arm]
        if len(part)!=config['n_questions']:raise ValueError('Primary denominator differs.')
        arms[arm]={'n':len(part),'exact':sum(r['exact'] for r in part),'mean_f1':sum(r['f1'] for r in part)/len(part),
            'substring':sum(r['substring'] for r in part),'unknown':sum(r['unknown'] for r in part),
            'malformed_or_truncated':sum(r['malformed_or_truncated'] for r in part),'nonempty_context':sum(bool(r['shown_ids']) for r in part)}
    return {'backend':backend,'complete':True,'arms':arms,'per_question':scored,'generation_calls':len(attempts),
        'metric':'Official-style normalized exact match on emitted JSON value; F1/substring are separate diagnostics.',
        'scope':'Full 100-question hard 262k multi-hop variant; bounded offline raw-line kernel adapter, not the official full-agent harness.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['prepare','run','score'])
    ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--source',type=Path)
    ap.add_argument('--output',type=Path);ap.add_argument('--backend',choices=['local14b','flash']);ap.add_argument('--ledger',type=Path)
    ap.add_argument('--raw-freeze',type=Path);args=ap.parse_args()
    if args.mode=='prepare':prepare(args.source,args.prepared)
    elif args.mode=='run':return 0 if run(args.prepared,args.output,args.backend,args.ledger) else 1
    else:
        result=score(args.prepared,args.output,args.raw_freeze)
        P.write(args.output/'scores.json',result);print(json.dumps(result['arms']))
    return 0


if __name__=='__main__':raise SystemExit(main())
