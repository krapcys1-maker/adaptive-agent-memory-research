"""Budget and replay regressions for the explicit amendment and offline CLI."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import structured_memory_pipeline_v2 as V2
from tools.structured_memory_cli_v1 import main
from tools.structured_memory_v1 import Memory


def test_cli_capture_and_restart_without_gold_or_credentials(tmp_path, capsys):
    store, source, proposal = [tmp_path/n for n in ['store','source.json','proposal.json']]
    source.write_text(json.dumps({'id':'a','scope':'fiction','text':'Mira lives in Koral.','recorded':1}), encoding='utf-8')
    proposal.write_text(json.dumps({'claims':[{'subject':'Mira','predicate':'lives_in','object':'Koral'}]}), encoding='utf-8')
    assert main(['--store',str(store),'source','--input',str(source)]) == 0
    assert main(['--store',str(store),'extract','--input',str(proposal),'--source-id','a']) == 0
    before = store.read_bytes()
    assert main(['--store',str(store),'resolve','--scope','fiction','--subject','Mira',
                 '--predicate','lives_in','--valid-at','3','--known-at','3']) == 0
    assert 'Koral' in capsys.readouterr().out
    assert before == store.read_bytes()


@pytest.mark.parametrize('override', [{'api_model':'deepseek-pro'}, {'api_reserved_cap_usd':2.01},
    {'max_calls':401}, {'api_url':'https://other.example'}, {'api_reservation_usd':0.001}])
def test_flash_amendment_guard_precedes_credentials(tmp_path, monkeypatch, override):
    cfg = json.loads((V2.V1.DATA/'config.json').read_text())
    cfg.update(api_reserved_cap_usd=2,max_calls=400)
    cfg.update(override)
    def forbidden():
        pytest.fail('Invalid request touched credentials')
    monkeypatch.setattr(V2.F.metered_proxy,'load_key',forbidden)
    with pytest.raises(ValueError):
        V2.FlashV2(cfg,tmp_path,tmp_path/'ledger','test')


def test_amended_ledger_keeps_all_earlier_reservations(tmp_path):
    cfg = json.loads((V2.V1.DATA/'config.json').read_text())
    ledger = V2.F.ReservationLedger(tmp_path/'ledger',cfg)
    ledger.reserve('v1:a')
    ledger.settle('v1:a',{'prompt_tokens':10,'completion_tokens':10})
    ledger.close()
    amended = dict(cfg,api_reserved_cap_usd=2,max_calls=400)
    ledger = V2.F.ReservationLedger(tmp_path/'ledger',amended)
    try:
        ledger.reserve('v2:b')
        assert ledger.summary()['reserved_calls'] == 2
        assert ledger.summary()['reserved_usd'] == .008
        assert ledger.summary()['unknown_usage_attempts'] == 1
        with pytest.raises(ValueError,match='already reserved'):
            ledger.reserve('v1:a')
    finally:
        ledger.close()


def test_visible_catalog_does_not_expose_other_scope(tmp_path):
    from tools.structured_memory_v1 import Source
    with Memory(tmp_path/'memory',writable=True) as memory:
        memory.add_source(Source('a','private','Mira uses Koral.',1))
        memory.extract('a',{'claims':[{'subject':'Mira','predicate':'secret_attribute','object':'Koral'}]})
        assert memory.visible_catalog('other',known_at=5) == set()
