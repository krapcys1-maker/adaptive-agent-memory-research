import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import h1_metadata_grounding_v3 as H3
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory


def test_projection_preserves_raw_and_only_rescues_literal_case(tmp_path,monkeypatch):
    store=tmp_path/'raw'; capture=tmp_path/'capture'; capture.mkdir(); out=tmp_path/'projection'
    with Memory(store,writable=True) as m:
        m.add_source(Source('E000000','test','Test suite is green.',1))
        m.add_source(Source('E000001','test','Linter checked 8 modules.',1))
        m.add_source(Source('E000002','test','Nera workspace changed.',2))
    def proposal(entity):
        return {'addresses':[{'entity':entity,'property':'workspace','kind':'observation'}]}
    badcase,invented,valid=proposal('test suite'),proposal('clean_modules'),proposal('Nera')
    H3.P.append(capture/'addresses.jsonl',{'source':'E000002','proposal':valid,'derivation':'new_generation','from_source':None})
    for i,p in enumerate([badcase,invented,valid]):
        H3.P.append(capture/'responses.jsonl',{'key':f'address-E{i:06d}','text':json.dumps(p)})
    H3.P.write(capture/'raw-freeze.json',{'files_sha256':{p.name:H3.S.file_sha(p) for p in capture.iterdir()}})
    before={p:p.read_bytes() for p in [store,*capture.iterdir()]}
    monkeypatch.setattr(H3,'identity',lambda:{'clean_tree':True})
    monkeypatch.setattr(H3.P.LocalReader,'__init__',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('No model calls')))
    H3.project(store,capture,out)
    summary=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    assert summary['new_generations']==0
    assert summary['counts']['case_rescued_sources']==1
    assert summary['counts']['quarantined']==1
    assert summary['counts']['retained_base_accepted']==1
    assert summary['counts']['lost_base_accepted']==0
    rows=H3.P.read_rows(out/'addresses.jsonl')
    assert rows[0]['proposal']['addresses'][0]['entity']=='Test suite'
    assert all(p.read_bytes()==raw for p,raw in before.items())
