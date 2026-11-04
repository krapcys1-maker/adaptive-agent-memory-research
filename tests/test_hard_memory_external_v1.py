import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import hard_memory_external_v1 as H
import hard_memory_local_control_v2 as V


@pytest.fixture
def prepared(tmp_path,monkeypatch):
    config=H.cfg();config['n_questions']=2;monkeypatch.setattr(H,'cfg',lambda:copy.deepcopy(config))
    archive,questions,gold=H.split_source({'context':'0. The secret orchid owner is Miro.\n1. The secret orchid owner is Lena.',
        'questions':['Who owns the secret orchid?','Who owns the missing violet?'],'answers':[['Lena'],['UNKNOWN']]})
    p=tmp_path/'prepared';p.mkdir()
    for name,rows in [('archive',archive),('questions',questions),('gold',gold)]:H.write_rows(p/(name+'.jsonl'),rows)
    H.write_rows(p/'packets.jsonl',H.packets(archive,questions,config))
    H.P.write(p/'preparation.json',{'source_sha256':config['source_sha256'],
        'inputs':[{'name':n,'sha256':H.digest(p/(n+'.jsonl'))} for n in ['archive','questions','gold','packets']]})
    return p


def provider(path,body=None):
    if path=='/models':return {'data':[{'id':'deepseek-flash','name':'DeepSeek-V4.1-Flash'}]}
    question=body['messages'][-1]['content']
    answer=question.split('The control value is ',1)[1].split('. What is it?')[0] if 'The control value is ' in question else 'UNKNOWN'
    return {'model':'deepseek-flash','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'value':answer})}}],
            'usage':{'prompt_tokens':100,'completion_tokens':8}}


@pytest.fixture
def completed(prepared,tmp_path,monkeypatch):
    out=tmp_path/'run';ledger=tmp_path/'ledger'
    factory=lambda cfg,o:H.F.FlashReader(cfg,o,ledger,'hard-test',key_loader=lambda:'test-secret',transport=provider)
    assert H.run(prepared,out,'flash',ledger,factory=factory,require_clean=False)
    freeze=tmp_path/'freeze.json';H.P.write(freeze,{'response_sha256':H.digest(out/'responses.jsonl'),
        'files':[{'name':p.name,'sha256':H.digest(p)} for p in out.glob('*.json*')]})
    monkeypatch.setattr(H,'committed',lambda p:None)
    return prepared,out,freeze


def test_full_fake_run_scores_unrepaired_answers_and_reconstructs_inputs(completed):
    prepared,out,freeze=completed;result=H.score(prepared,out,freeze)
    assert result['complete'] and result['generation_calls']==7
    assert result['arms']['K']['exact']==1 and result['arms']['B']['exact']==1
    assert result['arms']['B']['unknown']==2
    calls=H.records(out/'attempts.jsonl')
    assert all(len(c['request']['messages'])==2 for c in calls)
    assert all('test-secret' not in p.read_text() for p in out.glob('*.json*'))


def test_reader_generation_never_opens_gold(prepared,tmp_path,monkeypatch):
    original=Path.open
    def trapped(path,*args,**kwargs):
        if path.name=='gold.jsonl':pytest.fail('Gold opened during inference')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',trapped)
    ledger=tmp_path/'ledger'
    factory=lambda cfg,o:H.F.FlashReader(cfg,o,ledger,'test',key_loader=lambda:'test',transport=provider)
    assert H.run(prepared,tmp_path/'run','flash',ledger,factory=factory,require_clean=False)


def test_forbidden_gold_fields_never_reach_retrieval():
    with pytest.raises(ValueError,match='question'):
        H.packets([], [{'id':'Q0','question':'What?','answer':'leaked'}],H.cfg())
    with pytest.raises(ValueError,match='Archive'):
        H.packets([{'id':'F0','ordinal':0,'text':'fact','gold':True}],[],H.cfg())


def test_persisted_packet_source_order_and_equal_byte_ceiling(prepared):
    rows=H.records(prepared/'packets.jsonl')
    for row in rows:
        assert len(row['context'].encode())<=H.cfg()['max_context_bytes']
        assert row['shown_ids']==sorted(row['shown_ids'])
    assert next(r for r in rows if r['key']=='Q000:N')['context']==''


@pytest.mark.parametrize('tamper',['raw','gold','packet','answer-id','request','duplicate','incomplete'])
def test_tampering_cannot_produce_a_complete_score(completed,tamper):
    prepared,out,freeze=completed
    if tamper=='raw':path=out/'responses.jsonl';rows=H.records(path);rows[-1]['text']='{"value":"Lena"}'
    elif tamper=='gold':path=prepared/'gold.jsonl';rows=H.records(path);rows[0]['answers']=['UNKNOWN']
    elif tamper=='packet':path=prepared/'packets.jsonl';rows=H.records(path);rows[-1]['context']='leak'
    elif tamper=='answer-id':path=out/'answers.jsonl';rows=H.records(path);rows[0]['id']='Q001'
    elif tamper=='request':
        path=out/'attempts.jsonl';rows=H.records(path);rows[-1]['request']['model']='deepseek-pro'
        rows[-1]['request_sha256']=H.P.sha(rows[-1]['request'])
    elif tamper=='duplicate':path=out/'attempts.jsonl';rows=H.records(path);rows.append(rows[-1])
    else:
        path=out/'finished.json';v=json.loads(path.read_text());v['complete']=False;path.write_text(json.dumps(v))
        frozen=json.loads(freeze.read_text())
        for row in frozen['files']:
            if row['name']=='finished.json':row['sha256']=H.digest(path)
        freeze.write_text(json.dumps(frozen))
        with pytest.raises(ValueError,match='incomplete'):H.score(prepared,out,freeze)
        return
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    with pytest.raises(ValueError):H.score(prepared,out,freeze)


def test_normalized_exact_match_never_becomes_substring_success():
    assert H.metrics('The Nile.', ['Nile'])['exact']
    got=H.metrics('Nile or Amazon', ['Nile'])
    assert not got['exact'] and got['substring'] and got['f1']<1
    assert not H.metrics(None,['Nile'])['exact']


def test_old_results_cannot_be_overwritten(completed):
    prepared,out,_=completed
    with pytest.raises(FileExistsError):H.run(prepared,out,'flash',out/'ledger',require_clean=False)


def test_local_control_amendment_never_changes_primary_messages_or_seeds(tmp_path,monkeypatch):
    captured=[]
    def capture(self,key,messages,seed,**kwargs):captured.append((key,messages,seed))
    monkeypatch.setattr(H.P.LocalReader,'ask',capture)
    reader=V.Reader(H.R.local_config(H.cfg()),tmp_path)
    primary=[{'role':'system','content':'primary must stay identical'}]
    reader.ask('positive-0',[],17)
    reader.ask('Q003:B',primary,20)
    assert captured[0]==('positive-0',V.control_messages(H.cfg(),0),7)
    assert captured[1]==('Q003:B',primary,20) and captured[1][1] is primary
