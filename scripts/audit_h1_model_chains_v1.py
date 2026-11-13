"""Gold-free replay of H1 extraction provenance and matched reader inputs."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

import h1_model_chains_v1 as H
import nie_reader_pilot as P
from tools.structured_memory_v2 import Memory


def audit(history,questions,store,capture,answers,scope):
    failures=[]
    def check(condition,message):
        if not condition: failures.append(message)
    raw=P.read_rows(history); queries=P.read_rows(questions)
    captures=P.read_rows(capture/'captures.jsonl')
    with Memory(store) as m:
        check(len(m.sources)==len(raw),'source count')
        for i,row in enumerate(raw):
            s=m.sources[f'E{i:06d}']
            check(s.text==row['text'] and s.recorded==row['day'] and s.scope==scope,'raw source mismatch')
        check(len(captures)==len(raw) and len({r['id'] for r in captures})==len(raw),'capture roster')
        proposals={}; model_rows={r['key']:r for r in P.read_rows(capture/'responses.jsonl')}
        with tempfile.TemporaryDirectory() as temp:
            with Memory(Path(temp)/'never-created') as replay:
                for row in P.read_rows(store):
                    event=row['event']
                    if event['kind']=='extract':
                        sid=event['source']; proposal=event['proposal']; reuse=proposal.get('derivation')
                        if reuse:
                            prior=reuse.get('source')
                            check(reuse.get('kind')=='exact_text_reuse' and prior in proposals,'invalid reuse source')
                            check(m.sources[sid].text==m.sources[prior].text and
                                  proposal['claims']==proposals[prior]['claims'],'reuse differs from literal source/proposal')
                        elif event['method']=='template':
                            cached=replay.cached(sid)
                            expected=None if cached is None else [{k:v for k,v in asdict(cached).items() if k!='source'}]
                            check(proposal['claims']==expected,'non-causal learned shell: '+sid)
                        else:
                            response=model_rows.get('extract-'+sid)
                            check(response is not None and json.loads(response['text'])==proposal,'model proposal mismatch: '+sid)
                        proposals[sid]=proposal
                    replay._apply(event)
        for directory in [capture,answers]:
            frozen=json.loads((directory/'raw-freeze.json').read_text(encoding='utf-8'))
            check(all(H.S.file_sha(directory/name)==sha for name,sha in frozen['files_sha256'].items()),'raw hash drift')
            attempts=P.read_rows(directory/'attempts.jsonl'); responses=P.read_rows(directory/'responses.jsonl')
            check(len(attempts)==len(responses) and len({r['key'] for r in attempts})==len(attempts) and
                  {r['key'] for r in attempts}=={r['key'] for r in responses},'call coverage')
            check(all(P.sha(r['request'])==r['request_sha256'] for r in attempts),'request checksum')
            controls=P.read_rows(directory/'controls.jsonl')
            check(len(controls)==3 and all(c['correct'] for c in controls),'transport controls')
        outputs=P.read_rows(answers/'answers.jsonl')
        check(len(outputs)==2*len(queries) and {(r['id'],r['arm']) for r in outputs}==
              {(f'Q{i:06d}',arm) for i in range(len(queries)) for arm in ['base','chains']},'reader roster')
        requests={r['key']:r['request'] for r in P.read_rows(answers/'attempts.jsonl')}
        responses={r['key']:r['text'] for r in P.read_rows(answers/'responses.jsonl')}
        by_key={(r['id'],r['arm']):r for r in outputs}
        mk=P.bridge.load_kernel()
        for i,q in enumerate(queries):
            packs=H.packs(m,scope,q['question'],q['asked_on_day'],mk)
            for arm,pack in packs.items():
                row=by_key[(f'Q{i:06d}',arm)]; call=f'read-{arm}-Q{i:06d}'
                check(row['shown_ids']==pack['ids'] and row['context_sha256']==P.sha(pack['context']),'context reconstruction')
                check(requests[call]['messages'][1]['content']==pack['context']+'\nQuestion: '+q['question'],'reader input differs')
                try: value=json.loads(responses[call]).get('answer')
                except (TypeError,json.JSONDecodeError): value=None
                check(value==row['answer'],'reader output differs')
                check(all(m.sources[s].recorded<=q['asked_on_day'] for s in pack['ids']),'future source shown')
                check(len(pack['ids'])<=3 and len(pack['context'].encode())<=4500,'unequal/exceeded pack budget')
        return {'failures':failures,'sources':len(raw),'claims':len(m.claims),'reader_outputs':len(outputs),
                'exact_reuse_proofs':sum(bool(p.get('derivation')) for p in proposals.values()),
                'canonical_store_sha256':H.S.file_sha(store),'construction_labels_read':False,
                'semantic_extraction_accuracy':'not established by this mechanical audit'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['history','questions','store','capture','answers','output']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--scope',required=True)
    args=vars(p.parse_args()); output=args.pop('output')
    result=audit(**args); P.write(output,result)
    print(json.dumps(result,indent=2))
    return bool(result['failures'])


if __name__=='__main__':
    raise SystemExit(main())
