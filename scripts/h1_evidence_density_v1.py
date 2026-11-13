"""Whole-family repetition controls with explicit retained-ledger cap3300.

Inherits oracle source identities from a frozen prior control, not answer
labels. No API client, model judge, fallback, retry or canonical-history write.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import h1_obsolete_controls_v1 as C

DATA=ROOT/'data/lab/h1-evidence-density-v1'
ARMS=('neutral_first','neutral_last','stale_repeat_first','stale_repeat_last',
      'correction_repeat_first','correction_repeat_last')
NEUTRAL='Synthetic formatting control: this demonstration uses UTF-8 text and ordinary line endings.'
CAP=3300
CALLS=147


def conditions(supporting,obsolete):
    if supporting==obsolete or not supporting or not obsolete or 'CONTROL_NEUTRAL' in (supporting,obsolete):
        raise ValueError('Distinct real source identities are required.')
    return dict(zip(ARMS,[[supporting,'CONTROL_NEUTRAL',obsolete],
        [obsolete,'CONTROL_NEUTRAL',supporting],[supporting,obsolete,obsolete],
        [obsolete,obsolete,supporting],[supporting,supporting,obsolete],
        [obsolete,supporting,supporting]]))


def ledger_count(ledger,required=CALLS):
    rows=C.P.read_rows(ledger);keys=[r['key'] for r in rows]
    if len(keys)!=len(set(keys)) or len(keys)+required>CAP:
        raise ValueError('Whole density phase would exceed retained-ledger cap3300.')
    return len(keys)


def pack(memory,roles,ids,day):
    if len(ids)!=3:raise ValueError('Exactly three complete notes required.')
    text=''
    for sid in ids:
        if sid=='CONTROL_NEUTRAL':tick,role,content=day,'unknown',NEUTRAL
        else:
            source=memory.sources[sid]
            if source.recorded>day:raise ValueError('Future note in packet.')
            tick,role,content=source.recorded,roles[sid],source.text
        text+=f'[{sid}] day {tick}; source_role={role}: {content}\n'
    if len(text.encode())>4500:raise ValueError('Complete-note budget exceeded.')
    return text


class Reader(C.P.LocalReader):
    def __init__(self,config,output,ledger):
        cfg=deepcopy(config);cfg.update(max_calls=CALLS,max_seconds=1800)
        super().__init__(cfg,output);self.ledger=ledger;self.lock=ledger.with_suffix('.lock')
        with self.lock.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))

    def ask(self,name,messages,seed,*,output_schema=None):
        rows=C.P.read_rows(self.ledger);keys=[r['key'] for r in rows]
        full=self.output.name+':'+name
        if len(keys)!=len(set(keys)) or full in keys or len(keys)>=CAP:
            raise RuntimeError('Cumulative density local cap/identity failure.')
        if name in self.keys or len(self.keys)>=self.cfg['max_calls']:
            raise RuntimeError('Phase call cap/identity failure.')
        C.P.append(self.ledger,{'key':full,'model':self.cfg['model'],'event':'local-attempt'})
        return super().ask(name,messages,seed,output_schema=output_schema)

    def release(self):
        try:super().release()
        finally:self.lock.unlink()


def prepare(raw_root,source_controls,output):
    output.mkdir(parents=True,exist_ok=False)
    prior=json.loads((source_controls/'raw-freeze.json').read_text(encoding='utf-8'))
    if any(C.sha(source_controls/name)!=h for name,h in prior['files_sha256'].items()):
        raise ValueError('Original control freeze changed.')
    parents=[p for p in C.P.read_rows(source_controls/'packets.jsonl') if p['arm']=='old_then_new']
    if len(parents)!=24 or len({(p['split'],p['id']) for p in parents})!=24:
        raise ValueError('Every original OBSOLETE case is required.')
    inputs={};packets=[]
    for split in ['dev','valid']:
        reveal=ROOT/'data/lab/corpus-h1'/('reveal-v0' if split=='dev' else 'valid-b/reveal')
        questions=reveal/'queries.jsonl';qs={q['query_id']:q for q in C.P.read_rows(questions)}
        store=raw_root/f'h1-v2-{split}-memory.jsonl';role_path=raw_root/f'h1-v2-{split}-capture/source-roles.jsonl'
        roles={r['source']:r['channel'] for r in C.P.read_rows(role_path)}
        for name,path in [('questions',questions),('store',store),('roles',role_path),('gold',reveal/'gold.jsonl')]:inputs[split+'/'+name]=C.sha(path)
        with C.V5.Memory(store) as memory:
            for p in [p for p in parents if p['split']==split]:
                obsolete,supporting=p['shown_ids'];q=qs[p['query_id']]
                if any(memory.sources[s].scope!='h1-'+split for s in [obsolete,supporting]):
                    raise ValueError('Source scope mismatch.')
                choices=conditions(supporting,obsolete);case=len(packets)//6
                order=ARMS[case%6:]+ARMS[:case%6]
                for arm in order:
                    ids=choices[arm];context=pack(memory,roles,ids,q['asked_on_day'])
                    row={k:p[k] for k in ['split','id','query_id']}
                    row.update(arm=arm,shown_ids=ids,call_key='read-'+split+'-'+p['id']+'-'+arm,
                        messages=[{'role':'system','content':C.SYSTEM+C.AUTH},
                                  {'role':'user','content':context+'\nQuestion: '+q['question']}])
                    packets.append(row);C.P.append(output/'packets.jsonl',row)
    if len(packets)!=144:raise ValueError('Incomplete six-condition roster.')
    ledger=raw_root/'h1-local-ledger.jsonl'
    report={'cases':24,'primary_calls':144,'control_calls':3,'planned_calls':CALLS,
        'local_cap':CAP,'local_ledger_before':ledger_count(ledger),
        'local_ledger_digest_before':C.sha(ledger),'api_ledger_digest_before':C.sha(raw_root/'api-ledger.jsonl'),
        'packet_digest':C.sha(output/'packets.jsonl'),'input_digests':inputs,
        'parent_control_freeze_digest':C.sha(source_controls/'raw-freeze.json'),
        'inherited_oracle_source_ids':True,'answer_fragments_read_at_preparation':False,
        'neutral_source_is_synthetic':True,'arms':list(ARMS),
        'reader_config':json.loads((source_controls/'manifest.json').read_text(encoding='utf-8'))['config']}
    C.write(output/'preparation.json',report);print(json.dumps({k:v for k,v in report.items() if k!='reader_config'},indent=2))


def run(raw_root,output):
    if C.git('status','--porcelain'):raise ValueError('Freeze code/preparation before generation.')
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    if prep!=json.loads((DATA/'preparation.json').read_text(encoding='utf-8')) or C.sha(output/'packets.jsonl')!=prep['packet_digest']:
        raise ValueError('Prepared packet/freeze mismatch.')
    if any((output/p).exists() for p in ['manifest.json','attempts.jsonl','responses.jsonl','answers.jsonl']):
        raise ValueError('Artifacts already exist; no retry or overwrite.')
    ledger=raw_root/'h1-local-ledger.jsonl'
    if ledger_count(ledger)!=prep['local_ledger_before'] or C.sha(ledger)!=prep['local_ledger_digest_before']:
        raise ValueError('Ledger changed after preparation.')
    if C.sha(raw_root/'api-ledger.jsonl')!=prep['api_ledger_digest_before']:raise ValueError('Paid ledger changed.')
    reader=Reader(prep['reader_config'],output,ledger)
    source={'git_head':C.git('rev-parse','HEAD'),'clean_tree':True,
        'digests':{p.relative_to(ROOT).as_posix():C.sha(p) for p in [Path(__file__),DATA/'PLAN.md',DATA/'preparation.json',Path(C.__file__),Path(C.P.__file__)]}}
    C.write(output/'manifest.json',{'source':source,'config':reader.cfg,'preparation':prep})
    try:
        C.write(output/'preflight.json',reader.preflight());C.V5.S.controls(reader,'local14b',output)
        for p in C.P.read_rows(output/'packets.jsonl'):
            raw=reader.ask(p['call_key'],p['messages'],7,output_schema=C.SCHEMA)
            C.P.append(output/'answers.jsonl',{k:p[k] for k in ['split','id','query_id','arm','call_key','shown_ids']}|{'answer':C.parse(raw['text'])})
        finish=reader.finish()
        if len(C.P.read_rows(ledger))!=prep['local_ledger_before']+CALLS:raise ValueError('Actual count mismatch.')
        if C.sha(raw_root/'api-ledger.jsonl')!=prep['api_ledger_digest_before']:raise ValueError('Unexpected paid call.')
        C.write(output/'finished.json',finish|{'local_ledger_after':len(C.P.read_rows(ledger)),
            'local_ledger_digest_after':C.sha(ledger),'api_ledger_unchanged':True})
    finally:reader.release()
    C.write(output/'raw-freeze.json',{'files_sha256':{p.name:C.sha(p) for p in sorted(output.iterdir()) if p.is_file()},'source':source})
    print('Complete density outputs frozen before scoring.',flush=True)


def score(raw_root,output,freeze_commit,destination):
    raw=(output/'raw-freeze.json').read_bytes()
    committed=subprocess.check_output(['git','show',freeze_commit+':data/lab/h1-evidence-density-v1/raw-freeze.json'],cwd=ROOT)
    if raw!=committed:raise ValueError('Committed freeze differs.')
    freeze=json.loads(raw)
    if any(C.sha(output/name)!=h for name,h in freeze['files_sha256'].items()):raise ValueError('Raw artifact drift.')
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    gold={}
    for split in ['dev','valid']:
        p=ROOT/'data/lab/corpus-h1'/('reveal-v0/gold.jsonl' if split=='dev' else 'valid-b/reveal/gold.jsonl')
        if C.sha(p)!=prep['input_digests'][split+'/gold']:raise ValueError('Gold hash changed.')
        gold[split]={r['query_id']:r for r in C.P.read_rows(p)}
    packets=C.P.read_rows(output/'packets.jsonl');answers=C.P.read_rows(output/'answers.jsonl')
    attempts=C.P.read_rows(output/'attempts.jsonl');responses=C.P.read_rows(output/'responses.jsonl')
    req={r['key']:r for r in attempts};res={r['key']:r for r in responses};saved={r['call_key']:r for r in answers}
    if len(packets)!=144 or len(answers)!=144 or len(saved)!=144 or len(attempts)!=CALLS or len(responses)!=CALLS or set(req)!=set(res):
        raise ValueError('Incomplete call matrix.')
    controls=C.P.read_rows(output/'controls.jsonl')
    if len(controls)!=3 or not all(r['correct'] for r in controls):raise ValueError('Transport controls failed.')
    records=[];parse_failures=0
    for p in packets:
        key=p['call_key'];request=req[key]['request'];actual=C.parse(res[key]['text']);answer=saved[key]
        if request['messages']!=p['messages'] or C.P.sha(request)!=req[key]['request_sha256'] or request['format']!=C.SCHEMA or answer['answer']!=actual:
            raise ValueError('Saved/actual packet or answer mismatch.')
        parse_failures+=actual is None;result=C.scorer.score(actual or '',gold[p['split']][p['query_id']])
        records.append({k:p[k] for k in ['split','id','arm']}|{k:result[k] for k in ['answered','leaked','abstained']}|
            {'clean_answered':int(result['answered'] and not result['leaked'])})
    summary={a:{'n':len(rs),'answered':sum(r['answered'] for r in rs),'leaked':sum(r['leaked'] for r in rs)} for a in ARMS if (rs:=[r for r in records if r['arm']==a])}
    result={'summary':summary,'records':records,'parse_failures':parse_failures,'actual_local_calls':CALLS,
        'new_api_calls':0,'oracle_id_diagnostic':True,'local_cap':CAP,
        'claim':'Exploratory fixed-seed repetition contrast; no general memory/semantic confirmation.'}
    C.write(destination,result);print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ['prepare','run','score']:
        p=sub.add_parser(name);p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
        if name=='prepare':p.add_argument('--source-controls',type=Path,required=True)
        if name=='score':p.add_argument('--freeze-commit',required=True);p.add_argument('--destination',type=Path,required=True)
    args=vars(parser.parse_args());globals()[args.pop('command')](**args)
