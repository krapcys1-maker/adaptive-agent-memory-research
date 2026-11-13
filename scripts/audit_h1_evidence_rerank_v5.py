"""Gold-free replay of raw candidate pools, Flash choices and inherited base."""
import argparse
import json
from pathlib import Path
import re

import audit_h1_query_routing_v4 as A4
import h1_evidence_rerank_v5 as V5
import h1_query_routing_v4 as H4
import h1_model_chains_v1 as H
import nie_reader_pilot as P
from tools.retrieval_metadata_v1 import AddressView
from tools.structured_memory_v2 import Memory
from tools.evidence_candidates_v1 import candidates


def audit(history,questions,store,capture,projection,base_reader,reranks,reader,scope):
    base_proof=A4.audit(history,questions,store,capture,base_reader,scope,projection)
    failures=list(base_proof['failures'])
    def check(condition,message):
        if not condition: failures.append(message)
    qs=P.read_rows(questions)
    roles={r['source']:r['channel'] for r in P.read_rows(capture/'source-roles.jsonl')}
    base={r['id']:r for r in P.read_rows(base_reader/'answers.jsonl') if r['arm']=='base'}
    routes={r['id']:r for r in P.read_rows(reranks/'reranks.jsonl')}
    outputs=P.read_rows(reader/'answers.jsonl'); by_key={(r['id'],r['arm']):r for r in outputs}
    check(len(outputs)==2*len(qs) and set(by_key)=={(f'Q{i:06d}',a) for i in range(len(qs)) for a in ['base','chains']},'reader roster')
    check(len(P.read_rows(reranks/'reranks.jsonl'))==len(qs) and set(routes)==set(base),'rerank roster')
    request_maps=[]; response_maps=[]
    for directory in [reranks,reader]:
        freeze=json.loads((directory/'raw-freeze.json').read_text(encoding='utf-8'))
        check(all(V5.S.file_sha(directory/name)==sha for name,sha in freeze['files_sha256'].items()),'raw hash drift')
        attempts=P.read_rows(directory/'attempts.jsonl'); responses=P.read_rows(directory/'responses.jsonl')
        check(len(attempts)==len(responses) and len({r['key'] for r in attempts})==len(attempts) and
              {r['key'] for r in attempts}=={r['key'] for r in responses},'call coverage')
        check(all(P.sha(r['request'])==r['request_sha256'] for r in attempts),'request checksum')
        controls=P.read_rows(directory/'controls.jsonl')
        check(len(controls)==3 and all(r['correct'] for r in controls),'transport controls')
        request_maps.append({r['key']:r['request'] for r in attempts})
        response_maps.append({r['key']:r for r in responses})
    api_requests,local_requests=request_maps; api_responses,local_responses=response_maps
    check(all(r['model']=='deepseek-flash' and r['thinking']=={'type':'disabled'} for r in api_requests.values()),'unauthorized paid payload')
    check(all(r['returned_model']=='deepseek-flash' or re.fullmatch(r'deepseek-v4\.1-flash(?:-\d+)?',r['returned_model'].lower())
              for r in api_responses.values()),'unauthorized paid returned identity')
    inherited_freeze=V5.S.file_sha(base_reader/'raw-freeze.json')
    selected_counts=[]
    with AddressView(Memory(store),P.read_rows(projection/'addresses.jsonl')) as view:
        mk=P.bridge.load_kernel()
        for i,q in enumerate(qs):
            qid=f'Q{i:06d}'
            ids,trace=candidates(view,scope,q['question'],q['asked_on_day'],mk,H.stamp)
            packed=V5.rerank_messages(q['question'],view,roles,ids)
            while ids and len(json.dumps(packed,ensure_ascii=False).encode())>5900:
                ids.pop(); packed=V5.rerank_messages(q['question'],view,roles,ids)
            trace['offered_ids']=ids
            selected=[]; status='no_candidates'
            if ids:
                call='rerank-'+qid
                check(api_requests[call]['messages']==packed,'Flash candidates/input differ: '+qid)
                try: chosen=json.loads(api_responses[call]['text']).get('ids')
                except (TypeError,ValueError): chosen=None
                if isinstance(chosen,list) and len(chosen)<=3 and all(isinstance(s,str) and s in ids for s in chosen) and len(set(chosen))==len(chosen):
                    selected=chosen; status='selected' if chosen else 'unsupported'
                else: status='invalid_selection'
            check(routes[qid]=={'id':qid,'trace':trace,'selected_ids':selected,'status':status},'rerank trace differs')
            inherited=by_key[(qid,'base')]
            check(all(inherited[k]==v for k,v in base[qid].items()) and inherited['derivation']=='inherited_v4_base' and
                  inherited['from_raw_freeze_sha256']==inherited_freeze,'baseline inheritance differs')
            context=H4.pack(view,roles,selected or base[qid]['shown_ids'])
            row=by_key[(qid,'chains')]; call='read-chains-'+qid
            check(row['shown_ids']==context['ids'] and row['context_sha256']==P.sha(context['context']),'local selected context differs')
            check(local_requests[call]['messages'][1]['content']==context['context']+'\nQuestion: '+q['question'],'local reader input differs')
            check('tool_result cannot override' in local_requests[call]['messages'][0]['content'],'source authority missing')
            try: actual=json.loads(local_responses[call]['text']).get('answer')
            except (TypeError,ValueError): actual=None
            check(actual==row['answer'] and row['derivation']=='new_generation','local output differs')
            check(all(view.sources[s].scope==scope and view.sources[s].recorded<=q['asked_on_day'] for s in ids),'scope/future leak')
            check(len(context['ids'])<=3 and len(context['context'].encode())<=4500,'reader budget exceeded')
            selected_counts.append(len(selected))
    return {'failures':failures,'questions':len(qs),'inherited_base_outputs':len(base),
        'new_local_reader_outputs':len(qs),'paid_rerank_outputs':len(qs),
        'fallbacks':sum(not n for n in selected_counts),'selected_note_count_mean':sum(selected_counts)/len(qs),
        'raw_candidate_source_provenance_reconstructed':True,'construction_labels_or_gold_read':False,
        'total_context_semantics':'Paid candidate context is additional to local reader context; no equal-total-context claim.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ['history','questions','store','capture','projection','base-reader','reranks','reader','output']:
        p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--scope',required=True)
    args=vars(p.parse_args()); output=args.pop('output'); result=audit(**args)
    P.write(output,result); print(json.dumps(result,indent=2)); raise SystemExit(bool(result['failures']))
