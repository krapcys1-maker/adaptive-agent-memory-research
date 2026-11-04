"""Bounded local reader pilot for the NIE journal bridge; synthetic data only.

Does not use paid APIs, download models, modify NIE, resume a partial run or
establish production readiness. It records final content, never thinking fields.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import urllib.error
import urllib.request

import nie_memory_contract as contract
import nie_persona_replay as bridge

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/lab/nie-local-reader-v1'
PROTOCOL = ROOT / 'docs/00-project/nie-local-reader-pilot-2026-11-04.md'


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def append(path, value):
    with path.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False)+'\n')
        stream.flush()


def source_identity():
    files = [Path(__file__), Path(bridge.__file__), Path(contract.__file__), bridge.KERNEL,
             DATA/'config.json', DATA/'cases.json', PROTOCOL]
    return {'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'clean_tree': not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),
            'sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}


def validate(config, cases):
    if config['base_url'] != 'http://127.0.0.1:11434':
        raise ValueError('Only the fixed local Ollama endpoint is permitted.')
    if config['arms'] != ['N','K','O','V'] or config['writer_seeds'] != [17,43]:
        raise ValueError('Execution must use the committed arm/seed design.')
    if not (0 < config['max_calls'] <= 220 and 0 < config['max_seconds'] <= 1200):
        raise ValueError('Resource cap exceeds the fixed pilot ceiling.')
    if len(cases) != 8 or len({c['slot'] for c in cases}) != 8:
        raise ValueError('Eight distinct committed slots are required.')
    for case in cases:
        if not contract.SLOT.fullmatch(case['slot']) or len(case['values']) != 8 or len(set(case['values'])) != 8:
            raise ValueError('Invalid slot/value pool.')
        if any(contract.folded(v) in contract.folded(case['cue']) for v in case['values']):
            raise ValueError('Routing cue must not contain a value-pool answer.')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Local pilot refuses HTTP redirects.')


class LocalReader:
    def __init__(self, config, output, request=None):
        self.cfg, self.output = config, output
        self.started = time.monotonic()
        self.keys = set()
        self.responses = []
        self.owns_model = False
        self.request = request or self.http
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def http(self, path, body=None):
        request = urllib.request.Request(self.cfg['base_url']+path,
            data=None if body is None else json.dumps(body).encode(),
            headers={'Content-Type':'application/json'})
        timeout=self.cfg['http_timeout_seconds']
        if path=='/api/chat':
            timeout=min(timeout,self.cfg['max_seconds']-(time.monotonic()-self.started))
            if timeout<=0:
                raise RuntimeError('Generation deadline reached.')
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)

    def preflight(self):
        if self.request('/api/ps').get('models'):
            raise RuntimeError('A model is already loaded; do not interfere with another GPU task.')
        version = self.request('/api/version')
        tags = self.request('/api/tags').get('models',[])
        found = [m for m in tags if m.get('name') == self.cfg['model']]
        if len(found) != 1 or found[0].get('digest') != self.cfg['model_digest']:
            raise ValueError('Installed model digest differs; no pull or fallback is permitted.')
        show = self.request('/api/show', {'model': self.cfg['model']})
        gpu=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total,memory.used',
                            '--format=csv,noheader'],capture_output=True,text=True,timeout=10)
        return {'service':version, 'model':found[0], 'details':show.get('details'),
                'template_sha256':hashlib.sha256(show.get('template','').encode()).hexdigest(),
                'model_system_sha256':hashlib.sha256(show.get('system','').encode()).hexdigest(),
                'parameters':show.get('parameters'), 'python':platform.python_version(),
                'platform':platform.platform(),'gpu':gpu.stdout.strip() if gpu.returncode==0 else None}

    def ask(self, key, messages, seed):
        if key in self.keys:
            raise ValueError('Duplicate call key; no mixing or retry.')
        if len(self.keys) >= self.cfg['max_calls'] or time.monotonic()-self.started >= self.cfg['max_seconds']:
            raise RuntimeError('Local call/time cap reached.')
        payload = {'model':self.cfg['model'], 'messages':messages, 'stream':False, 'format':'json',
                   'keep_alive':'5m', 'options':dict(self.cfg['options'],seed=seed)}
        self.keys.add(key)
        append(self.output/'attempts.jsonl', {'key':key,'request_sha256':sha(payload),'request':payload})
        self.owns_model = True
        start = time.monotonic()
        response = self.request('/api/chat',payload)
        if response.get('error') or response.get('done') is not True or response.get('model') != self.cfg['model']:
            raise RuntimeError('Incomplete or unexpected model response; run stops without retry.')
        text = response.get('message',{}).get('content')
        if not isinstance(text,str):
            raise ValueError('Response has no final message content.')
        row = {'key':key, 'text':text, 'wall_seconds':time.monotonic()-start,
               'done_reason':response.get('done_reason'),
               'usage':{k:response.get(k) for k in ('prompt_eval_count','eval_count','total_duration',
                        'load_duration','prompt_eval_duration','eval_duration')}}
        self.responses.append(row)
        append(self.output/'responses.jsonl',row)
        print(f'{len(self.keys):03d} {key}',flush=True)
        return row

    def finish(self):
        tags = self.request('/api/tags').get('models',[])
        found = [m for m in tags if m.get('name') == self.cfg['model']]
        unchanged = len(found)==1 and found[0].get('digest')==self.cfg['model_digest']
        if not unchanged:
            raise RuntimeError('Model changed during execution.')
        return {'model_digest_unchanged':True,'elapsed_seconds':time.monotonic()-self.started,
                'generation_calls':len(self.keys), 'service':self.request('/api/version')}

    def release(self):
        if self.owns_model:
            result = self.request('/api/generate',{'model':self.cfg['model'],'keep_alive':0})
            write(self.output/'release.json',{'model':result.get('model'),'done':result.get('done'),
                                            'done_reason':result.get('done_reason')})


def journal_row(case, value, identity, stamp='2026-11-01T12:00:00Z', future=False):
    statement = case['statement'].format(value=value)
    return {'kiedy':stamp,'run_id':identity,'typ_zadania':'notka_zycie','zasiew':'local-pilot',
            'id_notki':identity,'tekst':('In 2019, '+statement if future else statement),
            'zrodlo':'improwizacja','supersedes':None,'wersja':'typed-pilot-v1',
            'typed_claim':{'slot':case['slot'],'value':value}}


def encoded(rows):
    return ('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n').encode()


def retrieve(config, case, question, rows, arm, identity):
    if arm == 'N':
        return {'context':'','shown_items':[],'kernel_ranked_ids':[]}
    if arm == 'O':
        rows = [r for r in rows if r['id_notki'] == identity]
        cue = case['cue']
        profile = {'name':'oracle-single-note','names':False,'lex_tau':1e-9,'min_evidence':0.0}
    else:
        cue = question + ('\n'+case['cue'] if arm == 'V' else '')
        profile = None
    return bridge.replay(encoded(rows),cue,config['as_of'],max_context_words=config['max_context_words'],profile=profile)


def reader_messages(config, slot, question, replay, history):
    system = config['reader_system']+'\nREQUESTED FIELD: '+slot+'\nRECORDED MEMORY:\n'+(replay['context'] or '(none)')
    user = f'A reader asks: {question}\nReturn only {{"value":"..."}}.'
    return [{'role':'system','content':system},*history,{'role':'user','content':user}]


def answer_value(response):
    return None if response.get('done_reason') == 'length' else contract.parse_value(response['text'])


def agreement(value, expected):
    return value is not None and contract.folded(value)==contract.folded(expected)


def read_rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()] if path.exists() else []


def summarize(config, cases, output, completed):
    writers, turns, controls = [read_rows(output/name) for name in ('writers.jsonl','turns.jsonl','controls.jsonl')]
    writer_keys = {(c['slot'],seed) for c in cases for seed in config['writer_seeds']}
    actual_writers = {(r['slot'],r['seed']) for r in writers}
    valid = {(r['slot'],r['seed']):r['value'] for r in writers if r['valid']}
    required_turns = {(slot,seed,arm,t) for slot,seed in valid for arm in config['arms'] for t in range(3)}
    turn_keys = [(r['slot'],r['seed'],r['arm'],r['turn']) for r in turns]
    expected_controls = {f'positive-{i}' for i in range(3)}|{'no-record','future-only','conflict','canary-0','canary-1'}
    attempts,responses=[read_rows(output/name) for name in ('attempts.jsonl','responses.jsonl')]
    expected_calls={r['call_key'] for r in writers}|{r['call_key'] for r in turns}|expected_controls
    attempt_keys=[r['key'] for r in attempts]
    response_keys=[r['key'] for r in responses]
    ledger_ok=(set(attempt_keys)==expected_calls==set(response_keys)
               and len(attempt_keys)==len(set(attempt_keys)) and len(response_keys)==len(set(response_keys))
               and all(r['request_sha256']==sha(r['request']) for r in attempts))
    response_by_key={r['key']:r for r in responses}
    pools={c['slot']:c['values'] for c in cases}
    for writer in writers:
        source=response_by_key.get(writer['call_key'])
        actual=answer_value(source) if source else None
        if writer['value']!=actual or writer['valid']!=(actual in pools.get(writer['slot'],[])):
            ledger_ok=False
    controls=[dict(r) for r in controls]
    for r in controls:
        if r['key'].startswith('positive-'):
            index=int(r['key'].split('-')[1])
            source=response_by_key.get(r['key'])
            r['passed']=source is not None and answer_value(source)==config['positive_controls'][index]
    # Derive scores from recorded outputs and accepted writer values, not saved success flags.
    verified_turns=[]
    for record in turns:
        r=dict(record)
        source=response_by_key.get(r['call_key'])
        raw=answer_value(source) if source else None
        if r['raw_value']!=raw:
            ledger_ok=False
        expected=valid.get((r['slot'],r['seed']))
        r['raw_agreement']=expected is not None and agreement(raw,expected)
        r['delivered_agreement']=expected is not None and agreement(r['delivered_value'],expected)
        verified_turns.append(r)
    turns=verified_turns
    complete = (completed and actual_writers==writer_keys and len(writers)==len(writer_keys)
                and set(turn_keys)==required_turns and len(turn_keys)==len(required_turns)
                and {r['key'] for r in controls}==expected_controls and len(controls)==8 and ledger_ok)
    arms = {}
    for arm in config['arms']:
        rows = [r for r in turns if r['arm']==arm]
        per_turn = {}
        for t in range(3):
            part=[r for r in rows if r['turn']==t]
            per_turn[str(t)]={'n':len(part),'retrieved':sum(r['retrieved'] for r in part),
                             'raw_agreement':sum(r['raw_agreement'] for r in part),
                             'delivered_agreement':sum(r['delivered_agreement'] for r in part)}
        good_chains = sum(all(any(r['slot']==slot and r['seed']==seed and r['turn']==t and r['delivered_agreement']
                                  for r in rows) for t in range(3)) for slot,seed in writer_keys)
        arms[arm]={'n_turns':len(rows),'raw_agreement':sum(r['raw_agreement'] for r in rows),
                   'delivered_agreement':sum(r['delivered_agreement'] for r in rows),
                   'retrieved':sum(r['retrieved'] for r in rows),'all_three_chain_agreement':good_chains,
                   'planned_chains':len(writer_keys),'per_turn':per_turn,
                   'guard_resolutions':dict(Counter(r['resolution'] for r in rows)),
                   'raw_unknown':sum(isinstance(r['raw_value'],str) and contract.folded(r['raw_value'])=='unknown' for r in rows),
                   'delivered_unknown':sum(isinstance(r['delivered_value'],str) and contract.folded(r['delivered_value'])=='unknown' for r in rows),
                   'malformed_raw':sum(r['raw_value'] is None for r in rows)}
        arms[arm]['per_seed']={str(seed):{'n_turns':sum(r['seed']==seed for r in rows),
            'delivered_agreement':sum(r['seed']==seed and r['delivered_agreement'] for r in rows),
            'all_three_chain_agreement':sum(all(any(r['slot']==slot and r['seed']==seed and r['turn']==t and r['delivered_agreement'] for r in rows)
                                                 for t in range(3)) for slot in [c['slot'] for c in cases])}
                                  for seed in config['writer_seeds']}
    positive = [r for r in controls if r['key'].startswith('positive-')]
    safe = [r for r in controls if r['key'] in ('no-record','future-only','conflict')]
    readiness = None
    if complete:
        v=arms['V']
        readiness=(v['all_three_chain_agreement']>=15 and v['retrieved']>=.9*v['n_turns']
                   and len(positive)==3 and all(r['passed'] for r in positive)
                   and len(safe)==3 and all(r['passed'] for r in safe))
    return {'complete':complete,'ledger_integrity':ledger_ok,'generation_calls':len(attempt_keys),
            'writer_chains':len(writers),'valid_writer_chains':len(valid),
            'write_failures':sum(not r['valid'] for r in writers),'arms':arms,'controls':controls,
            'larger_offline_test_only':readiness,
            'additional_V_benefit_over_K':None if not complete else arms['V']['all_three_chain_agreement']>arms['K']['all_three_chain_agreement'],
            'scope':'Local quantized reader, authored closed slots and supplied routing; no production/P2 replication claim.'}


def execute(output, config, cases, *, client_factory=LocalReader, require_clean=True):
    validate(config,cases)
    identity=source_identity()
    if require_clean and not identity['clean_tree']:
        raise ValueError('Commit the execution source before any generation call.')
    output.mkdir(parents=True,exist_ok=False)
    manifest={'execution':identity,'config':config,'cases_sha256':sha(cases),
              'started_at':datetime.now(timezone.utc).isoformat(),'status':'execution-start'}
    write(output/'manifest.json',manifest)
    client=client_factory(config,output)
    completed=False
    failure=None
    try:
        write(output/'local-environment.json',client.preflight())
        # Simple reader/format controls, independent of case answers.
        positive_messages=[]
        for i,token in enumerate(config['positive_controls']):
            messages=reader_messages(config,'control_value','What is the control_value?',
                                      {'context':f'The control_value is {token}.'},[])
            response=client.ask(f'positive-{i}',messages,7)
            ok=answer_value(response)==token
            append(output/'controls.jsonl',{'key':f'positive-{i}','passed':ok,'raw':response['text']})
            positive_messages.append(messages)
            if not ok:
                raise RuntimeError('Positive reader/format control failed; no main-chain conclusions.')
        case=cases[0]
        for label,rows in [('no-record',[]),
            ('future-only',[journal_row(case,case['values'][0],'future','2026-11-05T00:00:00Z',True)]),
            ('conflict',[journal_row(case,case['values'][0],'left'),journal_row(case,case['values'][1],'right')])]:
            replay=retrieve(config,case,case['direct'],rows,'V','unused')
            response=client.ask(label,reader_messages(config,case['slot'],case['direct'],replay,[]),7)
            guarded=contract.guard_answer(case['slot'],response['text'],replay['shown_items'])
            append(output/'controls.jsonl',{'key':label,'passed':guarded['value']=='UNKNOWN',
                  'raw':response['text'],'guard':guarded,'retrieved_ids':[i['id'] for i in replay['shown_items']]})
        for ci,case in enumerate(cases):
            for seed in config['writer_seeds']:
                chain=f"{case['slot']}:{seed}"
                response=client.ask('write:'+chain,[{'role':'system','content':config['writer_system']},
                    {'role':'user','content':f"Field: {case['slot']}. Choose exactly one pool member: "+json.dumps(case['values'])}],seed)
                value=answer_value(response)
                valid=value in case['values']
                append(output/'writers.jsonl',{'slot':case['slot'],'seed':seed,'value':value,'valid':valid,'call_key':'write:'+chain})
                if not valid:
                    continue
                identity_key='detail:'+chain
                target=journal_row(case,value,identity_key)
                rows=[target]+[journal_row(other,other['values'][0],f'distractor:{other["slot"]}:{chain}')
                               for other in cases if other['slot']!=case['slot']]
                foil=case['values'][(case['values'].index(value)+1)%len(case['values'])]
                rows.append(journal_row(case,foil,'future:'+chain,'2026-11-05T00:00:00Z',True))
                append(output/'journals.jsonl',{'slot':case['slot'],'seed':seed,'rows':rows})
                for arm in config['arms']:
                    history=[]
                    for turn,question in enumerate((case['direct'],case['paraphrase'],case['pressure'].format(foil=foil))):
                        if turn==1:
                            history=[]  # New session: the direct answer must not leak through working memory.
                        replay=retrieve(config,case,question,rows,arm,identity_key)
                        messages=reader_messages(config,case['slot'],question,replay,history)
                        key=f'read:{chain}:{arm}:{turn}'
                        response=client.ask(key,messages,seed+ci*100+turn)
                        raw=answer_value(response)
                        candidate=response['text'] if response.get('done_reason')!='length' else ''
                        guarded=contract.guard_answer(case['slot'],candidate,replay['shown_items']) if arm=='V' else None
                        delivered=guarded['value'] if guarded else raw
                        emitted=json.dumps({'value':delivered}) if guarded else response['text']
                        retrieved=any(i['meta']['publication_id']==identity_key for i in replay['shown_items'])
                        append(output/'turns.jsonl',{'slot':case['slot'],'seed':seed,'arm':arm,'turn':turn,'call_key':key,
                            'question':question,'raw_value':raw,'delivered_value':delivered,
                            'raw_agreement':agreement(raw,value),'delivered_agreement':agreement(delivered,value),
                            'retrieved':retrieved,'resolution':guarded['resolution'] if guarded else 'unguarded',
                            'guard':guarded,'replay':replay,'session':0 if turn==0 else 1})
                        history += [messages[-1],{'role':'assistant','content':emitted}]
        first_raw=read_rows(output/'controls.jsonl')[0]['raw']
        for i in range(2):
            response=client.ask(f'canary-{i}',positive_messages[0],7)
            append(output/'controls.jsonl',{'key':f'canary-{i}','passed':answer_value(response)==config['positive_controls'][0],
                                           'byte_identical_to_first':response['text']==first_raw,'raw':response['text']})
        finish=client.finish()
        write(output/'completion.json',finish)
        if source_identity()['sha256']!=identity['sha256']:
            raise RuntimeError('Measured sources changed during execution.')
        completed=True
    except Exception as exc:
        failure={'type':type(exc).__name__,'message':str(exc)}
        write(output/'failure.json',failure)
    finally:
        try:
            client.release()
        except Exception as exc:
            write(output/'release-failure.json',{'type':type(exc).__name__,'message':str(exc)})
    summary=summarize(config,cases,output,completed)
    write(output/'summary.json',summary)
    write(output/'execution-state.json',{'complete':summary['complete'],'failure':failure,
                                         'analysis_git_head':source_identity()['git_head']})
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(argv)
    config=json.loads((DATA/'config.json').read_text(encoding='utf-8'))
    cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
    result=execute(args.output,config,cases)
    print(json.dumps({'complete':result['complete'],'larger_offline_test_only':result['larger_offline_test_only']}))
    return 0 if result['complete'] else 1


if __name__=='__main__':
    raise SystemExit(main())
