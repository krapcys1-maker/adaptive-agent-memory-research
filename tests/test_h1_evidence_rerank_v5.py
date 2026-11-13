from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import h1_evidence_rerank_v5 as V5


def test_no_pro_before_credentials_or_ledger(tmp_path,monkeypatch):
    original=V5.R.settings()
    monkeypatch.setattr(V5.R,'settings',lambda:dict(original,api_model='deepseek-pro'))
    monkeypatch.setattr(V5.F.metered_proxy,'load_key',lambda:pytest.fail('Unauthorized credential access'))
    with pytest.raises(ValueError): V5.Flash(tmp_path,tmp_path/'ledger')
    assert not list(tmp_path.iterdir())


def test_unsettled_paid_attempt_stops_before_network(tmp_path,monkeypatch):
    monkeypatch.setattr(V5.F.metered_proxy,'load_key',lambda:'test-only-value')
    reader=V5.Flash(tmp_path,tmp_path/'ledger')
    reader.request=lambda *a,**kw:pytest.fail('Unsettled usage touched network')
    try:
        reader.ledger.reserve('earlier:unknown')
        with pytest.raises(RuntimeError,match='Unsettled'): reader.preflight()
        assert reader.ledger.summary()['reserved_usd']==.004
    finally:
        reader.release()
