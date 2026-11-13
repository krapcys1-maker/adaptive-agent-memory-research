import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import h1_model_chains_v1 as H
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory


def put(m,sid,text,p,value,day):
    m.add_source(Source(sid,'test',text,day))
    m.extract(sid,{'claims':[{'subject':'Mira','predicate':p,'object':value}]})


def test_chain_promotion_keeps_two_properties_and_excludes_unavailable_source(tmp_path):
    with Memory(tmp_path/'m',writable=True) as m:
        put(m,'E000000','Mira home is Koral.','home','Koral',1)
        put(m,'E000001','Mira job is Atrium.','job','Atrium',2)
        put(m,'E000002','Mira home is Zefir.','home','Zefir',3)
        put(m,'E000003','Mira home is Future.','home','Future',9)
        visible=[]
        fake=SimpleNamespace(PROFILES={'lexical':{}},Item=lambda sid,*a:SimpleNamespace(id=sid),
            build_index=lambda items,day:visible.extend(i.id for i in items),
            retrieve=lambda *a:{'status':'ok','items':[SimpleNamespace(id='E000000'),SimpleNamespace(id='E000001')]})
        packs=H.packs(m,'test','What is Mira home?',4,fake)
        assert packs['base']['ids']==['E000000','E000001']
        assert packs['chains']['ids']==['E000002','E000000','E000001']
        assert 'E000003' not in visible
        assert 'Future' not in packs['chains']['context']


def test_labeled_history_is_rejected_before_loading_model(tmp_path,monkeypatch):
    history=tmp_path/'history'
    history.write_text(json.dumps({'text':'Mira lives in Koral.','construction_label':'gold'})+'\n',encoding='utf-8')
    monkeypatch.setattr(H,'start',lambda *a:None)
    monkeypatch.setattr(H,'Reader',lambda *a:pytest.fail('Labeled source touched model'))
    with pytest.raises(ValueError,match='labels cannot enter'):
        H.capture(history,tmp_path/'m',tmp_path/'out',tmp_path/'ledger','test')


def test_local_cumulative_cap_precedes_transport(tmp_path,monkeypatch):
    ledger=tmp_path/'ledger.jsonl'
    ledger.write_text(''.join(json.dumps({'key':f'previous:{i}'})+'\n' for i in range(1200)),encoding='utf-8')
    reader=H.Reader(tmp_path,ledger)
    monkeypatch.setattr(H.P.LocalReader,'ask',lambda *a,**kw:pytest.fail('Over-cap generation'))
    try:
        with pytest.raises(RuntimeError,match='Cumulative'):
            reader.ask('next',[{'role':'user','content':'test'}],7)
    finally:
        reader.release()
    assert not ledger.with_suffix('.lock').exists()
