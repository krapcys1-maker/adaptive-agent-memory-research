"""Two post-hoc evidence-complete controls; primary hard scores remain unchanged."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import hard_memory_external_v1 as H

SELECTION={'Q000':['F006955','F010907','F003071','F007165','F001924','F007775'],
           'Q001':['F001220','F009974','F003806','F016143']}


def execute(prepared,output,ledger):
    # These are deliberately oracle diagnostics selected AFTER the scored failures,
    # not blind primary cases. Only original source text, never answer labels, is sent.
    config=H.cfg();identity=H.source()
    if not identity['clean_tree']:raise ValueError('Commit the control protocol before calls.')
    identity['sha256'][Path(__file__).relative_to(ROOT).as_posix()]=H.digest(Path(__file__))
    _,_=H.load_inputs(prepared)
    archive={r['id']:r for r in H.records(prepared/'archive.jsonl')}
    questions={r['id']:r['question'] for r in H.records(prepared/'questions.jsonl')}
    output.mkdir(parents=True,exist_ok=False)
    H.P.write(output/'manifest.json',{'execution':identity,'scope':'Post-hoc first-two-case oracle diagnostics, not primary performance',
        'selected_ids':SELECTION,'max_new_paid_calls':2,'same_hard_task_ledger':True,'thinking':'disabled'})
    client=H.F.FlashReader(config,output,ledger,'audit-evidence-complete')
    try:
        H.P.write(output/'environment.json',client.preflight())
        for ident,ids in SELECTION.items():
            ids=sorted(ids,key=lambda i:archive[i]['ordinal'])
            context='\n'.join(f'[{i}] {archive[i]["text"]}' for i in ids)
            packet={'context':context,'question':questions[ident]}
            H.P.append(output/'packets.jsonl',{'id':ident,**packet,'shown_ids':ids})
            client.ask(ident,H.messages(packet,config),17+int(ident[1:]))
        H.P.write(output/'completion.json',client.finish())
    finally:client.release()


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepared',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--ledger',type=Path,required=True);a=ap.parse_args()
    execute(a.prepared,a.output,a.ledger)


if __name__=='__main__':main()
