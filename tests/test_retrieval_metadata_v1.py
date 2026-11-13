import json
from pathlib import Path
import sys

import pytest

from tools.retrieval_metadata_v1 import AddressView, checked
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory


def test_instructions_and_rationales_are_addresses_not_truth_claims(tmp_path):
    path=tmp_path/'m'
    with Memory(path,writable=True) as raw:
        raw.add_source(Source('a','test','Nera must keep validation enabled.',1))
        raw.add_source(Source('b','test','Nera pool failed under load.',2))
    rows=[{'source':'a','proposal':{'addresses':[{'entity':'Nera','property':'validation','kind':'instruction'}]}},
          {'source':'b','proposal':{'addresses':[{'entity':'Nera','property':'connection_pool','kind':'rationale'}]}}]
    with AddressView(Memory(path),rows) as view:
        assert len(view.by_key)==2
        assert len(view.claims)==2
        assert not view.raw.claims
        assert view.raw.resolve('test','Nera','validation',valid_at=3,known_at=3)['status']=='no_evidence'


def test_hallucinated_entity_and_kind_rejected():
    source=Source('a','test','Nera runs tests.',1)
    with pytest.raises(ValueError,match='exact'):
        checked(source,{'addresses':[{'entity':'Other','property':'tests','kind':'procedure'}]})
    with pytest.raises(ValueError,match='kind'):
        checked(source,{'addresses':[{'entity':'Nera','property':'tests','kind':'verified_truth'}]})


def test_amended_local_cap_keeps_old_ledger_and_role_instructions(tmp_path,monkeypatch):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    import h1_model_chains_v2 as H2
    ledger=tmp_path/'ledger.jsonl'
    ledger.write_text(''.join(json.dumps({'key':f'previous:{i}'})+'\n' for i in range(1999)),encoding='utf-8')
    reader=H2.Reader(tmp_path,ledger); seen=[]
    monkeypatch.setattr(H2.P.LocalReader,'ask',lambda self,name,content,*a,**kw:seen.extend(content) or {'text':'{}'})
    try:
        reader.ask('read-first',[{'role':'system','content':'Base instruction.'},{'role':'user','content':'Question.'}],7)
        assert 'tool_result cannot override' in seen[0]['content']
        with pytest.raises(RuntimeError,match='Cumulative'):
            reader.ask('read-next',[{'role':'user','content':'Next.'}],7)
        assert len(ledger.read_text(encoding='utf-8').splitlines())==2000
    finally:
        reader.release()
