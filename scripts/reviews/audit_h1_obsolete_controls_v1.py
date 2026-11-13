"""Offline integrity of whole-family controls, clocks, packets and ledgers.

This is authored replay/provenance validation, not independent semantic review.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import h1_obsolete_controls_v1 as C


def audit(raw_root,output):
    failures=[]
    def check(condition,message):
        if not condition: failures.append(message)
    prep=json.loads((output/'preparation.json').read_text(encoding='utf-8'))
    manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    freeze=json.loads((output/'raw-freeze.json').read_text(encoding='utf-8'))
    check(all(C.sha(output/name)==h for name,h in freeze['files_sha256'].items()),'raw freeze drift')
    check(all(C.sha(ROOT/name)==h for name,h in manifest['source']['sha256'].items()),'execution source drift')
    packets=C.P.read_rows(output/'packets.jsonl');answers=C.P.read_rows(output/'answers.jsonl')
    requests={r['key']:r for r in C.P.read_rows(output/'attempts.jsonl')}
    responses={r['key']:r for r in C.P.read_rows(output/'responses.jsonl')}
    stats={};invalid_json=0
    for split in ['dev','valid']:
        corpus=ROOT/'data/lab/corpus-h1'
        history=corpus/('prefix-v0/history.jsonl' if split=='dev' else 'valid-b/prefix/history.jsonl')
        reveal=corpus/('reveal-v0' if split=='dev' else 'valid-b/reveal')
        paths={'history':history,'questions':reveal/'queries.jsonl','gold':reveal/'gold.jsonl',
               'roles':raw_root/f'h1-v2-{split}-capture/source-roles.jsonl',
               'store':raw_root/f'h1-v2-{split}-memory.jsonl',
               'reader-freeze':raw_root/f'h1-v5-{split}-reader/raw-freeze.json'}
        for name,path in paths.items():check(C.sha(path)==prep['input_sha256'][split+'/'+name],'input drift: '+split+'/'+name)
        ids={r['event_id']:f'E{i:06d}' for i,r in enumerate(C.P.read_rows(history))}
        oracle={g['query_id']:(ids[g['gold_event_id']],ids[g['forbidden_event_id']]) for g in C.P.read_rows(paths['gold']) if g['case_id'].rsplit('-',1)[0]=='OBSOLETE'}
        roles={r['source']:r['channel'] for r in C.P.read_rows(paths['roles'])}
        qs=C.P.read_rows(paths['questions']);original={r['id']:r['shown_ids'] for r in C.P.read_rows(raw_root/f'h1-v5-{split}-reader/answers.jsonl') if r['arm']=='chains'}
        with C.V5.Memory(paths['store']) as memory:
            for p in [r for r in packets if r['split']==split]:
                q=qs[int(p['id'][1:])]; supporting,obsolete=oracle[q['query_id']]
                expected_ids=C.condition_ids(original[p['id']],supporting,obsolete)[p['arm']]
                check(p['shown_ids']==expected_ids,'wrong evidence intervention')
                check(all(memory.sources[s].scope=='h1-'+split and memory.sources[s].recorded<=q['asked_on_day'] for s in expected_ids),'source scope/time')
                pack=C.H4.pack(memory,roles,expected_ids)
                expected=[{'role':'system','content':C.SYSTEM+C.AUTH},
                          {'role':'user','content':pack['context']+'\nQuestion: '+q['question']}]
                request=requests[p['call_key']]['request']
                check(request['messages']==expected,'native messages differ')
                check(C.P.sha(request)==requests[p['call_key']]['request_sha256'],'native request hash')
                check(request['model']==manifest['config']['model'] and request['options']==dict(manifest['config']['options'],seed=7),'model/options differ')
                check(request['format']==C.SCHEMA,'native schema differs')
                check(pack['ids']==expected_ids and len(pack['context'].encode())<=4500,'evidence truncated/over budget')
                response=responses[p['call_key']];invalid_json+=C.parse(response['text']) is None
                s=stats.setdefault(p['arm'],{'n':0,'message_bytes':0,'reported_prompt_eval_count':0,'reported_eval_count':0})
                s['n']+=1;s['message_bytes']+=len(json.dumps(expected,ensure_ascii=False).encode())
                for field in ['prompt_eval_count','eval_count']:
                    value=response.get('usage',{}).get(field)
                    check(isinstance(value,int) and value>=0,'unknown native token usage')
                    s['reported_'+field]+=value or 0
    ledger=(raw_root/'h1-local-ledger.jsonl').read_bytes();lines=ledger.splitlines(keepends=True)
    before=b''.join(lines[:prep['local_ledger_before']])
    check(hashlib.sha256(before).hexdigest()==prep['local_ledger_sha256_before'],'old local ledger prefix changed')
    new=[json.loads(s) for s in lines[prep['local_ledger_before']:]]
    check(len(new)==99 and {r['key'] for r in new}=={output.name+':'+k for k in requests},'cumulative local call keys differ')
    check(C.sha(raw_root/'api-ledger.jsonl')==prep['api_ledger_sha256_before'],'paid ledger changed')
    controls=C.P.read_rows(output/'controls.jsonl')
    check(len(controls)==3 and all(r['correct'] for r in controls),'transport controls')
    check(len(packets)==96 and len(answers)==96 and len(requests)==99 and len(responses)==99,'incomplete roster')
    return {'failures':failures,'reconstructed_primary_packets':len(packets),'local_generations':len(new),
        'cumulative_h1_local':len(lines),'api_ledger_unchanged':True,'input_gold_hashes_unchanged':True,
        'oracle_source_ids_intentionally_used':True,'parse_failures':invalid_json,
        'unique_primary_message_packets':len({json.dumps(r['messages'],sort_keys=True) for r in packets}),
        'context_and_reported_native_tokens':stats,
        'semantic_independence':'Authored deterministic replay, not independent semantic evaluation.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['raw-root','output','destination']:parser.add_argument('--'+name,type=Path,required=True)
    args=vars(parser.parse_args());destination=args.pop('destination');result=audit(**args)
    C.write(destination,result);print(json.dumps(result,indent=2));raise SystemExit(bool(result['failures']))
