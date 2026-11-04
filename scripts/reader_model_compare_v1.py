"""Frozen v1 matched comparison: Qwen 14B and V4.1 Flash, with independent record audit.

No writer regeneration, Pro, live-agent changes, automatic retry or production changes. API credentials never enter a recorded request or config.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess

import flash_reader_client_v1 as F
import nie_reader_pilot as P
import nie_memory_contract as C

ROOT=P.ROOT
DATA=ROOT/'data/lab/reader-model-compare-v1'
REFERENCE=P.DATA/'run-002'


def settings():
    return json.loads((DATA/'config.json').read_text(encoding='utf-8'))


def source_identity():
    files=[Path(__file__),ROOT/'scripts/audit_reader_model_compare_v1.py',Path(F.__file__),Path(P.__file__),Path(P.bridge.__file__),Path(C.__file__),P.bridge.KERNEL,
           DATA/'PLAN.md',DATA/'config.json',ROOT/'docs/00-project/reader-model-usage-policy-2026-11-04.md',
           P.DATA/'cases.json',REFERENCE/'manifest.json',REFERENCE/'writers.jsonl',REFERENCE/'journals.jsonl']
    return {'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'clean_tree':not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
            'sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}


def reference():
    manifest=json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    cases=json.loads((P.DATA/'cases.json').read_text(encoding='utf-8'))
    writers=P.read_rows(REFERENCE/'writers.jsonl')
    if len(writers)!=16 or any(not w['valid'] for w in writers):raise ValueError('The fixed valid writer cohort is required.')
    expected={(c['slot'],s) for c in cases for s in manifest['config']['writer_seeds']}
    if {(w['slot'],w['seed']) for w in writers}!=expected:raise ValueError('Writer-cohort identity mismatch.')
    return manifest['config'],cases,{(w['slot'],w['seed']):w['value'] for w in writers}


def local_config(config):
    old=json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))['config']
    return dict(old,model=config['local_model'],model_digest=config['local_digest'],max_calls=config['max_calls'],
                max_seconds=config['max_seconds'],options={'temperature':0,'num_ctx':4096,'num_predict':64})


def client_for(backend,config,output,ledger,phase):
    if backend=='flash':return F.FlashReader(config,output,ledger,phase)
    if backend=='local14b':return P.LocalReader(local_config(config),output)
    raise ValueError('Only local14b and approved flash backends exist.')


def summarize(output,gold,completed):
    turns=P.read_rows(output/'turns.jsonl');controls=P.read_rows(output/'controls.jsonl')
    attempts=P.read_rows(output/'attempts.jsonl');responses=P.read_rows(output/'responses.jsonl')
    expected={f'read:{slot}:{seed}:{arm}:{t}' for slot,seed in gold for arm in ['N','K','O','V'] for t in range(3)}
    expected_controls={f'positive-{i}' for i in range(3)}|{'no-record','future-only','conflict','canary-0','canary-1'}
    all_keys=expected|expected_controls
    key_lists=[[r['key'] for r in source] for source in (attempts,responses)]
    complete=(completed and all(set(keys)==all_keys and len(keys)==len(all_keys) for keys in key_lists)
              and len(turns)==len(expected) and {r['key'] for r in turns}==expected
              and len(controls)==8 and {r['key'] for r in controls}==expected_controls
              and all(r['request_sha256']==P.sha(r['request']) for r in attempts))
    by_key={r['key']:r for r in responses};arms={}
    for arm in ['N','K','O','V']:
        rows=[r for r in turns if r['arm']==arm]
        scored=[]
        for r in rows:
            raw=P.answer_value(by_key[r['key']]) if r['key'] in by_key else None
            if raw!=r['raw_value']:complete=False
            actual=gold[(r['slot'],r['seed'])]
            scored.append(dict(r,raw_agreement=P.agreement(raw,actual),delivered_agreement=P.agreement(r['delivered_value'],actual)))
        per_turn={str(t):{'n':sum(r['turn']==t for r in scored),
            'retrieved':sum(r['turn']==t and r['retrieved'] for r in scored),
            'raw_agreement':sum(r['turn']==t and r['raw_agreement'] for r in scored),
            'delivered_agreement':sum(r['turn']==t and r['delivered_agreement'] for r in scored)} for t in range(3)}
        chains=sum(all(any(r['slot']==slot and r['seed']==seed and r['turn']==t and r['delivered_agreement'] for r in scored)
                       for t in range(3)) for slot,seed in gold)
        unknown=sum(isinstance(r['raw_value'],str) and C.folded(r['raw_value'])=='unknown' for r in scored)
        malformed=sum(r['raw_value'] is None for r in scored)
        raw_ok=sum(r['raw_agreement'] for r in scored)
        arms[arm]={'n_turns':len(scored),'retrieved':sum(r['retrieved'] for r in scored),'raw_agreement':raw_ok,
                   'delivered_agreement':sum(r['delivered_agreement'] for r in scored),
                   'all_three_chain_agreement':chains,'raw_unknown':unknown,'malformed_raw':malformed,
                   'raw_wrong_value':len(scored)-raw_ok-unknown-malformed,
                   'guard_resolutions':dict(Counter(r['resolution'] for r in scored)),'per_turn':per_turn}
    return {'complete':complete,'generation_calls':len(attempts),'arms':arms,'controls':controls,
            'scope':'Fixed 7B-writer cohort, eight authored slots, supplied routing; no production or independent-population claim.'}


def run(output,backend,ledger,*,factory=None,require_clean=True):
    cfg=settings();F.permitted(cfg)
    source=source_identity()
    if require_clean and not source['clean_tree']:raise ValueError('Commit source before calls.')
    output.mkdir(parents=True,exist_ok=False)
    cohort,cases,gold=reference()
    P.write(output/'manifest.json',{'execution':source,'backend':backend,'config':cfg,'cohort_config':cohort,
                                  'started_at':datetime.now(timezone.utc).isoformat()})
    client=factory(cfg,output) if factory else client_for(backend,cfg,output,ledger,'benchmark')
    completed=False
    try:
        P.write(output/'environment.json',client.preflight())
        positives=[]
        for i,token in enumerate(cohort['positive_controls']):
            messages=P.reader_messages(cohort,'control_value','What is the control_value?',{'context':f'The control_value is {token}.'},[])
            response=client.ask(f'positive-{i}',messages,7)
            passed=P.answer_value(response)==token
            P.append(output/'controls.jsonl',{'key':f'positive-{i}','passed':passed,'raw':response['text']})
            positives.append(messages)
            if not passed:raise RuntimeError('Positive control failed; retain partial result without retry.')
        case=cases[0]
        conflicting=[P.journal_row(case,case['values'][i],f'conflict-{i}') for i in range(2)]
        conflicting += [P.journal_row(c,c['values'][0],'distractor:'+c['slot']) for c in cases[1:]]
        for name,rows in [('no-record',[]),('future-only',[P.journal_row(case,case['values'][0],'future','2026-11-05T00:00:00Z',True)]),('conflict',conflicting)]:
            replay=P.retrieve(cohort,case,case['direct'],rows,'V','unused')
            guard=C.guard_answer(case['slot'],'{}',replay['shown_items'])
            if name=='conflict' and guard['resolution']!='conflicting_evidence':raise RuntimeError('Unexercised conflict control.')
            response=client.ask(name,P.reader_messages(cohort,case['slot'],case['direct'],replay,[]),7)
            emitted=C.guard_answer(case['slot'],response['text'],replay['shown_items'])
            P.append(output/'controls.jsonl',{'key':name,'passed':emitted['value']=='UNKNOWN','raw':response['text'],'guard':emitted})
        for ci,case in enumerate(cases):
            for seed in cohort['writer_seeds']:
                value=gold[(case['slot'],seed)];foil=case['values'][(case['values'].index(value)+1)%8]
                for arm in ['N','K','O','V']:
                    history=[]
                    for turn,question in enumerate((case['direct'],case['paraphrase'],case['pressure'].format(foil=foil))):
                        if turn==1:history=[]
                        rows=P.load_journal(REFERENCE,case['slot'],seed)
                        replay=P.retrieve(cohort,case,question,rows,arm,f'detail:{case["slot"]}:{seed}')
                        messages=P.reader_messages(cohort,case['slot'],question,replay,history)
                        key=f'read:{case["slot"]}:{seed}:{arm}:{turn}'
                        response=client.ask(key,messages,seed+ci*100+turn)
                        raw=P.answer_value(response)
                        guard=C.guard_answer(case['slot'],response['text'] if response.get('done_reason')!='length' else '',replay['shown_items']) if arm=='V' else None
                        delivered=guard['value'] if guard else raw
                        emitted=json.dumps({'value':delivered}) if guard else response['text']
                        P.append(output/'turns.jsonl',{'key':key,'slot':case['slot'],'seed':seed,'arm':arm,'turn':turn,
                            'question':question,'raw_value':raw,'delivered_value':delivered,
                            'retrieved':any(i['meta']['publication_id']==f'detail:{case["slot"]}:{seed}' for i in replay['shown_items']),
                            'resolution':guard['resolution'] if guard else 'unguarded','guard':guard,'replay':replay})
                        history += [messages[-1],{'role':'assistant','content':emitted}]
        first=P.read_rows(output/'controls.jsonl')[0]['raw']
        for i in range(2):
            response=client.ask(f'canary-{i}',positives[0],7)
            P.append(output/'controls.jsonl',{'key':f'canary-{i}','passed':P.answer_value(response)==cohort['positive_controls'][0],
                'byte_identical_to_first':response['text']==first,'raw':response['text']})
        P.write(output/'completion.json',client.finish())
        if source_identity()['sha256']!=source['sha256']:raise RuntimeError('Source changed during execution.')
        completed=True
    except Exception as exc:
        P.write(output/'failure.json',{'type':type(exc).__name__,'http_status':getattr(exc,'code',None),
                                    'message':'Phase stopped without retry; inspect local state and retained reservations.'})
    finally:client.release()
    summary=summarize(output,gold,completed);P.write(output/'summary.json',summary)
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--backend',choices=['local14b','flash'],required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--ledger',type=Path,required=True)
    args=ap.parse_args(argv)
    result=run(args.output,args.backend,args.ledger)
    print(json.dumps({'complete':result['complete'],'generation_calls':result['generation_calls']}))
    return 0 if result['complete'] else 1



if __name__=='__main__':raise SystemExit(main())
