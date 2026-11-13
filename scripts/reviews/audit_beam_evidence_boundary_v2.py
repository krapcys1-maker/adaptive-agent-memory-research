"""Full packet/coverage reconstruction of the offline evidence diagnostic."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import beam_evidence_boundary_v2 as E
A = E.A


def audit(prepared, access, reader, review, legacy, beam_ledger, output):
    started = time.monotonic(); manifest = E.load(output / 'manifest.json'); source = manifest['source']
    if not source['clean_tree'] or E.load(output / 'started.json')['source'] != source:
        raise ValueError('Unfrozen diagnostic source.')
    for name, h in source['sha256'].items():
        p = Path(name)
        if p.is_absolute() or '..' in p.parts: raise ValueError('Invalid source path.')
        original = subprocess.check_output(['git', 'show', source['head'] + ':' + p.as_posix()], cwd=ROOT)
        if hashlib.sha256(original).hexdigest() != h or A.sha(ROOT / p) != h:
            raise ValueError('Executed source differs from working/committed bytes.')
    for name, h in manifest['output_sha256'].items():
        if Path(name).name != name or A.sha(output / name) != h: raise ValueError('Diagnostic output hash changed.')
    paths = (prepared, access, reader, review, legacy, beam_ledger)
    before = E.inputs(*paths)
    if before != manifest['input_sha256']: raise ValueError('Frozen inputs/old ledgers differ.')
    E.validate_inputs(prepared, access, reader, review)
    cases, packets, details, result = E.analyze(prepared, access, reader, review, started=started)
    for name, reconstructed in [('cases.jsonl', cases), ('context-packets.jsonl', packets), ('target-details.jsonl', details)]:
        if list(A.rows(output / name)) != reconstructed: raise ValueError('Reconstructed ' + name + ' differs.')
    if result != manifest['result'] or len(cases) != 200 or len(packets) != 200:
        raise ValueError('Full result/roster differs.')
    if E.inputs(*paths) != before: raise ValueError('Inputs/ledgers changed during replay.')
    return {'failures': [], 'source_head': source['head'], 'cases_reconstructed': len(cases),
        'context_packets_reconstructed': len(packets), 'annotation_slots_reconstructed': len(details),
        'original_source_messages_checked': result['complete_source_messages'],
        'full_source_contexts_verified': True, 'complete_message_budgets_hold': all(max(p['packet']['message_bytes'].values()) <= 6000 for p in packets),
        'source_inputs_and_old_ledgers_unchanged': True, 'new_model_calls': 0,
        'manifest_sha256': A.sha(output / 'manifest.json'), 'audit_seconds': time.monotonic() - started,
        'claim': 'Authored deterministic replay, not independent semantic sufficiency or observed-event validation.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['prepared', 'access', 'reader', 'review', 'legacy', 'beam-ledger', 'output', 'destination']:
        p.add_argument('--' + name, type=Path, required=True)
    args = vars(p.parse_args()); destination = args.pop('destination'); report = audit(**args)
    A.write(destination, report); print(E.json.dumps(report, indent=2))
