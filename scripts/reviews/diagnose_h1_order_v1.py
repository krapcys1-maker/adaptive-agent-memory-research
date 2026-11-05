"""Post-hoc same-message stability versus changed-order outcome decomposition."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import h1_chronological_pack_v1 as H
C=H.C


def diagnose(output,score_path):
    freeze=json.loads((output/'raw-freeze.json').read_text(encoding='utf-8'))
    if any(C.sha(output/n)!=h for n,h in freeze['files_sha256'].items()):raise ValueError('Raw freeze drift.')
    packets={(p['split'],p['id'],p['arm']):p for p in C.P.read_rows(output/'packets.jsonl')}
    answers={(p['split'],p['id'],p['arm']):p['answer'] for p in C.P.read_rows(output/'answers.jsonl')}
    score=json.loads(score_path.read_text(encoding='utf-8'));scores={(p['split'],p['id'],p['arm']):p for p in score['records']}
    if set(packets)!=set(answers) or set(packets)!=set(scores) or len(packets)!=336:raise ValueError('Paired roster differs.')
    totals=[];changes=[]
    for split in ['dev','valid']:
        for group in ['identical_messages','changed_order']:
            ids=[qid for s,qid,arm in packets if s==split and arm=='original' and
                ((packets[s,qid,'original']['messages']==packets[s,qid,'chronological']['messages'])==(group=='identical_messages'))]
            row={'split':split,'group':group,'n':len(ids),'text_differences':sum(answers[split,i,'original']!=answers[split,i,'chronological'] for i in ids)}
            for arm in H.ARMS:
                row[arm]={k:sum(scores[split,i,arm][k] for i in ids) for k in ['answered','leaked','clean_answered']}
            totals.append(row)
            for i in ids:
                a,b=[scores[split,i,arm] for arm in H.ARMS]
                if any(a[k]!=b[k] for k in ['answered','leaked','clean_answered']):changes.append({'split':split,'id':i,'group':group,
                    'family':a['family'],'clean_delta':b['clean_answered']-a['clean_answered'],'leak_delta':b['leaked']-a['leaked']})
    return {'groups':totals,'metric_changed_pairs':changes,'parent_original_text_drift_count':len(score['original_text_drift']),
        'input_sha256':{'raw_freeze':C.sha(output/'raw-freeze.json'),'scored_records':C.sha(score_path)},
        'new_inference_calls':0,'interpretation':'Post-hoc stability control. Same seed/temperature does not guarantee byte-identical live outputs. Attribute no same-message differences to sorting; do not upgrade a screen to confirmation.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['output','score-path','destination']:p.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());destination=args.pop('destination');result=diagnose(**args)
    C.write(destination,result);print(json.dumps(result,indent=2))
