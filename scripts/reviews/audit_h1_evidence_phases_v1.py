"""Offline authored integrity replay of density/order phases; no inference/judge."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import h1_chronological_pack_v1 as H

D=H.D
C=H.C


def audit(raw_root,output,phase):
    failures=[]
    def check(ok,message):
        if not ok:failures.append(message)
    module=D if phase=='density' else H
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    freeze=json.loads((output/'raw-freeze.json').read_text(encoding='utf-8'))
    manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    finish=json.loads((output/'finished.json').read_text(encoding='utf-8'))
    relative=(module.DATA/'raw-freeze.json').relative_to(ROOT).as_posix()
    check(subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)==(output/'raw-freeze.json').read_bytes(),'public freeze not committed')
    check(all(C.sha(output/n)==h for n,h in freeze['files_sha256'].items()),'raw evidence drift')
    check(manifest['source']==freeze['source'],'source manifest differs')
    check(all(C.sha(ROOT/n)==h for n,h in manifest['source']['digests'].items()),'execution source drift')
    check(C.sha(output/'packets.jsonl')==prep['packet_digest'],'packet digest differs')
    packets=C.P.read_rows(output/'packets.jsonl');answers=C.P.read_rows(output/'answers.jsonl')
    attempts=C.P.read_rows(output/'attempts.jsonl');responses=C.P.read_rows(output/'responses.jsonl')
    req={r['key']:r for r in attempts};res={r['key']:r for r in responses};saved={r['call_key']:r for r in answers}
    expected_primary=144 if phase=='density' else 336
    check(len(packets)==len(answers)==len(saved)==expected_primary,'primary roster differs')
    check(len(attempts)==len(req)==len(responses)==len(res)==module.CALLS,'native call count/uniqueness differs')
    check(set(req)==set(res)==set(saved)|{'control-0','control-1','control-2'},'native call keys differ')
    usage={};cases=Counter();full={};unchanged=Counter();parse_failures=0;primary_keys=[]
    for split in ['dev','valid']:
        corpus=ROOT/'data/lab/corpus-h1';reveal=corpus/('reveal-v0' if split=='dev' else 'valid-b/reveal')
        paths={'questions':reveal/'queries.jsonl','gold':reveal/'gold.jsonl',
            'store':raw_root/f'h1-v2-{split}-memory.jsonl','roles':raw_root/f'h1-v2-{split}-capture/source-roles.jsonl'}
        for name,path in paths.items():check(C.sha(path)==prep['input_digests'][split+'/'+name],'input drift: '+split+'/'+name)
        qs={q['query_id']:q for q in C.P.read_rows(paths['questions'])};roles={r['source']:r['channel'] for r in C.P.read_rows(paths['roles'])}
        base=raw_root/f'h1-v5-{split}-reader'
        parent=json.loads((base/'raw-freeze.json').read_text(encoding='utf-8'))
        check(all(C.sha(base/n)==h for n,h in parent['files_sha256'].items()),'parent output drift')
        original={r['id']:r['shown_ids'] for r in C.P.read_rows(base/'answers.jsonl') if r['arm']=='chains'}
        parent_requests={r['key']:r['request'] for r in C.P.read_rows(base/'attempts.jsonl')}
        if phase=='density':
            history=corpus/('prefix-v0/history.jsonl' if split=='dev' else 'valid-b/prefix/history.jsonl')
            ids={r['event_id']:f'E{i:06d}' for i,r in enumerate(C.P.read_rows(history))}
            oracle={g['query_id']:(ids[g['gold_event_id']],ids[g['forbidden_event_id']]) for g in C.P.read_rows(paths['gold']) if g['case_id'].rsplit('-',1)[0]=='OBSOLETE'}
        else:check(C.sha(base/'raw-freeze.json')==prep['input_digests'][split+'/parent_freeze'],'parent freeze differs')
        with C.V5.Memory(paths['store']) as memory:
            for p in [p for p in packets if p['split']==split]:
                q=qs[p['query_id']];cases[split,p['id'],p['arm']]+=1
                if phase=='density':
                    supporting,obsolete=oracle[p['query_id']]
                    expected_ids=D.conditions(supporting,obsolete)[p['arm']]
                    context=D.pack(memory,roles,expected_ids,q['asked_on_day'])
                else:
                    expected_ids=original[p['id']] if p['arm']=='original' else H.ordered(original[p['id']],memory.sources)
                    pack=C.H4.pack(memory,roles,expected_ids);context=pack['context']
                    check(pack['ids']==expected_ids,'chronological pack truncated')
                    if p['arm']=='chronological':
                        check(Counter(expected_ids)==Counter(original[p['id']]),'chronological evidence added/removed')
                        unchanged[split]+=expected_ids==original[p['id']]
                check(p['shown_ids']==expected_ids,'wrong evidence intervention')
                check(all(memory.sources[s].scope=='h1-'+split and memory.sources[s].recorded<=q['asked_on_day'] for s in expected_ids if s!='CONTROL_NEUTRAL'),'source time/scope violation')
                expected=[{'role':'system','content':C.SYSTEM+C.AUTH},{'role':'user','content':context+'\nQuestion: '+q['question']}]
                if phase=='chronological' and p['arm']=='original':check(expected==parent_requests['read-chains-'+p['id']]['messages'],'parent original message differs')
                key=p['call_key'];primary_keys.append(key);request=req[key]['request'];response=res[key]
                check(p['messages']==expected==request['messages'],'reconstructed native messages differ')
                check(C.P.sha(request)==req[key]['request_sha256'],'native request hash differs')
                check(request['format']==C.SCHEMA,'answer schema differs')
                check(request['model']==manifest['config']['model'] and request['options']==dict(manifest['config']['options'],seed=7),'model/options differ')
                check(len(context.encode())<=4500,'context exceeds byte budget')
                check(saved[key]['answer']==C.parse(response['text']),'saved/native answer differs')
                parse_failures+=C.parse(response['text']) is None
                s=usage.setdefault(p['arm'],{'n':0,'message_bytes':0,'prompt_eval_count':0,'eval_count':0,'done_reasons':Counter()})
                s['n']+=1;s['message_bytes']+=len(json.dumps(expected,ensure_ascii=False).encode());s['done_reasons'][response['done_reason']]+=1
                for field in ['prompt_eval_count','eval_count']:
                    value=response.get('usage',{}).get(field)
                    check(isinstance(value,int) and value>=0,'missing native usage');s[field]+=value or 0
                full[split,p['id'],p['arm']]=expected
    check(all(n==1 for n in cases.values()) and len(cases)==expected_primary,'case-condition uniqueness differs')
    expected_cases=12 if phase=='density' else 84
    check(all(sum(s==split and a==arm for s,i,a in cases)==expected_cases for split in ['dev','valid'] for arm in module.ARMS),'case-family roster incomplete')
    if phase=='chronological':check(dict(unchanged)==prep['unchanged_pairs'],'unchanged-pair count differs')
    controls=C.P.read_rows(output/'controls.jsonl')
    check(len(controls)==3 and all(c['correct'] for c in controls),'saved controls failed')
    for i,token in enumerate(['cobalt-47','juniper-83','marble-29']):
        check(json.loads(res[f'control-{i}']['text']).get('value')==token,'actual transport control failed')
    lines=(raw_root/'h1-local-ledger.jsonl').read_bytes().splitlines(keepends=True)
    before=prep['local_ledger_before'];after=before+module.CALLS
    digest=lambda rows:hashlib.sha256(b''.join(rows)).hexdigest()
    check(digest(lines[:before])==prep['local_ledger_digest_before'],'old ledger prefix changed')
    phase_rows=[json.loads(s) for s in lines[before:after]]
    check(len(phase_rows)==module.CALLS and {r['key'] for r in phase_rows}=={output.name+':'+k for k in req},'cumulative phase call keys differ')
    check(finish['local_ledger_after']==after<=D.CAP and digest(lines[:after])==finish['local_ledger_digest_after'],'frozen final ledger prefix differs')
    check(C.sha(raw_root/'api-ledger.jsonl')==prep['api_ledger_digest_before'],'paid ledger changed')
    check(finish['model_digest_unchanged'] and finish['generation_calls']==module.CALLS,'model/call receipt differs')
    check(finish['elapsed_seconds']<=manifest['config']['max_seconds'],'phase deadline exceeded')
    release=json.loads((output/'release.json').read_text(encoding='utf-8'))
    check(release['done'] and release['done_reason']=='unload' and release['model']==manifest['config']['model'],'owned model not released')
    return {'phase':phase,'failures':failures,'reconstructed_primary_packets':len(packets),
        'actual_local_calls':module.CALLS,'api_ledger_unchanged':not any('paid' in f for f in failures),
        'h1_ledger_before':before,'h1_ledger_after_phase':after,'local_cap':D.CAP,'parse_failures':parse_failures,
        'unique_primary_messages':len({json.dumps(p['messages'],sort_keys=True) for p in packets}),
        'identical_paired_messages':sum(full[s,i,'original']==full[s,i,'chronological'] for s,i,a in full if a=='original') if phase=='chronological' else None,
        'native_usage_by_arm':usage,'claim':'Authored deterministic integrity replay, not independent semantic evaluation.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['raw-root','output','destination']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--phase',choices=['density','chronological'],required=True)
    args=vars(parser.parse_args());destination=args.pop('destination');result=audit(**args)
    C.write(destination,result);print(json.dumps(result,indent=2));raise SystemExit(bool(result['failures']))
