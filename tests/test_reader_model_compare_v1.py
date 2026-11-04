import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reader_model_compare_v1 as R
import audit_reader_model_compare_v1 as A
import report_reader_model_compare_v1 as B

F,P=R.F,R.P


def provider(path,body=None):
    if path=='/models':return {'data':[{'id':'deepseek-flash','name':'DeepSeek-V4.1-Flash'}]}
    assert path=='/chat/completions'
    system=body['messages'][0]['content']
    value=system.rsplit('The control_value is ',1)[1].rstrip('.') if 'The control_value is ' in system else 'deliberately-wrong'
    return {'model':'deepseek-flash','choices':[{'finish_reason':'stop','message':{'content':json.dumps({'value':value})}}],
            'usage':{'prompt_tokens':200,'completion_tokens':12}}


@pytest.fixture
def fake_run(tmp_path):
    out=tmp_path/'run';ledger=tmp_path/'ledger.jsonl'
    result=R.run(out,'flash',ledger,require_clean=False,factory=lambda cfg,o:F.FlashReader(
        cfg,o,ledger,'benchmark',key_loader=lambda:'secret-for-tests',transport=provider))
    return out,ledger,result


def test_full_fixed_cohort_with_real_guard_and_independent_reconstruction(fake_run):
    out,ledger,result=fake_run
    assert result['complete'] and result['generation_calls']==200
    assert result['arms']['V']['delivered_agreement']==48
    assert result['arms']['V']['raw_agreement']==0
    assert result['arms']['V']['all_three_chain_agreement']==16
    assert result['arms']['K']['retrieved']==32
    assert A.audit(out)['passed']
    assert len(P.read_rows(ledger))==400
    assert not ledger.with_suffix('.jsonl.lock').exists()
    assert all('secret-for-tests' not in p.read_text(encoding='utf-8') for p in out.glob('*'))


@pytest.mark.parametrize('tamper',['summary','context','response','history','request_hash','control','duplicate'])
def test_auditor_rejects_tampered_metrics_inputs_answers_and_coverage(fake_run,tamper):
    out,_,_=fake_run
    if tamper=='summary':
        path=out/'summary.json';value=json.loads(path.read_text());value['arms']['V']['raw_agreement']=48
        path.write_text(json.dumps(value));assert not A.audit(out)['passed'];return
    filename={'context':'turns','response':'responses','history':'attempts','request_hash':'attempts','control':'controls','duplicate':'responses'}[tamper]
    path=out/(filename+'.jsonl');rows=P.read_rows(path)
    if tamper=='context':rows[0]['replay']['context']='injected answer'
    if tamper=='response':rows[6]['text']='{"value":"forged"}'
    if tamper=='history':
        row=next(r for r in rows if r['key'].endswith(':N:2'))
        row['request']['messages'][2]['content']='forged'
        row['request_sha256']=P.sha(row['request'])
    if tamper=='request_hash':rows[0]['request_sha256']='wrong'
    if tamper=='control':rows[3]['passed']=False
    if tamper=='duplicate':rows.append(rows[0])
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows))
    assert not A.audit(out)['passed']


@pytest.mark.parametrize('field,value',[('api_model','deepseek-pro'),('api_model','deepseek-chat'),
    ('api_url','https://example.com'),('api_advertised_name_prefix','DeepSeek'),('api_reserved_cap_usd',2),
    ('api_reservation_usd',.001),('max_calls',206),('max_api_messages',5),('max_api_message_bytes',6001)])
def test_unapproved_model_provider_and_relaxed_caps_fail_before_key_loading(tmp_path,field,value):
    cfg=copy.deepcopy(R.settings());cfg[field]=value
    def forbidden():pytest.fail('credentials must not be loaded')
    with pytest.raises(ValueError):F.FlashReader(cfg,tmp_path,tmp_path/'ledger','x',key_loader=forbidden)
    assert not (tmp_path/'ledger').exists()


def test_reservation_precedes_failed_transport_and_survives_new_client(tmp_path):
    cfg=R.settings();cfg['max_calls']=1;path=tmp_path/'ledger'
    def failing(endpoint,body):
        assert len(P.read_rows(path))==1
        raise TimeoutError('failure with secret body must not be logged')
    client=F.FlashReader(cfg,tmp_path,path,'phase',key_loader=lambda:'secret',transport=failing)
    with pytest.raises(TimeoutError):client.ask('one',[{'role':'user','content':'JSON please'}],7)
    client.release()
    client=F.FlashReader(cfg,tmp_path,path,'newphase',key_loader=lambda:'secret',transport=provider)
    try:
        with pytest.raises(RuntimeError,match='Cumulative'):client.ask('two',[],7)
        assert client.ledger.summary()['unknown_usage_attempts']==1
    finally:client.release()


