"""Post-freeze authored BEAM review packets and transparent descriptive counts.

No model client or semantic auto-judge. Verdicts must be supplied by the author.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import beam_reader_evidence_v1 as B
A=B.A
TARGETS=('N','B','Craw','Cdelivered')


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def candidate_id(case_id,text):
    return 'a-'+hashlib.sha256((case_id+'\0'+text).encode()).hexdigest()[:20]


def group_answers(case_id,answers):
    """Deduplicate exact valid strings within one case; malformed always wrong."""
    choices={};mapping={}
    for target,row in answers.items():
        text=row['raw_answer'] if target=='Craw' else row['delivered_answer']
        if row['valid_output']:
            if not isinstance(text,str) or not text.strip():raise ValueError('Valid answer has no text.')
            key=candidate_id(case_id,text)
            if key in choices and choices[key]!=text:raise ValueError('Candidate hash collision.')
            choices[key]=text;mapping[target]={'candidate_id':key,'valid_output':True}
        else:mapping[target]={'candidate_id':None,'valid_output':False}
    return [{'candidate_id':key,'text':text} for key,text in sorted(choices.items())],mapping


def prepare(output,labels,audit,destination):
    # The complete raw freeze must already exist in committed Git, not merely
    # in a mutable private directory or the index.
    path='data/lab/beam-reader-evidence-v1/raw-freeze.json'
    committed=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
    if committed!=(output/'raw-freeze.json').read_bytes():raise ValueError('Commit the complete raw freeze before opening references.')
    freeze=load(output/'raw-freeze.json');prep=load(output/'preparation.json');checked=load(audit)
    if checked['failures'] or checked['native_responses_replayed']!=605 or checked['raw_freeze_sha256']!=A.sha(output/'raw-freeze.json'):raise ValueError('Full raw audit required.')
    for name,h in freeze['files_sha256'].items():
        if Path(name).name!=name or A.sha(output/name)!=h:raise ValueError('Frozen raw file changed.')
    if A.sha(labels)!=prep['labels_sha256']:raise ValueError('Reference identity changed.')
    # First semantic reference read happens below, after the checks above.
    refs=list(A.rows(labels));packets=[r for r in A.rows(output/'packets.jsonl') if r['type']=='primary']
    answers=list(A.rows(output/'answers.jsonl'));by_case={};questions={}
    for row in answers:
        arms=by_case.setdefault(row['id'],{})
        if row['arm'] in arms:raise ValueError('Duplicate case/arm.')
        arms[row['arm']]=row
    for row in packets:questions[row['id']]=json.loads(row['messages'][1]['content'])['question']
    if len(refs)!=200 or len({r['id'] for r in refs})!=200 or {r['id'] for r in refs}!=set(by_case) or set(questions)!=set(by_case):raise ValueError('Full200case roster required.')
    destination.mkdir(parents=True,exist_ok=False);count=0
    for ref in refs:
        arms=by_case[ref['id']]
        if set(arms)!=set(B.ARMS) or any(r['conversation_id']!=ref['conversation_id'] for r in arms.values()):raise ValueError('Reference/case scope differs.')
        candidates,mapping=group_answers(ref['id'],{'N':arms['N'],'B':arms['B'],'Craw':arms['C'],'Cdelivered':arms['C']})
        count+=len(candidates)
        A.append(destination/'packet.jsonl',{'id':ref['id'],'conversation_id':ref['conversation_id'],'ability':ref['ability'],
            'question':questions[ref['id']],'reference_annotations':ref['annotations'],'candidates':candidates})
        A.append(destination/'mapping.jsonl',{'id':ref['id'],'mapping':mapping})
    A.write(destination/'manifest.json',{'raw_freeze_sha256':A.sha(output/'raw-freeze.json'),'labels_sha256':A.sha(labels),
        'integrity_audit_sha256':A.sha(audit),'packet_sha256':A.sha(destination/'packet.jsonl'),
        'mapping_sha256':A.sha(destination/'mapping.jsonl'),'cases':200,'distinct_within_question_answers':count,
        'reviewer':'Codex author; no model judge; not independent or fully blind',
        'source_head_at_reference_join':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()})
    print(json.dumps({'cases':200,'distinct_within_question_answers':count}))


def validate_verdicts(packets,verdicts):
    by_id={r['id']:r for r in verdicts}
    if len(by_id)!=len(verdicts) or set(by_id)!={p['id'] for p in packets}:raise ValueError('One authored verdict required for every case; no extras.')
    result={}
    for p in packets:
        v=by_id[p['id']]
        if set(v)!={'id','reference_status','reference_note','candidates'} or v['reference_status'] not in {'usable','ambiguous','defective'} or not isinstance(v['reference_note'],str):raise ValueError('Reference review schema differs.')
        if v['reference_status']!='usable' and len(v['reference_note'].strip())<12:raise ValueError('Ambiguous/defective reference needs an explicit note.')
        candidates={c['candidate_id']:c for c in v['candidates']}
        if len(candidates)!=len(v['candidates']) or set(candidates)!={c['candidate_id'] for c in p['candidates']}:raise ValueError('Every deduplicated answer needs a verdict exactly once.')
        for c in candidates.values():
            if (set(c)!={'candidate_id','pass','material_contradiction','reason'}
                or not (c['pass'] is None or type(c['pass']) is bool)
                or not (c['material_contradiction'] is None or type(c['material_contradiction']) is bool)
                or not isinstance(c['reason'],str) or not 12<=len(c['reason'].strip())<=1200):raise ValueError('Invalid authored candidate verdict.')
            if c['pass'] is True and c['material_contradiction'] is True:raise ValueError('Complete-rubric pass cannot materially contradict reference.')
        result[p['id']]={'reference_status':v['reference_status'],'candidates':candidates}
    return result


def outcome(verdict,target):
    if not target['valid_output']:return {'pass':False,'uncertain':False,'material_contradiction':None,'format_failure':True}
    row=verdict['candidates'][target['candidate_id']]
    uncertain=verdict['reference_status']!='usable' or row['pass'] is None
    return {'pass':row['pass'] is True and not uncertain,'uncertain':uncertain,
        'material_contradiction':row['material_contradiction'],'format_failure':False}


def summarize(rows):
    result={}
    for target in TARGETS:
        r=[x['outcomes'][target] for x in rows]
        result[target]={'cases':len(r),'passes':sum(x['pass'] for x in r),'uncertain':sum(x['uncertain'] for x in r),
            'upper_pass_bound':sum(x['pass'] or x['uncertain'] for x in r),'format_failures':sum(x['format_failure'] for x in r),
            'material_contradictions':sum(x['material_contradiction'] is True for x in r),
            'unresolved_contradiction':sum(x['material_contradiction'] is None and not x['format_failure'] for x in r)}
    return result


def score(review,verdicts,audit,destination):
    manifest=load(review/'manifest.json');checked=load(audit)
    if A.sha(review/'packet.jsonl')!=manifest['packet_sha256'] or A.sha(review/'mapping.jsonl')!=manifest['mapping_sha256'] or A.sha(audit)!=manifest['integrity_audit_sha256']:raise ValueError('Review packet/mapping/audit changed.')
    packets=list(A.rows(review/'packet.jsonl'));vs=validate_verdicts(packets,list(A.rows(verdicts)))
    maps=list(A.rows(review/'mapping.jsonl'))
    if [r['id'] for r in maps]!=[p['id'] for p in packets]:raise ValueError('Review mapping roster differs.')
    rows=[]
    for p,m in zip(packets,maps,strict=True):
        rows.append({k:p[k] for k in ['id','ability','conversation_id']}|{'reference_status':vs[p['id']]['reference_status'],
            'outcomes':{t:outcome(vs[p['id']],m['mapping'][t]) for t in TARGETS}})
    total=summarize(rows);pairs={}
    for left,right in [('N','B'),('B','Craw'),('B','Cdelivered')]:
        pairs[left+'->'+right]={'both_pass':sum(r['outcomes'][left]['pass'] and r['outcomes'][right]['pass'] for r in rows),
            'gains':sum(not r['outcomes'][left]['pass'] and r['outcomes'][right]['pass'] for r in rows),
            'losses':sum(r['outcomes'][left]['pass'] and not r['outcomes'][right]['pass'] for r in rows),
            'both_fail':sum(not r['outcomes'][left]['pass'] and not r['outcomes'][right]['pass'] for r in rows)}
    new_contradictions=[r['id'] for r in rows if r['outcomes']['Cdelivered']['material_contradiction'] is True and r['outcomes']['B']['material_contradiction'] is not True]
    latency_ratio=checked['arm_statistics']['C']['median_wall_seconds']/checked['arm_statistics']['B']['median_wall_seconds']
    conditions={'more_C_delivered_passes_than_B':total['Cdelivered']['passes']>total['B']['passes'],
        'no_new_material_contradiction':not new_contradictions,'C_to_B_median_wall_at_most_2':latency_ratio<=2}
    unresolved=any(total[t]['uncertain'] or total[t]['unresolved_contradiction'] for t in ['B','Cdelivered'])
    decision='reject-adoption' if not all(conditions.values()) else ('inconclusive-reference-uncertainty' if unresolved else 'fresh-transfer-candidacy-only-no-adoption')
    report={'cases':len(rows),'evaluation':'Codex authored complete-rubric assessment; not official BEAM accuracy; no model judge',
        'independent':False,'fully_blind':False,'reference_status':dict(Counter(r['reference_status'] for r in rows)),
        'totals':total,'paired':pairs,'new_C_delivered_material_contradiction_cases':new_contradictions,
        'guard_false_refusal_cases':[r['id'] for r in rows if r['outcomes']['Craw']['pass'] and not r['outcomes']['Cdelivered']['pass']],
        'by_ability':{a:summarize([r for r in rows if r['ability']==a]) for a in sorted({r['ability'] for r in rows})},
        'by_history':{a:summarize([r for r in rows if r['conversation_id']==a]) for a in sorted({r['conversation_id'] for r in rows})},
        'screen_conditions':conditions,'C_to_B_median_wall_ratio':latency_ratio,'decision':decision,
        'review_packet_manifest_sha256':A.sha(review/'manifest.json'),'verdicts_sha256':A.sha(verdicts),
        'raw_freeze_sha256':manifest['raw_freeze_sha256'],'all_200_cases_retained':len(rows)==200,
        'limits':'Ten shared history clusters; public single-seed exploratory run; self-authored scoring; no vendor or general-memory claim.'}
    if len(rows)!=200:raise ValueError('Full200denominator required.')
    A.write(destination,report);print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('prepare')
    for name in ['output','labels','audit','destination']:x.add_argument('--'+name,type=Path,required=True)
    x=sub.add_parser('score')
    for name in ['review','verdicts','audit','destination']:x.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());globals()[args.pop('command')](**args)
