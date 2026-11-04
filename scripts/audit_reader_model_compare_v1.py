"""No-model audit: reconstruct inputs, evidence, guard and scores from raw records."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import reader_model_compare_v1 as R

P,C=R.P,R.C


def audit(output):
    manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    cfg=manifest['config'];backend=manifest['backend'];cohort,cases,gold=R.reference()
    errors=[];checked=0
    def check(ok,label):
        if not ok:errors.append(label)
    for path,digest in manifest['execution']['sha256'].items():
        check(hashlib.sha256((R.ROOT/path).read_bytes()).hexdigest()==digest,'source:'+path)
    check(manifest['cohort_config']==cohort,'cohort config')
    attempts=P.read_rows(output/'attempts.jsonl');responses=P.read_rows(output/'responses.jsonl')
    turns=P.read_rows(output/'turns.jsonl');controls=P.read_rows(output/'controls.jsonl')
    indexed=[]
    for name,rows in [('attempt',attempts),('response',responses),('turn',turns),('control',controls)]:
        check(len(rows)==len({r['key'] for r in rows}),'duplicate '+name)
        indexed.append({r['key']:r for r in rows})
    requests,answers,stored_turns,stored_controls=indexed
    expected=set();scores={a:[] for a in ['N','K','O','V']}
    def request(key,messages,seed):
        nonlocal checked
        expected.add(key);checked+=1
        attempt=requests.get(key,{});response=answers.get(key,{})
        body={'model':cfg['api_model'],'messages':messages,'stream':False,'temperature':0,'max_tokens':64,
              'thinking':{'type':'disabled'},'response_format':{'type':'json_object'}} if backend=='flash' else {
              'model':cfg['local_model'],'messages':messages,'stream':False,'format':'json','keep_alive':'5m',
              'options':dict(R.local_config(cfg)['options'],seed=seed)}
        check(attempt.get('request')==body,'request:'+key)
        check(attempt.get('request_sha256')==P.sha(body),'request hash:'+key)
        if backend=='flash':
            check(attempt.get('controller_seed_not_sent')==seed,'seed:'+key)
            check(response.get('returned_model')=='deepseek-flash' or bool(R.F.re.fullmatch(
                r'deepseek-v4\.1-flash(?:-\d+)?',str(response.get('returned_model','')).lower())),'model:'+key)
        check(isinstance(response.get('text'),str),'response:'+key)
        return response
    positive_messages=[]
    for i,token in enumerate(cohort['positive_controls']):
        messages=P.reader_messages(cohort,'control_value','What is the control_value?',{'context':f'The control_value is {token}.'},[])
        positive_messages.append(messages);key=f'positive-{i}';raw=request(key,messages,7)
        check(P.answer_value(raw)==token,'positive failed:'+key)
        check(stored_controls.get(key)=={'key':key,'passed':True,'raw':raw.get('text')},'control:'+key)
    case=cases[0]
    conflict=[P.journal_row(case,case['values'][i],f'conflict-{i}') for i in range(2)]
    conflict += [P.journal_row(c,c['values'][0],'distractor:'+c['slot']) for c in cases[1:]]
    for key,rows in [('no-record',[]),('future-only',[P.journal_row(case,case['values'][0],'future','2026-11-05T00:00:00Z',True)]),('conflict',conflict)]:
        replay=P.retrieve(cohort,case,case['direct'],rows,'V','unused')
        raw=request(key,P.reader_messages(cohort,case['slot'],case['direct'],replay,[]),7)
        guard=C.guard_answer(case['slot'],raw.get('text'),replay['shown_items'])
        check(guard['resolution']==('conflicting_evidence' if key=='conflict' else 'no_evidence'),'control coverage:'+key)
        check(stored_controls.get(key)=={'key':key,'passed':True,'raw':raw.get('text'),'guard':guard},'control:'+key)
    for ci,case in enumerate(cases):
        for seed in cohort['writer_seeds']:
            value=gold[(case['slot'],seed)];foil=case['values'][(case['values'].index(value)+1)%8]
            for arm in scores:
                history=[]
                for turn,question in enumerate((case['direct'],case['paraphrase'],case['pressure'].format(foil=foil))):
                    if turn==1:history=[]
                    replay=P.retrieve(cohort,case,question,P.load_journal(R.REFERENCE,case['slot'],seed),arm,f'detail:{case["slot"]}:{seed}')
                    messages=P.reader_messages(cohort,case['slot'],question,replay,history)
                    key=f'read:{case["slot"]}:{seed}:{arm}:{turn}'
                    raw=request(key,messages,seed+ci*100+turn);answer=P.answer_value(raw)
                    guard=C.guard_answer(case['slot'],raw.get('text') if raw.get('done_reason')!='length' else '',replay['shown_items']) if arm=='V' else None
                    delivered=guard['value'] if guard else answer
                    reconstructed={'key':key,'slot':case['slot'],'seed':seed,'arm':arm,'turn':turn,'question':question,
                        'raw_value':answer,'delivered_value':delivered,'guard':guard,'replay':replay,
                        'retrieved':any(i['meta']['publication_id']==f'detail:{case["slot"]}:{seed}' for i in replay['shown_items']),
                        'resolution':guard['resolution'] if guard else 'unguarded'}
                    check(stored_turns.get(key)==json.loads(json.dumps(reconstructed)),'turn:'+key)
                    scores[arm].append(dict(reconstructed,raw_ok=P.agreement(answer,value),ok=P.agreement(delivered,value)))
                    history += [messages[-1],{'role':'assistant','content':json.dumps({'value':delivered}) if guard else raw.get('text')}]
    for i in range(2):
        key=f'canary-{i}';raw=request(key,positive_messages[0],7)
        check(P.answer_value(raw)==cohort['positive_controls'][0],'canary failed:'+key)
        check(stored_controls.get(key)=={'key':key,'passed':True,'raw':raw.get('text'),
              'byte_identical_to_first':raw.get('text')==answers['positive-0']['text']},'control:'+key)
    check(set(requests)==expected and set(answers)==expected,'call coverage')
    check(set(stored_turns)=={k for k in expected if k.startswith('read:')},'turn coverage')
    check(set(stored_controls)=={k for k in expected if not k.startswith('read:')},'control coverage')
    summary=json.loads((output/'summary.json').read_text(encoding='utf-8'))
    check(summary.get('complete') is True and summary.get('generation_calls')==200,'completion')
    for arm,rows in scores.items():
        actual=summary['arms'][arm]
        unknown=sum(isinstance(r['raw_value'],str) and C.folded(r['raw_value'])=='unknown' for r in rows)
        malformed=sum(r['raw_value'] is None for r in rows);raw_ok=sum(r['raw_ok'] for r in rows)
        expected_metrics={'n_turns':len(rows),'raw_agreement':raw_ok,'delivered_agreement':sum(r['ok'] for r in rows),
            'retrieved':sum(r['retrieved'] for r in rows),'raw_unknown':unknown,'malformed_raw':malformed,
            'raw_wrong_value':len(rows)-raw_ok-unknown-malformed,
            'guard_resolutions':dict(Counter(r['resolution'] for r in rows)),
            'all_three_chain_agreement':sum(all(any(r['slot']==slot and r['seed']==seed and r['turn']==t and r['ok'] for r in rows) for t in range(3)) for slot,seed in gold),
            'per_turn':{str(t):{'n':sum(r['turn']==t for r in rows),'retrieved':sum(r['turn']==t and r['retrieved'] for r in rows),
                'raw_agreement':sum(r['turn']==t and r['raw_ok'] for r in rows),'delivered_agreement':sum(r['turn']==t and r['ok'] for r in rows)} for t in range(3)}}
        check(actual==expected_metrics,'metrics:'+arm)
    return {'passed':not errors,'errors':errors,'requests_reconstructed':checked,'primary_turns_reconstructed':192,
            'method':'No LLM judge: reconstruct persisted inputs, history, shown evidence, guard and all counts from final raw answers.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('output',type=Path);args=ap.parse_args()
    result=audit(args.output);print(json.dumps(result,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