def test_lock_torn_ledger_and_budget_fail_closed(tmp_path):
    cfg=R.settings();cfg['api_reserved_cap_usd']=.004;path=tmp_path/'ledger'
    ledger=F.ReservationLedger(path,cfg)
    try:
        with pytest.raises(FileExistsError):F.ReservationLedger(path,cfg)
        ledger.reserve('a')
        with pytest.raises(ValueError):ledger.reserve('a')
        with pytest.raises(RuntimeError,match='cap'):ledger.reserve('b')
        with path.open('a') as stream:stream.write('{torn')
        with pytest.raises(ValueError,match='torn'):ledger.reserve('b')
    finally:ledger.close()


@pytest.mark.parametrize('kind',['identity','returned-model','thinking','usage','oversize'])
def test_provider_mismatch_and_input_bounds_never_fallback(tmp_path,kind):
    cfg=R.settings();seen=[]
    def transport(path,body=None):
        seen.append(path);response=provider(path,body)
        if kind=='identity':response['data'][0]['name']='DeepSeek-V4.1-Pro'
        if kind=='returned-model':response['model']='deepseek-pro'
        if kind=='thinking':response['choices'][0]['message']['reasoning_content']='never store this'
        if kind=='usage':response['usage']={}
        return response
    client=F.FlashReader(cfg,tmp_path,tmp_path/'ledger','x',key_loader=lambda:'secret',transport=transport)
    try:
        if kind=='identity':
            with pytest.raises(ValueError):client.preflight()
            assert seen==['/models']
        else:
            with pytest.raises((ValueError,RuntimeError)):
                client.ask('a',[{'role':'user','content':'x'*7000 if kind=='oversize' else 'JSON'}],7)
            assert len(seen)==(0 if kind=='oversize' else 1)
            assert not (tmp_path/'responses.jsonl').exists()
    finally:client.release()


def test_partial_failure_records_no_provider_body_and_never_resumes(tmp_path):
    out=tmp_path/'run';ledger=tmp_path/'ledger'
    def fail(*args):raise RuntimeError('private error body')
    factory=lambda cfg,o:F.FlashReader(cfg,o,ledger,'x',key_loader=lambda:'secret',transport=fail)
    result=R.run(out,'flash',ledger,factory=factory,require_clean=False)
    assert not result['complete']
    assert 'private error body' not in (out/'failure.json').read_text()
    with pytest.raises(FileExistsError):R.run(out,'flash',ledger,factory=factory,require_clean=False)


def test_local_backend_runs_same_cohort_with_no_api_ledger(tmp_path):
    class Local(P.LocalReader):
        def __init__(self,cfg,out):super().__init__(R.local_config(cfg),out,request=self.fake)
        def preflight(self):return {'fake':True}
        def fake(self,path,body=None):
            if path=='/api/tags':return {'models':[{'name':self.cfg['model'],'digest':self.cfg['model_digest']}]}
            if path=='/api/version':return {'version':'fake'}
            if path=='/api/generate':return {'model':self.cfg['model'],'done':True}
            response=provider('/chat/completions',body)
            return {'model':self.cfg['model'],'done':True,'done_reason':'stop','message':response['choices'][0]['message']}
    out=tmp_path/'local';ledger=tmp_path/'unused'
    result=R.run(out,'local14b',ledger,factory=Local,require_clean=False)
    assert result['complete'] and A.audit(out)['passed']
    assert not ledger.exists()


def test_saved_comparison_rebuilds_reference_metrics_context_matches_and_spend():
    actual=B.report()
    stored=json.loads((R.DATA/'comparison.json').read_text(encoding='utf-8'))
    assert actual==stored
    assert actual['new_generation_calls']==400 and actual['new_model_planning_calls']==0
    assert actual['reference_7b_recomputed']['V']['raw_agreement']==36
    assert actual['readers']['local14b']['reference_matched_contexts_and_questions']==192
    assert actual['readers']['flash']['reference_matched_contexts_and_questions']==192
    assert actual['api_budget_rechecked']['reserved_calls']==200
