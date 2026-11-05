from types import SimpleNamespace
import json
import pytest
from scripts import h1_chronological_pack_v1 as H


def test_ordering_preserves_duplicate_evidence_and_equal_day_order():
    sources={s:SimpleNamespace(recorded=t) for s,t in [('new',20),('old-b',2),('old-a',2)]}
    ids=['new','old-b','old-a','new']
    assert H.ordered(ids,sources)==['old-b','old-a','new','new']
    assert ids==['new','old-b','old-a','new']


def test_full_phase_guard_uses_retained_ledger(tmp_path):
    p=tmp_path/'ledger'
    p.write_text('\n'.join(json.dumps({'key':str(i)}) for i in range(2961)),encoding='utf-8')
    assert H.ledger_count(p)==2961
    with p.open('a',encoding='utf-8') as f:f.write('\n'+json.dumps({'key':'one-more'}))
    with pytest.raises(ValueError,match='Entire paired phase'):H.ledger_count(p)
