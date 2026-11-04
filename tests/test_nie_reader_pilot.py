import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import nie_reader_pilot as P


def design():
    return (json.loads((P.DATA/'config.json').read_text(encoding='utf-8')),
            json.loads((P.DATA/'cases.json').read_text(encoding='utf-8')))


class FakeReader(P.LocalReader):
    def __init__(self, config, output):
        super().__init__(config,output,request=self.fake_request)

    def preflight(self):
        return {'fake':True}

    def fake_request(self,path,body=None):
        if path=='/api/tags':
            return {'models':[{'name':self.cfg['model'],'digest':self.cfg['model_digest']}]}
        if path=='/api/version':
            return {'version':'fake'}
        if path=='/api/generate':
            return {'model':self.cfg['model'],'done':True}
        assert path=='/api/chat'
        messages=body['messages']
        user=messages[-1]['content']
        if 'pool member: ' in user:
            value=json.loads(user.split('pool member: ',1)[1])[0]
        elif 'control_value' in messages[0]['content']:
            value=messages[0]['content'].rsplit('The control_value is ',1)[1].rstrip('.')
        else:
            value='wrong-reader-value'  # Force the real guard to use retrieved evidence, not a fake good reader.
        return {'model':self.cfg['model'],'done':True,'done_reason':'stop',
                'message':{'content':json.dumps({'value':value})},'thinking':'must never be saved',
                'prompt_eval_count':40,'eval_count':8}


@pytest.fixture
def fake_run(tmp_path):
    cfg,cases=design()
    out=tmp_path/'run'
    result=P.execute(out,cfg,cases,client_factory=FakeReader,require_clean=False)
    return out,cfg,cases,result


def test_complete_fake_loop_scores_all_chains_and_preserves_caps(fake_run):
    out,cfg,cases,result=fake_run
    assert result['complete'] and result['ledger_integrity'] and result['generation_calls']==216
    assert result['arms']['V']['all_three_chain_agreement']==16
    assert result['arms']['K']['all_three_chain_agreement']==0
    assert result['arms']['V']['guard_resolutions']['corrected']==48
    assert result['larger_offline_test_only'] is True
    assert 'must never be saved' not in (out/'responses.jsonl').read_text()


def test_paraphrase_resets_context_and_pressure_sees_only_emitted_answer(fake_run):
    out,_,_,_=fake_run
    calls={r['key']:r['request']['messages'] for r in P.read_rows(out/'attempts.jsonl')}
    for arm in ('N','K','O','V'):
        prefix='read:kettle_colour:17:'+arm+':'
        assert [x['role'] for x in calls[prefix+'0']]==['system','user']
        assert [x['role'] for x in calls[prefix+'1']]==['system','user']
        assert [x['role'] for x in calls[prefix+'2']]==['system','user','assistant','user']
    assert json.loads(calls['read:kettle_colour:17:V:2'][2]['content'])['value']=='teal'
    assert json.loads(calls['read:kettle_colour:17:K:2'][2]['content'])['value']=='wrong-reader-value'


def test_journal_reload_is_from_disk_and_missing_or_duplicate_chains_fail(fake_run):
    out,_,_,_=fake_run
    assert P.load_journal(out,'kettle_colour',17)[0]['typed_claim']['value']=='teal'
    journals=P.read_rows(out/'journals.jsonl')
    selected=next(r for r in journals if r['slot']=='kettle_colour' and r['seed']==17)
    selected['rows'][0]['typed_claim']['value']='amber'
    (out/'journals.jsonl').write_text('\n'.join(json.dumps(r) for r in journals)+'\n')
    assert P.load_journal(out,'kettle_colour',17)[0]['typed_claim']['value']=='amber'
    P.append(out/'journals.jsonl',selected)
    with pytest.raises(ValueError,match='unique'):P.load_journal(out,'kettle_colour',17)
    with pytest.raises(ValueError,match='unique'):P.load_journal(out,'missing',17)


