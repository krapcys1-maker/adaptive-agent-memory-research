"""Extend frozen metadata/source-role replay with actual query-router proofs."""
import argparse
import json
from pathlib import Path

import audit_h1_model_chains_v2 as A
import h1_query_routing_v4 as V4
import h1_model_chains_v1 as H
import nie_reader_pilot as P


def audit(history,questions,store,capture,answers,scope,projection):
    queries=P.read_rows(questions)
    routing=P.read_rows(answers/'routing.jsonl')
    routes={r['id']:r for r in routing}
    requests={r['key']:r['request'] for r in P.read_rows(answers/'attempts.jsonl')}
    responses={r['key']:r['text'] for r in P.read_rows(answers/'responses.jsonl')}
    failures=[]; cursor=[0]; calls=[0]
    def check(condition,message):
        if not condition: failures.append(message)
    check(len(routing)==len(queries) and set(routes)=={f'Q{i:06d}' for i in range(len(queries))},'route roster')
    roles={r['source']:r['channel'] for r in P.read_rows(capture/'source-roles.jsonl')}
    original=H.packs
    def replay(view,actual_scope,question,day,mk):
        i=cursor[0]; cursor[0]+=1; qid=f'Q{i:06d}'
        check(queries[i]['question']==question and queries[i]['asked_on_day']==day,'query order differs')
        base=original(view,actual_scope,question,day,mk)['base']
        choices=V4.catalog(view,actual_scope,question,day,base['ids'])
        row=routes[qid]; plan={'entity':'UNKNOWN','properties':[]}
        if choices:
            call='route-'+qid; calls[0]+=1
            check(requests[call]['messages']==V4.route_messages(question,choices),'router input differs')
            try: plan=json.loads(responses[call])
            except (ValueError,TypeError): plan={}
        selected=V4.selected_sources(view,actual_scope,plan,day,choices)
        check(row['choices']==choices and row['plan']==plan and row['selected_ids']==selected,
              'route is not derived from recorded model/visible metadata: '+qid)
        check(row['fallback_to_base']==(not selected),'hidden route fallback')
        return {'base':V4.pack(view,roles,base['ids']),
                'chains':V4.pack(view,roles,selected if selected else base['ids'])}
    H.packs=replay
    try:
        result=A.audit(history,questions,store,capture,answers,scope,projection)
    finally:
        H.packs=original
    result['failures'].extend(failures)
    result['query_router_outputs_reconstructed']=calls[0]
    result['question_routing_used_no_gold_or_supplied_cue']=True
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ['history','questions','store','capture','projection','answers','output']:
        p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--scope',required=True)
    args=vars(p.parse_args()); output=args.pop('output'); result=audit(**args)
    P.write(output,result); print(json.dumps(result,indent=2)); raise SystemExit(bool(result['failures']))
