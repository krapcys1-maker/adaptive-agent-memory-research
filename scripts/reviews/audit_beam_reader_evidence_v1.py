"""Replay the complete frozen reader phase without labels or inference."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import beam_reader_evidence_v1 as B
A=B.A


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def unique(rows):
    result={r['key']:r for r in rows}
    if len(result)!=len(rows):raise ValueError('Duplicate native call key.')
    return result


def audit(output,access,raw_root,ledger):
    freeze=load(output/'raw-freeze.json');manifest=load(output/'manifest.json')
    source=manifest['source'];cfg=manifest['config'];prep=manifest['preparation']
    if source!=freeze['source'] or not source['clean_tree']:raise ValueError('Source identity differs.')
    for name,h in freeze['files_sha256'].items():
        if Path(name).name!=name or A.sha(output/name)!=h:raise ValueError('Raw freeze changed.')
    for name,h in source['sha256'].items():
        committed=subprocess.check_output(['git','show',source['head']+':'+name],cwd=ROOT)
        if hashlib.sha256(committed).hexdigest()!=h or A.sha(ROOT/name)!=h:raise ValueError('Frozen source differs from committed/executed code.')
    B.validate_config(cfg)
    if cfg!=load(B.DATA/'config.json') or prep!=load(B.DATA/'preparation.json') or prep!=load(output/'preparation.json'):raise ValueError('Frozen config/preparation differs.')
    for path,field in [(output/'packets.jsonl','packets_sha256'),(access/'manifest.json','access_manifest_sha256'),
                       (access/'query-packets.jsonl','access_packet_sha256'),(B.DATA/'config.json','config_sha256'),
                       (raw_root/'h1-local-ledger.jsonl','h1_ledger_sha256_before'),(raw_root/'api-ledger.jsonl','api_ledger_sha256_before')]:
        if A.sha(path)!=prep[field]:raise ValueError('Inputs/old cumulative ledgers changed.')
    packets=list(A.rows(output/'packets.jsonl'));attempts=list(A.rows(output/'attempts.jsonl'));responses=list(A.rows(output/'responses.jsonl'))
    controls=list(A.rows(output/'controls.jsonl'));answers=list(A.rows(output/'answers.jsonl'))
    maps=[unique(x) for x in [packets,attempts,responses,controls+answers]]
    if any(set(m)!=set(maps[0]) for m in maps) or any(len(x)!=605 for x in [packets,attempts,responses,controls+answers]):raise ValueError('Incomplete605native request/output roster.')
    if any([r['key'] for r in x]!=[r['key'] for r in packets] for x in [attempts,responses,controls+answers]):raise ValueError('Actual execution order differs.')
    if packets[:5]!=B.controls() or len(controls)!=5 or len(answers)!=600:raise ValueError('Control/primary roster differs.')
    expected=[];cases=set();matched=0
    for i,row in enumerate(A.rows(access/'query-packets.jsonl')):
        if row['id'] in cases:raise ValueError('Duplicate case.')
        cases.add(row['id']);ps=B.paired_packets(row,cfg['max_message_bytes'])
        order=B.ARMS[i%3:]+B.ARMS[:i%3]
        for arm in order:
            p=ps[arm];expected.append({'type':'primary','id':row['id'],'conversation_id':row['conversation_id'],'arm':arm,
                'key':f'read-{row["id"]}-{arm}','messages':p['messages'],'aliases':p['aliases'],'shown_ids':p['shown_ids'],
                'schema':B.c_schema(p['aliases']) if arm=='C' else B.B_SCHEMA})
        if ps['B']['messages'][1]!=ps['C']['messages'][1]:raise ValueError('B/C evidence mismatch.')
        if json.loads(ps['N']['messages'][1]['content'])['history']['evidence']:raise ValueError('Memory in N.')
        matched+=1
    if len(cases)!=200 or expected!=packets[5:]:raise ValueError('Reconstructed complete primary matrix differs.')
    stats={};request_bytes=[];message_bytes=[]
    for p in packets:
        key=p['key'];attempt=maps[1][key];response=maps[2][key];saved=maps[3][key]
        B.request_guard(cfg,p['messages'],p['schema'])
        payload=B.native_payload(cfg,p['messages'],p['schema'])
        if attempt['request']!=payload or attempt['request_sha256']!=B.P.sha(payload):raise ValueError('Native request mismatch.')
        replay=B.grade_output(response['text'],p['arm'],p['messages'],p['aliases'])
        actual={k:p[k] for k in ['type','key','arm']}|replay
        if p['type']=='primary':actual|={k:p[k] for k in ['id','conversation_id']}
        else:
            actual['correct']=replay['valid_output'] and replay['delivered_answer']==p['expected']
            if p['arm']=='C' and p['expected']!='UNKNOWN':actual['correct']&=replay['guard_reason']=='literal_evidence_valid'
            if not actual['correct']:raise ValueError('A retained control failed.')
        if saved!=actual:raise ValueError('Saved answer/provenance is not a replay of native text.')
        request_bytes.append(len(json.dumps(payload).encode()));message_bytes.append(max(B.W.message_bytes(p['messages']).values()))
    for arm in B.ARMS:
        selected=[r for r in answers if r['arm']==arm];native=[maps[2][r['key']] for r in selected]
        stats[arm]={'primary_calls':len(selected),'valid_format':sum(r['valid_output'] for r in selected),
            'guard_reasons':dict(Counter(r['guard_reason'] for r in selected)),
            'delivered_unknown':sum(r['delivered_answer'].strip().casefold()=='unknown' for r in selected),
            'native_done_reasons':dict(Counter(r['done_reason'] for r in native)),
            'median_wall_seconds':median(r['wall_seconds'] for r in native),'total_wall_seconds':sum(r['wall_seconds'] for r in native),
            'prompt_tokens':sum(r['usage']['prompt_eval_count'] for r in native),
            'generated_tokens':sum(r['usage']['eval_count'] for r in native)}
    retained=list(A.rows(ledger));finished=load(output/'finished.json')
    if len(retained)!=605 or len({r['key'] for r in retained})!=605 or [r['key'] for r in retained]!=[output.name+':'+p['key'] for p in packets]:raise ValueError('BEAM task ledger differs.')
    if any(r['model']!=cfg['model'] or r['event']!='local-attempt' or r['task']!='beam-reader-evidence-v1' for r in retained):raise ValueError('Task ledger model/event differs.')
    if finished['generation_calls']!=605 or finished['beam_ledger_after']!=605 or finished['beam_ledger_sha256_after']!=A.sha(ledger) or not finished['model_digest_unchanged']:raise ValueError('Completion/digest receipt differs.')
    release=load(output/'release.json')
    if release!={'model':cfg['model'],'done':True,'done_reason':'unload'}:raise ValueError('Owned model release not confirmed.')
    preflight=load(output/'preflight.json')
    if preflight['model']['digest']!=cfg['model_digest'] or preflight['model']['name']!=cfg['model']:raise ValueError('Preflight identity differs.')
    return {'failures':[],'source_head':source['head'],'primary_cases':200,'native_requests_replayed':605,
        'native_responses_replayed':605,'controls_passed':5,'matched_B_C_evidence_pairs':matched,
        'source_and_raw_hashes_verified':True,'old_h1_and_paid_ledgers_unchanged':True,'new_api_calls':0,
        'beam_task_local_calls':605,'pr105_local_calls':4361,'pr105_all_calls':4824,
        'max_native_request_bytes':max(request_bytes),'max_message_bytes':max(message_bytes),'arm_statistics':stats,
        'elapsed_seconds':finished['elapsed_seconds'],'raw_freeze_sha256':A.sha(output/'raw-freeze.json'),
        'labels_read':False,'semantic_score':None,'claim':'Authored integrity replay only; semantic rubric review remains separate.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','access','raw-root','ledger','destination']:p.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());destination=args.pop('destination');result=audit(**args)
    A.write(destination,result);print(json.dumps(result,indent=2))
