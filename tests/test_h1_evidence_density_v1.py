"""Declared repetition identity and retained whole-phase resource guard."""
import json
import pytest
from scripts import h1_evidence_density_v1 as D


def test_duplicate_is_the_same_source_not_fake_corroboration():
    rows=D.conditions('new','old')
    assert rows['stale_repeat_first']==['new','old','old']
    assert rows['stale_repeat_last']==['old','old','new']
    assert rows['correction_repeat_first']==['new','new','old']
    assert rows['correction_repeat_last']==['old','new','new']
    assert all(len(r)==3 and set(r)<= {'old','new','CONTROL_NEUTRAL'} for r in rows.values())
    with pytest.raises(ValueError):D.conditions('same','same')


def test_retain_prior_attempts_and_require_whole_phase_room(tmp_path):
    p=tmp_path/'ledger';p.write_text('\n'.join(json.dumps({'key':str(i)}) for i in range(3153)),encoding='utf-8')
    assert D.ledger_count(p)==3153
    with p.open('a',encoding='utf-8') as f:f.write('\n'+json.dumps({'key':'extra'}))
    with pytest.raises(ValueError,match='cap3300'):D.ledger_count(p)
