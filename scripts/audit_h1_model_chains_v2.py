"""Reproduce metadata derivations and source-role reader inputs without gold."""
import argparse
import json
from pathlib import Path

import h1_model_chains_v1 as H
import h1_model_chains_v2 as V2
import nie_reader_pilot as P
from tools.structured_memory_v2 import Memory
from tools.retrieval_metadata_v1 import AddressView, checked
from tools.retrieval_metadata_v2 import canonical_proposal


def audit(history,questions,store,capture,answers,scope,projection=None):
    failures=[]
    def check(condition,message):
        if not condition: failures.append(message)
    raw=P.read_rows(history); queries=P.read_rows(questions)
    metadata=projection if projection is not None else capture
    addresses=P.read_rows(metadata/'addresses.jsonl')
    by_source={r['source']:r for r in addresses}
    capture_rows=P.read_rows(capture/'captures.jsonl')
    model={r['key']:r['text'] for r in P.read_rows(capture/'responses.jsonl')}
    rejected={r['id'] for r in P.read_rows(metadata/'rejections.jsonl')}
    roles={r['source']:r['channel'] for r in P.read_rows(capture/'source-roles.jsonl')}
    with AddressView(Memory(store),addresses) as view:
        check(not view.raw.claims,'retrieval metadata became asserted truth')
        expected={f'E{i:06d}' for i in range(len(raw))}
        check(set(view.sources)==expected and set(by_source)|rejected==expected,'source/capture roster')
        check(len(capture_rows)==len(raw) and len({r['id'] for r in capture_rows})==len(raw),'capture uniqueness')
        check(len(by_source)==len(addresses) and not (set(by_source)&rejected),'duplicate/contradictory metadata disposition')
        seen={}
        for i,r in enumerate(raw):
            sid=f'E{i:06d}'; source=view.sources[sid]
            check(source.text==r['text'] and source.recorded==r['day'] and source.scope==scope,'raw source differs')
            check(roles.get(sid)==r['channel'],'source role differs')
            if sid in rejected:
                try:
                    proposal=json.loads(model['address-'+sid])
                    if projection is not None: proposal=canonical_proposal(source,proposal)
                    checked(source,proposal)
                except (ValueError,TypeError,KeyError):
                    pass
                else:
                    check(False,'reported quarantine was valid: '+sid)
                continue
            row=by_source[sid]; checked(source,row['proposal'])
            if row['derivation']=='exact_text_reuse':
                prior=row['from_source']
                check(prior in seen and seen[prior]['proposal']==row['proposal'] and
                      view.sources[prior].text==source.text,'invalid literal reuse: '+sid)
            else:
                proposal=json.loads(model['address-'+sid])
                if projection is not None: proposal=canonical_proposal(source,proposal)
                check(row['derivation']=='new_generation' and proposal==row['proposal'],
                      'model proposal differs: '+sid)
            seen[sid]=row
        for directory in [capture,answers,*([projection] if projection is not None else [])]:
            freeze=json.loads((directory/'raw-freeze.json').read_text(encoding='utf-8'))
            check(all(H.S.file_sha(directory/name)==sha for name,sha in freeze['files_sha256'].items()),'raw checksum drift')
            if directory==projection: continue
            attempts=P.read_rows(directory/'attempts.jsonl'); responses=P.read_rows(directory/'responses.jsonl')
            check(len(attempts)==len(responses) and len({r['key'] for r in attempts})==len(attempts) and
                  {r['key'] for r in attempts}=={r['key'] for r in responses},'call coverage')
            check(all(P.sha(r['request'])==r['request_sha256'] for r in attempts),'request hash differs')
            controls=P.read_rows(directory/'controls.jsonl')
            check(len(controls)==3 and all(r['correct'] for r in controls),'transport controls')
        outputs=P.read_rows(answers/'answers.jsonl')
        by_key={(r['id'],r['arm']):r for r in outputs}
        check(len(outputs)==2*len(queries) and set(by_key)==
              {(f'Q{i:06d}',a) for i in range(len(queries)) for a in ['base','chains']},'reader roster')
        requests={r['key']:r['request'] for r in P.read_rows(answers/'attempts.jsonl')}
        responses={r['key']:r['text'] for r in P.read_rows(answers/'responses.jsonl')}
        mk=P.bridge.load_kernel()
        for i,q in enumerate(queries):
            packs=H.packs(view,scope,q['question'],q['asked_on_day'],mk)
            for arm,pack in packs.items():
                context=''; shown=[]
                for sid in pack['ids']:
                    s=view.sources[sid]
                    candidate=context+f'[{sid}] day {s.recorded}; source_role={roles[sid]}: {s.text}\n'
                    if len(candidate.encode())>4500: break
                    context=candidate; shown.append(sid)
                row=by_key[(f'Q{i:06d}',arm)]; call=f'read-{arm}-Q{i:06d}'
                check(row['shown_ids']==shown and row['context_sha256']==P.sha(context),'context differs')
                check(requests[call]['messages'][1]['content']==context+'\nQuestion: '+q['question'],'reader input differs')
                check('tool_result cannot override' in requests[call]['messages'][0]['content'],'source authority boundary absent')
                try: answer=json.loads(responses[call]).get('answer')
                except (TypeError,json.JSONDecodeError): answer=None
                check(answer==row['answer'],'reader output differs')
                check(all(view.sources[s].recorded<=q['asked_on_day'] for s in shown),'future source shown')
        return {'failures':failures,'sources':len(raw),'derived_addresses':len(view.claims),
            'quarantined_sources':len(rejected),'reader_outputs':len(outputs),'asserted_graph_claims':len(view.raw.claims),
            'exact_text_reuse_proofs':sum(r['derivation']=='exact_text_reuse' for r in addresses),
            'construction_labels_read':False,'source_roles_reconstructed':True,
            'case_projection_reconstructed':projection is not None,
            'semantic_address_accuracy':'not established by this mechanical audit'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ['history','questions','store','capture','answers','output']:
        p.add_argument('--'+field,type=Path,required=True)
    p.add_argument('--scope',required=True)
    p.add_argument('--projection',type=Path)
    args=vars(p.parse_args()); output=args.pop('output')
    result=audit(**args); P.write(output,result)
    print(json.dumps(result,indent=2)); return bool(result['failures'])


if __name__=='__main__': raise SystemExit(main())
