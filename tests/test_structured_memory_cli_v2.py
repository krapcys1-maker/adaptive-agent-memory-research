"""Actual CLI source/extraction/replay/packet round trip, without providers."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_cli_persists_exact_replay_then_builds_a_read_only_packet(tmp_path):
    store = tmp_path/'memory'
    def run(*args):
        p = subprocess.run([sys.executable, 'tools/structured_memory_cli_v2.py', '--store', str(store), *args],
            cwd=ROOT, capture_output=True, check=True)
        return json.loads(p.stdout)
    def file(name, value):
        p = tmp_path/name; p.write_text(json.dumps(value), encoding='utf-8'); return str(p)
    run('source', '--input', file('source.json', {'id': 'seed', 'scope': 'public', 'text': 'Mira lives in Koral.', 'recorded': 1}))
    run('extract', '--source-id', 'seed', '--input', file('proposal.json', {'claims': [{'subject': 'Mira', 'predicate': 'lives_in', 'object': 'Koral'}]}), '--learn')
    run('source', '--input', file('repeat.json', {'id': 'repeat', 'scope': 'public', 'text': 'Mira lives in Koral.', 'recorded': 2}))
    assert run('cache', '--source-id', 'repeat')['derived_from'] == ['seed']
    replay = run('replay', '--source-id', 'repeat')
    assert replay['persisted'][0]['source'] == replay['claim']['source'] == 'repeat'
    before = store.read_bytes()
    packet = run('packet', '--scope', 'public', '--valid-at', '2', '--known-at', '2', '--question', 'Where does Mira live?')
    assert packet['plans'][0]['steps'] == [{'predicate': 'lives_in', 'direction': 'out'}]
    assert 'Koral' not in packet['messages'][1]['content']
    assert store.read_bytes() == before
