"""Post-hoc paired reader summary; no inference, re-ranking or metric replacement."""
import argparse
import hashlib
import json
from math import comb
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import diagnose_structured_memory_v1 as M


def compare(raw_root,gold_path):
    inputs={};readers={};primary={}
    for label in ['local','flash']:
        base=raw_root/(label+'-path-answers')
        freeze=json.loads((base/'raw-freeze.json').read_text(encoding='utf-8'))
        if any(M.V5.V1.file_sha(base/n)!=h for n,h in freeze['files_sha256'].items()):raise ValueError('Raw path-answer freeze changed.')
        inputs[label+'_freeze']=M.V5.V1.file_sha(base/'raw-freeze.json')
        rows=M.P.read_rows(base/'answers.jsonl')
        readers[label]={r['id']:r['result'].get('value') for r in rows}
        score_path=ROOT/f'data/lab/structured-memory-v1/{label}-path-score.json'
        primary[label]={r['id']:r['correct'] for r in json.loads(score_path.read_text(encoding='utf-8'))['records']}
        inputs[label+'_primary_score']=M.V5.V1.file_sha(score_path)
        if len(rows)!=100 or len(readers[label])!=100:raise ValueError('Expected complete 100-question readers.')
    gold={r['id']:r['answers'] for r in M.P.read_rows(gold_path)}
    if not all(set(x)==set(gold) for x in [*readers.values(),*primary.values()]) or len(gold)!=100:raise ValueError('Gold/question IDs differ.')
    inputs['gold']=M.V5.V1.file_sha(gold_path)
    source_diag=json.loads((ROOT/'data/lab/structured-memory-v1/flash-path-diagnosis.json').read_text(encoding='utf-8'))
    detail_path=raw_root/'flash-path-diagnosis-details.json'
    if M.V5.V1.file_sha(detail_path)!=source_diag['details_sha256']:raise ValueError('Prior diagnostic changed.')
    details=json.loads(detail_path.read_text(encoding='utf-8'))
    if {r['id']:r['gold'] for r in details}!=gold:raise ValueError('Gold differs from prior diagnostic.')
    inputs['prior_path_coverage_details']=M.V5.V1.file_sha(detail_path)
    cells={'both_correct':0,'local_only':0,'flash_only':0,'both_wrong':0};records=[]
    for qid in sorted(gold):
        l,f=primary['local'][qid],primary['flash'][qid]
        cells['both_correct' if l and f else 'local_only' if l else 'flash_only' if f else 'both_wrong']+=1
        records.append({'id':qid,'local_primary_exact':l,'flash_primary_exact':f,
            'local_secondary_subem':M.subem(readers['local'][qid],gold[qid]),
            'flash_secondary_subem':M.subem(readers['flash'][qid],gold[qid])})
    discordant=cells['local_only']+cells['flash_only'];tail=min(cells['local_only'],cells['flash_only'])
    p=min(1.0,2*sum(comb(discordant,k) for k in range(tail+1))/2**discordant) if discordant else 1.0
    return {'n':100,'primary_exact':{label:sum(primary[label].values()) for label in primary},
        'secondary_upstream_subem':{label:sum(M.subem(value,gold[qid]) for qid,value in readers[label].items()) for label in readers},
        'paired_primary_cells':cells,'posthoc_exact_mcnemar_p':p,
        'posthoc_subem_any_enumerated_path_coverage':sum(r['gold_path_available'] for r in details),
        'input_sha256':inputs,'records':records,'new_model_calls':0,
        'limits':['Already-spent public development set; same one history and one locally derived graph.',
                  'Post-hoc p value assumes exchangeable question outcomes; shared history/development weakens inference. No equality or superiority proof.',
                  'Path-coverage diagnostic uses SubEM and bounded enumeration; it is not an exact-score or universal oracle upper bound.',
                  'Upstream published competitors use different models, ingestion, prompts, budgets and versions; this is not a matched leaderboard comparison.',
                  'The preserved graph predates exact-only capture repair; it is not a fresh end-to-end run of the repaired extractor.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['raw-root','gold-path','destination']:p.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());destination=args.pop('destination');result=compare(**args)
    M.P.write(destination,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['records','input_sha256']},indent=2))
