"""Whole-H1 paired ordering intervention; no new source selection or model judge."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import h1_evidence_density_v1 as D

C=D.C
DATA=ROOT/'data/lab/h1-chronological-pack-v1'
ARMS=('original','chronological')
CALLS=339


def ordered(ids,sources):
    return sorted(ids,key=lambda sid:sources[sid].recorded)


def ledger_count(ledger):
    rows=C.P.read_rows(ledger);keys=[r['key'] for r in rows]
    if len(keys)!=len(set(keys)) or len(keys)+CALLS>D.CAP:
        raise ValueError('Entire paired phase must fit retained-ledger cap3300.')
    return len(keys)


class Reader(D.Reader):
    def __init__(self,config,output,ledger):
        super().__init__(config,output,ledger)
        self.cfg.update(max_calls=CALLS,max_seconds=2400)


def prepare(raw_root,output):
    output.mkdir(parents=True,exist_ok=False)
    inputs={};packets=[];cases=0;unchanged=Counter();config=None
    for split in ['dev','valid']:
        reveal=ROOT/'data/lab/corpus-h1'/('reveal-v0' if split=='dev' else 'valid-b/reveal')
        base=raw_root/f'h1-v5-{split}-reader'
        freeze=json.loads((base/'raw-freeze.json').read_text(encoding='utf-8'))
        if any(C.sha(base/n)!=h for n,h in freeze['files_sha256'].items()):raise ValueError('Parent reader drift.')
        questions=reveal/'queries.jsonl';gold=reveal/'gold.jsonl'
        store=raw_root/f'h1-v2-{split}-memory.jsonl';role_path=raw_root/f'h1-v2-{split}-capture/source-roles.jsonl'
        for name,path in [('questions',questions),('gold',gold),('store',store),('roles',role_path),('parent_freeze',base/'raw-freeze.json')]:inputs[split+'/'+name]=C.sha(path)
        roles={r['source']:r['channel'] for r in C.P.read_rows(role_path)}
        prior={r['id']:r['shown_ids'] for r in C.P.read_rows(base/'answers.jsonl') if r['arm']=='chains'}
        requests={r['key']:r['request'] for r in C.P.read_rows(base/'attempts.jsonl')}
        qs=C.P.read_rows(questions)
        if len(qs)!=84 or set(prior)!={f'Q{i:06d}' for i in range(84)}:raise ValueError('Full H1 roster required.')
        with C.V5.Memory(store) as memory:
            for i,q in enumerate(qs):
                if set(q)!={'query_id','question','asked_on_day'}:raise ValueError('Queries must be gold-free.')
                qid=f'Q{i:06d}';ids=prior[qid];req=requests['read-chains-'+qid]
                cfg={k:deepcopy(req[k]) for k in ['model','options']};cfg['options'].pop('seed')
                if config is not None and cfg!=config:raise ValueError('Parent reader configuration differs.')
                config=cfg
                if len(ids)>3 or any(memory.sources[s].scope!='h1-'+split or memory.sources[s].recorded>q['asked_on_day'] for s in ids):raise ValueError('Source outside scope/time/budget.')
                choices={'original':list(ids),'chronological':ordered(ids,memory.sources)}
                unchanged[split]+=choices['original']==choices['chronological']
                arms=ARMS if cases%2==0 else ARMS[::-1];cases+=1
                for arm in arms:
                    pack=C.H4.pack(memory,roles,choices[arm])
                    if pack['ids']!=choices[arm]:raise ValueError('Complete notes were truncated.')
                    messages=[{'role':'system','content':C.SYSTEM+C.AUTH},
                              {'role':'user','content':pack['context']+'\nQuestion: '+q['question']}]
                    if arm=='original' and messages!=req['messages']:raise ValueError('Original native packet mismatch.')
                    C.P.append(output/'packets.jsonl',{'split':split,'id':qid,'query_id':q['query_id'],
                        'arm':arm,'shown_ids':choices[arm],'messages':messages,'call_key':'read-'+split+'-'+qid+'-'+arm})
    if cases!=168:raise ValueError('Incomplete cases.')
    cfg=json.loads((D.DATA/'preparation.json').read_text(encoding='utf-8'))['reader_config']
    if config!={k:cfg[k] for k in ['model','options']}:raise ValueError('Pinned actual reader options differ.')
    ledger=raw_root/'h1-local-ledger.jsonl'
    prep={'cases':cases,'primary_calls':336,'control_calls':3,'planned_calls':CALLS,
        'local_cap':D.CAP,'local_ledger_before':ledger_count(ledger),'local_ledger_digest_before':C.sha(ledger),
        'api_ledger_digest_before':C.sha(raw_root/'api-ledger.jsonl'),'packet_digest':C.sha(output/'packets.jsonl'),
        'input_digests':inputs,'reader_config':cfg,'unchanged_pairs':dict(unchanged),
        'answer_fragments_read_at_preparation':False,'new_oracle_source_selection':False}
    C.write(output/'preparation.json',prep)
    print(json.dumps({k:v for k,v in prep.items() if k not in ['input_digests','reader_config']},indent=2))


def run(raw_root,output):
    if C.git('status','--porcelain'):raise ValueError('Commit code/preparation before generation.')
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    if prep!=json.loads((DATA/'preparation.json').read_text(encoding='utf-8')) or C.sha(output/'packets.jsonl')!=prep['packet_digest']:raise ValueError('Prepared freeze differs.')
    if any((output/p).exists() for p in ['manifest.json','attempts.jsonl','responses.jsonl','answers.jsonl']):raise ValueError('No overwrite or retry.')
    ledger=raw_root/'h1-local-ledger.jsonl'
    if ledger_count(ledger)!=prep['local_ledger_before'] or C.sha(ledger)!=prep['local_ledger_digest_before']:raise ValueError('Ledger prefix changed.')
    if C.sha(raw_root/'api-ledger.jsonl')!=prep['api_ledger_digest_before']:raise ValueError('Paid ledger changed.')
    source={'git_head':C.git('rev-parse','HEAD'),'clean_tree':True,'digests':{
        p.relative_to(ROOT).as_posix():C.sha(p) for p in [Path(__file__),DATA/'PLAN.md',DATA/'preparation.json',Path(D.__file__),Path(C.__file__),Path(C.P.__file__),Path(C.H4.__file__)]}}
    reader=Reader(prep['reader_config'],output,ledger)
    C.write(output/'manifest.json',{'source':source,'config':reader.cfg,'preparation':prep})
    try:
        C.write(output/'preflight.json',reader.preflight());C.V5.S.controls(reader,'local14b',output)
        for p in C.P.read_rows(output/'packets.jsonl'):
            raw=reader.ask(p['call_key'],p['messages'],7,output_schema=C.SCHEMA)
            C.P.append(output/'answers.jsonl',{k:p[k] for k in ['split','id','query_id','arm','call_key','shown_ids']}|{'answer':C.parse(raw['text'])})
        finish=reader.finish()
        if len(C.P.read_rows(ledger))!=prep['local_ledger_before']+CALLS:raise ValueError('Actual call count differs.')
        if C.sha(raw_root/'api-ledger.jsonl')!=prep['api_ledger_digest_before']:raise ValueError('Unexpected API call.')
        C.write(output/'finished.json',finish|{'local_ledger_after':len(C.P.read_rows(ledger)),
            'local_ledger_digest_after':C.sha(ledger),'api_ledger_unchanged':True})
    finally:reader.release()
    C.write(output/'raw-freeze.json',{'files_sha256':{p.name:C.sha(p) for p in sorted(output.iterdir()) if p.is_file()},'source':source})
    print('All paired outputs frozen before scoring.',flush=True)


def score(raw_root,output,freeze_commit,destination):
    raw=(output/'raw-freeze.json').read_bytes()
    if raw!=subprocess.check_output(['git','show',freeze_commit+':data/lab/h1-chronological-pack-v1/raw-freeze.json'],cwd=ROOT):raise ValueError('Raw freeze must be committed first.')
    freeze=json.loads(raw)
    if any(C.sha(output/n)!=h for n,h in freeze['files_sha256'].items()):raise ValueError('Raw evidence drift.')
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    gold={};old={}
    for split in ['dev','valid']:
        p=ROOT/'data/lab/corpus-h1'/('reveal-v0/gold.jsonl' if split=='dev' else 'valid-b/reveal/gold.jsonl')
        if C.sha(p)!=prep['input_digests'][split+'/gold']:raise ValueError('Gold drift.')
        gold[split]={r['query_id']:r for r in C.P.read_rows(p)}
        old[split]={r['id']:r['answer'] for r in C.P.read_rows(raw_root/f'h1-v5-{split}-reader/answers.jsonl') if r['arm']=='chains'}
    packets=C.P.read_rows(output/'packets.jsonl');answers=C.P.read_rows(output/'answers.jsonl')
    attempts=C.P.read_rows(output/'attempts.jsonl');responses=C.P.read_rows(output/'responses.jsonl')
    req={r['key']:r for r in attempts};res={r['key']:r for r in responses};saved={r['call_key']:r for r in answers}
    controls=C.P.read_rows(output/'controls.jsonl')
    if len(packets)!=336 or len(answers)!=336 or len(saved)!=336 or len(attempts)!=CALLS or len(responses)!=CALLS or set(req)!=set(res) or len(controls)!=3 or not all(r['correct'] for r in controls):raise ValueError('Incomplete matrix/controls.')
    records=[];parse_failures=0;drift=[]
    for p in packets:
        key=p['call_key'];request=req[key]['request'];actual=C.parse(res[key]['text'])
        if request['messages']!=p['messages'] or C.P.sha(request)!=req[key]['request_sha256'] or request['format']!=C.SCHEMA or saved[key]['answer']!=actual:raise ValueError('Actual request/answer mismatch.')
        parse_failures+=actual is None;g=gold[p['split']][p['query_id']];result=C.scorer.score(actual or '',g)
        if p['arm']=='original' and actual!=old[p['split']][p['id']]:drift.append({'split':p['split'],'id':p['id']})
        records.append({k:p[k] for k in ['split','id','arm']}|{'family':g['case_id'].rsplit('-',1)[0]}|
            {k:result[k] for k in ['answered','leaked','abstained']}|{'clean_answered':int(result['answered'] and not result['leaked'])})
    totals=[];pairs=[]
    for split in ['dev','valid']:
        for family in ['ALL',*sorted({r['family'] for r in records})]:
            for arm in ARMS:
                rs=[r for r in records if r['split']==split and r['arm']==arm and (family=='ALL' or r['family']==family)]
                totals.append({'split':split,'family':family,'arm':arm,'n':len(rs),**{k:sum(r[k] for r in rs) for k in ['answered','leaked','clean_answered','abstained']}})
        for qid in old[split]:
            a,b=[next(r for r in records if r['split']==split and r['id']==qid and r['arm']==arm) for arm in ARMS]
            if any(a[k]!=b[k] for k in ['answered','leaked','clean_answered']):pairs.append({'split':split,'id':qid,'family':a['family'],'original':a,'chronological':b})
    valid=[r for r in totals if r['split']=='valid'];by={(r['family'],r['arm']):r for r in valid}
    no_new_leak=not any(p['split']=='valid' and p['chronological']['leaked']>p['original']['leaked'] for p in pairs)
    improved=by['ALL','chronological']['clean_answered']>by['ALL','original']['clean_answered']
    no_family_loss=all(by[f,'chronological']['clean_answered']>=by[f,'original']['clean_answered'] for f in {r['family'] for r in valid})
    passed=no_new_leak and improved and no_family_loss
    result={'totals':totals,'records':records,'changed_pairs':pairs,'original_text_drift':drift,
        'parse_failures':parse_failures,'actual_local_calls':CALLS,'new_api_calls':0,
        'screen':{'no_new_validation_leak':no_new_leak,'validation_clean_gain':improved,'no_validation_family_loss':no_family_loss,'fresh_transfer_candidate':passed},
        'decision':'Fresh transfer candidate only; no adoption.' if passed else 'Reject automatic adoption; preserve diagnostic and all tradeoffs.',
        'claim':'Spent public single-seed exploratory comparison, not independent confirmation.'}
    C.write(destination,result);print(json.dumps({'all_family_totals':[r for r in totals if r['family']=='ALL'],'screen':result['screen'],'decision':result['decision']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['prepare','run','score']:
        p=sub.add_parser(name);p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
        if name=='score':p.add_argument('--freeze-commit',required=True);p.add_argument('--destination',type=Path,required=True)
    args=vars(parser.parse_args());globals()[args.pop('command')](**args)
