"""Local-only positive-control amendment; primary benchmark packets stay identical."""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path

import hard_memory_external_v1 as H


def control_messages(config,index):
    cohort=json.loads((H.R.REFERENCE/'manifest.json').read_text(encoding='utf-8'))['config']
    if cohort['positive_controls']!=config['positive_controls']:raise ValueError('Control values changed.')
    token=config['positive_controls'][index]
    return H.P.reader_messages(cohort,'control_value','What is the control_value?',{'context':f'The control_value is {token}.'},[])


class Reader(H.P.LocalReader):
    def ask(self,key,messages,seed,**kwargs):
        if key.startswith('positive-'):
            messages=control_messages(H.cfg(),int(key.split('-')[1]));seed=7
        return super().ask(key,messages,seed,**kwargs)


def run(prepared,output,failed):
    config=H.cfg();prior=H.records(failed/'attempts.jsonl')
    failure_manifest=json.loads((failed/'manifest.json').read_text(encoding='utf-8'))
    if [r['key'] for r in prior]!=['positive-0'] or (failed/'answers.jsonl').exists():
        raise ValueError('Amendment is only for the one-control failure before any primary question.')
    elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(failure_manifest['started_at'])).total_seconds()
    remaining=config['max_seconds']-elapsed
    if remaining<=0:raise RuntimeError('Original local wall-clock budget exhausted.')
    source_hash=H.digest(Path(__file__))
    def factory(cfg,out):
        local=dict(H.R.local_config(cfg),max_calls=cfg['local_max_calls']-len(prior),max_seconds=remaining)
        return Reader(local,out)
    complete=H.run(prepared,output,'local14b',output.parent/'api-ledger.jsonl',factory=factory)
    if H.digest(Path(__file__))!=source_hash:raise RuntimeError('Control amendment changed during execution.')
    H.P.write(output/'control-amendment.json',{'scope':'Positive-control messages/seed only; all primary packets/settings unchanged.',
        'previous_attempts':len(prior),'previous_primary_calls':0,'remaining_local_calls':config['local_max_calls']-len(prior),
        'remaining_original_wall_seconds':remaining,'source_sha256':source_hash,'prior_response_sha256':H.digest(failed/'responses.jsonl')})
    return complete


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepared',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--failed',type=Path,required=True);args=ap.parse_args()
    return 0 if run(args.prepared,args.output,args.failed) else 1


if __name__=='__main__':raise SystemExit(main())