@pytest.mark.parametrize('corruption',['missing_response','duplicate_response','unknown_turn','bad_request_hash'])
def test_incomplete_or_corrupt_records_cannot_receive_a_complete_reading(fake_run,corruption):
    out,cfg,cases,_=fake_run
    if corruption in ('missing_response','duplicate_response'):
        rows=P.read_rows(out/'responses.jsonl')
        rows=rows[:-1] if corruption=='missing_response' else rows+[rows[0]]
        (out/'responses.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    elif corruption=='unknown_turn':
        row=P.read_rows(out/'turns.jsonl')[0];row['slot']='unknown'
        P.append(out/'turns.jsonl',row)
    else:
        rows=P.read_rows(out/'attempts.jsonl');rows[0]['request_sha256']='bad'
        (out/'attempts.jsonl').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    result=P.summarize(cfg,cases,out,True)
    assert result['complete'] is False and result['larger_offline_test_only'] is None


def test_attempt_cap_is_reserved_before_transport_and_never_retries(tmp_path):
    cfg,_=design();cfg['max_calls']=1
    seen=[]
    def fail(path,body):
        seen.append(path);raise TimeoutError('fake interruption')
    client=P.LocalReader(cfg,tmp_path,request=fail)
    with pytest.raises(TimeoutError):client.ask('one',[],7)
    with pytest.raises(ValueError,match='Duplicate'):client.ask('one',[],7)
    with pytest.raises(RuntimeError,match='cap'):client.ask('two',[],7)
    assert len(seen)==1 and len(P.read_rows(tmp_path/'attempts.jsonl'))==1


def test_remote_endpoint_and_answer_leaking_cue_are_refused_before_execution(tmp_path):
    cfg,cases=design();cfg['base_url']='https://example.com'
    with pytest.raises(ValueError,match='local'):P.execute(tmp_path/'remote',cfg,cases,require_clean=False)
    assert not (tmp_path/'remote').exists()
    cfg,cases=design();cases[0]['cue']='teal kettle'
    with pytest.raises(ValueError,match='answer'):P.validate(cfg,cases)


def test_existing_execution_is_never_resumed_or_overwritten(tmp_path):
    cfg,cases=design();marker=tmp_path/'manifest.json';marker.write_text('preserve')
    with pytest.raises(FileExistsError):P.execute(tmp_path,cfg,cases,client_factory=FakeReader,require_clean=False)
    assert marker.read_text()=='preserve'


def test_schema_amendment_affects_only_writer_transport_and_is_recorded(tmp_path):
    cfg,cases=design();cfg['writer_format']='json_schema'
    out=tmp_path/'schema'
    result=P.execute(out,cfg,cases,client_factory=FakeReader,require_clean=False)
    assert result['complete']
    calls=P.read_rows(out/'attempts.jsonl')
    for call in calls:
        fmt=call['request']['format']
        if call['key'].startswith('write:'):
            assert fmt['required']==['value'] and fmt['additionalProperties'] is False
            slot=call['key'].split(':')[1]
            assert fmt['properties']['value']['enum']==next(c['values'] for c in cases if c['slot']==slot)
        else:
            assert fmt=='json'


def test_invalid_writer_is_a_failed_chain_not_a_selected_success(tmp_path):
    class RefusingWriter(FakeReader):
        def fake_request(self,path,body=None):
            value=super().fake_request(path,body)
            if path=='/api/chat' and 'pool member: ' in body['messages'][-1]['content']:
                value['message']['content']='{"value":"UNKNOWN"}'
            return value
    cfg,cases=design()
    result=P.execute(tmp_path/'refusal',cfg,cases,client_factory=RefusingWriter,require_clean=False)
    assert result['complete'] and result['write_failures']==16
    assert result['arms']['V']['all_three_chain_agreement']==0
    assert result['larger_offline_test_only'] is False
