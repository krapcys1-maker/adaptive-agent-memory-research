"""Rebuild the matched comparison report without model calls or a model judge."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics

import audit_reader_model_compare_v1 as A

R,P,C=A.R,A.P,A.C


def report():
    cohort,cases,gold=R.reference();base=R.DATA
    reference={r['call_key']:dict(r,key=r['call_key']) for r in P.read_rows(R.REFERENCE/'turns.jsonl')}
    reference_answers={r['key']:r for r in P.read_rows(R.REFERENCE/'responses.jsonl')}
    compared={};inputs=[Path(__file__)]
    for backend in ('local14b','flash'):
        output=base/'runs'/backend;audit=A.audit(output)
        if not audit['passed']:raise ValueError('Stored run failed reconstruction: '+backend)
        turns=P.read_rows(output/'turns.jsonl');responses=P.read_rows(output/'responses.jsonl')
        matched=0
        for turn in turns:
            old=reference[turn['key']]
            if all(turn[k]==old[k] for k in ('question','slot','seed','arm','turn')) and all(
                turn['replay'][k]==old['replay'][k] for k in ('context','shown_items','kernel_ranked_ids')):matched+=1
        if matched!=192:raise ValueError('Reference contexts or questions differ.')
        completion=json.loads((output/'completion.json').read_text(encoding='utf-8'))
        timings=[r['wall_seconds'] for r in responses]
        counters=('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens') if backend=='flash' else ('prompt_eval_count','eval_count')
        compared[backend]={'audit':audit,'reference_matched_contexts_and_questions':matched,
            'arms':json.loads((output/'summary.json').read_text(encoding='utf-8'))['arms'],
            'controls_passed':8,'elapsed_seconds':completion.get('seconds',completion.get('elapsed_seconds')),
            'call_wall_seconds':{'sum':sum(timings),'median':statistics.median(timings),'max':max(timings)},
            'token_usage':{k:sum(r['usage'].get(k,0) or 0 for r in responses) for k in counters}}
        if backend=='flash':compared[backend]['budget']=completion['budget']
        inputs.extend(sorted(output.glob('*.json*')))
    # Independently recompute the old primary endpoint from final raw answers and shown evidence.
    old_arms={}
    for arm in ('N','K','O','V'):
        rows=[r for r in reference.values() if r['arm']==arm];raw_ok=0;emitted_ok=0
        for row in rows:
            response=reference_answers[row['key']];raw=P.answer_value(response)
            emitted=C.guard_answer(row['slot'],response['text'] if response.get('done_reason')!='length' else '',row['replay']['shown_items'])['value'] if arm=='V' else raw
            if raw!=row['raw_value'] or emitted!=row['delivered_value']:raise ValueError('Reference answer accounting differs.')
            raw_ok+=P.agreement(raw,gold[(row['slot'],row['seed'])]);emitted_ok+=P.agreement(emitted,gold[(row['slot'],row['seed'])])
        old_arms[arm]={'raw_agreement':raw_ok,'delivered_agreement':emitted_ok,'n_turns':len(rows)}
    inputs.extend([R.REFERENCE/'turns.jsonl',R.REFERENCE/'responses.jsonl',R.REFERENCE/'journals.jsonl',R.REFERENCE/'writers.jsonl',base/'api-spend-ledger.jsonl'])
    ledger=R.F.ReservationLedger(base/'api-spend-ledger.jsonl',R.settings())
    try:budget=ledger.summary()
    finally:ledger.close()
    if budget['reserved_calls']!=200 or budget['unknown_usage_attempts']!=0:raise ValueError('API spend ledger incomplete.')
    if budget!=compared['flash']['budget']:raise ValueError('API summary differs from cumulative ledger.')
    return {'new_generation_calls':400,'new_model_planning_calls':0,'n_semantic_cases':8,'n_persisted_chains':16,
        'reference_7b_recomputed':old_arms,'readers':compared,'api_budget_rechecked':budget,
        'sha256':{p.relative_to(R.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'decision':'Prefer the adequate local reader for this bounded typed task. Keep Flash as a transfer check. Next address text-to-slot routing and typed capture, not a reader-size substitution or a universal retrieval threshold.',
        'limits':['Eight authored fields; both writer seeds chose the same value per field.',
                  'Questions and evidence match; histories after model answers differ by design.',
                  'No actual NIE prompts, automatic slot inference, free-prose extraction, revision/card-conflict resolution or production benefit measured.',
                  'Repeated canaries are a small check, not a service determinism guarantee.']}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);args=ap.parse_args()
    result=report()
    if args.output:P.write(args.output,result)
    else:print(json.dumps(result,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
