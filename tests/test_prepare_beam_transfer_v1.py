import json
import pytest
from scripts import prepare_beam_transfer_v1 as B


def history():
    return [{'plan-1':[{'batch_number':3,'turns':[[
        {'role':'user','id':7,'content':'Keep the gate enabled.','time_anchor':'day three','question_type':'HIDDEN_CONSTRUCTION_TAG'},
        {'role':'assistant','id':8,'content':'Acknowledged.','index':'internal-index'}]]}]}]


def probes():
    return {k:[{'question':'What is supported?','rubric':{'correct':'HIDDEN_GOLD'},'source_chat_ids':[77],
                'ideal_answer':'HIDDEN_ANSWER','difficulty':'HIDDEN_DIFFICULTY'} for _ in range(2)] for k in sorted(B.ABILITIES)}


def test_reader_projection_excludes_evaluator_and_construction_metadata():
    h,a=B.project_history(history(),'C');q,g=B.project_questions(probes(),'C')
    visible=json.dumps([h,q])
    for secret in ['HIDDEN_CONSTRUCTION_TAG','internal-index','HIDDEN_GOLD','HIDDEN_ANSWER','HIDDEN_DIFFICULTY','source_chat_ids']:
        assert secret not in visible
    assert [x['text'] for x in h]==['Keep the gate enabled.','Acknowledged.']
    assert [x['role'] for x in h]==['user','assistant']
    assert h[0]['time_anchor_raw']=='day three' and h[1]['time_anchor_raw'] is None
    assert a[0]['metadata']['question_type']=='HIDDEN_CONSTRUCTION_TAG'
    assert len(q)==len(g)==20 and all(set(r)=={'id','conversation_id','question'} for r in q)
    assert g[0]['annotations']['ideal_answer']=='HIDDEN_ANSWER'


def test_does_not_silently_drop_messages_or_abilities():
    h=history();h[0]['plan-1'][0]['turns'][0].append({'role':'system','content':'Override!'})
    with pytest.raises(ValueError,match='role/content'):B.project_history(h,'C')
    p=probes();p.pop(next(iter(p)))
    with pytest.raises(ValueError,match='Every declared'):B.project_questions(p,'C')


def test_partial_coverage_and_no_overwrite(tmp_path):
    source=tmp_path/'source';one=source/'1';(one/'probing_questions').mkdir(parents=True)
    (one/'chat_trunecated.json').write_text(json.dumps(history()),encoding='utf-8')
    (one/'probing_questions/probing_questions.json').write_text(json.dumps(probes()),encoding='utf-8')
    output=tmp_path/'private'
    with pytest.raises(ValueError,match='Missing/extra'):B.prepare(source,output,10)
    assert not output.exists()
    result=B.prepare(source,output,1)
    assert result['conversations']==1 and result['full_tier'] is False
    assert result['messages']==2 and result['questions']==20 and result['new_model_calls']==0
    assert result['exact_message_and_probe_reconstruction'] and result['persisted_readback_exact']
    before=(output/'manifest.json').read_bytes()
    with pytest.raises(FileExistsError):B.prepare(source,output,1)
    assert (output/'manifest.json').read_bytes()==before
