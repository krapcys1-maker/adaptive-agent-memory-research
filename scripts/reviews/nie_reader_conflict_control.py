"""One post-pilot conflict-coverage control; no primary rerun or threshold change."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nie_reader_pilot as P
import nie_memory_contract as C


def run(output, client_factory=P.LocalReader, require_clean=True):
    config=json.loads((P.DATA/'config-v2.json').read_text(encoding='utf-8'))
    config['max_calls']=1
    config['max_seconds']=180
    cases=json.loads((P.DATA/'cases.json').read_text(encoding='utf-8'))
    P.validate(config,cases)
    source=P.source_identity()
    if require_clean and not source['clean_tree']:
        raise ValueError('Commit the control source first.')
    output.mkdir(parents=True,exist_ok=False)
    control_path=Path(__file__)
    P.write(output/'manifest.json',{'execution':source,'config':config,
        'control_sha256':P.hashlib.sha256(control_path.read_bytes()).hexdigest(),
        'scope':'Post-result control coverage repair; separate from primary arm counts.'})
    case=cases[0]
    rows=[P.journal_row(case,case['values'][0],'conflict-left'),
          P.journal_row(case,case['values'][1],'conflict-right')]
    rows += [P.journal_row(other,other['values'][0],'distractor:'+other['slot']) for other in cases[1:]]
    replay=P.retrieve(config,case,case['direct'],rows,'V','unused')
    checked=C.guard_answer(case['slot'],'{"value":"UNKNOWN"}',replay['shown_items'])
    if checked['resolution']!='conflicting_evidence' or len(checked['source_ids'])!=2:
        P.write(output/'uninformative.json',{'guard':checked,'replay':replay})
        raise RuntimeError('Control still lacks two shown conflicting records; no model call.')
    client=client_factory(config,output)
    try:
        P.write(output/'local-environment.json',client.preflight())
        response=client.ask('supplemental-conflict',P.reader_messages(config,case['slot'],case['direct'],replay,[]),7)
        guard=C.guard_answer(case['slot'],response['text'],replay['shown_items'])
        finish=client.finish()
        result={'complete':True,'generation_calls':finish['generation_calls'],'replay':replay,
                'raw_value':P.answer_value(response),'guard':guard,
                'conflict_exercised':guard['resolution']=='conflicting_evidence',
                'delivered_unknown':guard['value']=='UNKNOWN'}
        if P.source_identity()['sha256']!=source['sha256']:
            raise RuntimeError('Sources changed during control.')
        P.write(output/'result.json',result)
        return result
    finally:
        client.release()


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    result=run(args.output)
    print(json.dumps({k:result[k] for k in ['complete','generation_calls','conflict_exercised','delivered_unknown']}))
