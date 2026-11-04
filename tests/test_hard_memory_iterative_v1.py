import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hard_memory_iterative_v1 as I
from test_hard_memory_external_v1 import prepared


class Fake(I.H.P.LocalReader):
    def __init__(self,cfg,out):super().__init__(cfg,out,request=self.fake)
    def preflight(self):return {'fake':True}
    def fake(self,path,body=None):
        if path=='/api/tags':return {'models':[{'name':self.cfg['model'],'digest':self.cfg['model_digest']}]}
        if path=='/api/version':return {'version':'fake'}
        if path=='/api/generate':return {'model':self.cfg['model'],'done':True}
        system=body['messages'][0]['content'];user=body['messages'][-1]['content']
        if 'The control_value is ' in system:
            value={'value':system.rsplit('The control_value is ',1)[1].rstrip('.')}
        else:
            searched=json.loads(user.split('Previously searched: ',1)[1].split('\nReturn JSON',1)[0])
            value={'value':'Lena','queries':[]} if 'orchid owner' in searched else {'value':'UNKNOWN','queries':['orchid owner']}
        return {'model':self.cfg['model'],'done':True,'done_reason':'stop','message':{'content':json.dumps(value)},'eval_count':8,'prompt_eval_count':50}


@pytest.fixture
def completed(prepared,tmp_path,monkeypatch):
    out=tmp_path/'run';assert I.execute(prepared,out,factory=Fake,require_clean=False)
    freeze=tmp_path/'freeze.json'
    I.H.P.write(freeze,{'files':[{'name':p.name,'sha256':I.H.digest(p)} for p in out.glob('*.json*')]})
    monkeypatch.setattr(I.H,'committed',lambda p:None)
    return prepared,out,freeze


def test_queries_trigger_real_search_and_all_rounds_are_reconstructed(completed):
    prepared,out,freeze=completed;result=I.score(prepared,out,freeze)
    assert result['complete'] and result['n']==2
    assert result['total_primary_rounds']==4 and result['requests_and_search_rounds_reconstructed']==4
    assert result['exact']==1  # The same fake answer is wrong on the unanswerable control, not repaired.
    traces=I.H.records(out/'trace.jsonl')
    assert [r['value'] for r in traces]==['UNKNOWN','Lena','UNKNOWN','Lena']


def test_same_budget_and_source_order_do_not_accept_invented_record_ids():
    archive={'F2':{'ordinal':2,'text':'new fact'},'F1':{'ordinal':1,'text':'old fact'}}
    ids,text=I.context(['F2','F1','F2'],archive,100)
    assert ids==['F1','F2'] and text.index('old fact')<text.index('new fact')
    assert I.context(['F2'],archive,1)==([], '')
    with pytest.raises(ValueError):I.context(['invented'],archive,100)


@pytest.mark.parametrize('text',['{}','{"value":"x"}','{"value":"x","queries":[1]}',
    '{"value":"x","queries":["a","b","c"]}','{"value":"x","queries":[],"gold":"leak"}'])
def test_malformed_query_protocol_is_not_a_good_answer(text):
    assert I.parse({'text':text,'done_reason':'stop'})==(None,[])


def test_generation_never_reads_gold(prepared,tmp_path,monkeypatch):
    original=Path.open
    def opened(path,*args,**kwargs):
        if path.name=='gold.jsonl':pytest.fail('Repair opened gold during generation')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',opened)
    assert I.execute(prepared,tmp_path/'run',factory=Fake,require_clean=False)


def test_scoring_rejects_trace_mutation_even_if_an_outer_hash_is_updated(completed):
    prepared,out,freeze=completed;p=out/'trace.jsonl';rows=I.H.records(p);rows[1]['shown_ids']=[]
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    frozen=json.loads(freeze.read_text())
    for r in frozen['files']:
        if r['name']=='trace.jsonl':r['sha256']=I.H.digest(p)
    freeze.write_text(json.dumps(frozen))
    with pytest.raises(ValueError,match='trace'):I.score(prepared,out,freeze)
