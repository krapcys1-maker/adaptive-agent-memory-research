from copy import deepcopy
import json
import pytest
from scripts import beam_reader_evidence_v1 as B


def packet():
    source=B.W.Source('source','scope','Żółty zapis: the gate must stay enabled before every deployment.','user',0)
    windows=list(B.W.split(source))
    return B.project('What is the gate policy?',windows,scope='scope',known_at=0,system=B.C_SYSTEM,total_candidates=1)


def response(answer='Keep the gate enabled.',quote='gate must stay enabled',window='E0',unknown=False):
    return json.dumps({'answer':answer,'unknown':unknown,'evidence':[{'window':window,'quote':quote}]})


def test_literal_provenance_maps_unicode_offsets_and_keeps_raw_answer():
    p=packet();r=B.grade_output(response(),'C',p['messages'],p['aliases'])
    assert r['valid_output'] and r['guard_reason']=='literal_evidence_valid'
    assert r['raw_answer']==r['delivered_answer']=='Keep the gate enabled.'
    trace=r['evidence_provenance'][0]
    assert trace['window']==p['aliases']['E0'] and trace['source']=='source'
    assert trace['utf8_span'][0]>trace['char_span'][0]


def test_presence_guard_intentionally_does_not_claim_semantic_entailment():
    p=packet();r=B.grade_output(response(answer='Disable the gate.'),'C',p['messages'],p['aliases'])
    assert r['guard_reason']=='literal_evidence_valid'
    assert r['delivered_answer']=='Disable the gate.'
    # This must be caught by semantic/reference evaluation, never relabelled
    # as a proven correct answer merely because a source quote exists.


def test_unsupported_literal_quote_refuses_without_gold_repair():
    p=packet();r=B.grade_output(response(quote='a fabricated supporting phrase'),'C',p['messages'],p['aliases'])
    assert r['valid_output'] and r['guard_reason']=='invalid_quote'
    assert r['delivered_answer']=='UNKNOWN' and r['raw_answer']=='Keep the gate enabled.'


@pytest.mark.parametrize('raw',['not JSON','[]','{"answer":17}',response(window='FORGED'),response(quote='tiny'),
    json.dumps({'answer':'UNKNOWN','unknown':True,'evidence':[{'window':'E0','quote':3}]})])
def test_malformed_output_is_not_a_successful_safe_abstention(raw):
    p=packet();r=B.grade_output(raw,'C',p['messages'],p['aliases'])
    assert r['delivered_answer']=='UNKNOWN' and not r['valid_output']


def test_candidate_and_raw_reader_receive_exact_same_alias_evidence():
    s=B.W.Source('s','scope','A policy record. '*100,'user',0)
    windows=list(B.W.split(s,max_text_bytes=128,overlap_bytes=16))
    old=B.W.render_packet('Question?',windows,scope='scope',known_at=0)
    row={'question':'Question?','conversation_id':'scope','known_at':0,'candidate_windows':[B.W.asdict(w) for w in windows],'retrieval_packet':old}
    ps=B.paired_packets(row)
    b,c=[json.loads(ps[a]['messages'][1]['content']) for a in ['B','C']]
    assert b==c and ps['B']['aliases']==ps['C']['aliases']
    assert ps['B']['shown_ids']==ps['C']['shown_ids']
    assert b['history']['evidence']
    assert not json.loads(ps['N']['messages'][1]['content'])['history']['evidence']
    for p in ps.values():assert max(B.W.message_bytes(p['messages']).values())<=6000
    assert {e['window'] for e in b['history']['evidence']}==set(ps['B']['aliases'])


def test_request_and_local_identity_guards_do_not_allow_provider_fallback():
    cfg=json.loads((B.DATA/'config.json').read_text(encoding='utf-8'));B.validate_config(cfg)
    altered=deepcopy(cfg);altered['base_url']='https://elsewhere.invalid'
    with pytest.raises(ValueError):B.validate_config(altered)
    p=packet();B.request_guard(cfg,p['messages'],B.c_schema(p['aliases']))
    altered=deepcopy(cfg);altered['max_request_bytes']=10
    with pytest.raises(ValueError):B.request_guard(altered,p['messages'],B.c_schema(p['aliases']))


def test_attempt_is_retained_and_duplicate_is_not_retried(tmp_path):
    cfg=json.loads((B.DATA/'config.json').read_text(encoding='utf-8'));out=tmp_path/'run';out.mkdir();ledger=tmp_path/'ledger.jsonl'
    reader=B.Reader(cfg,out,ledger);native=[]
    def fake(path,body=None):
        native.append(body)
        if body.get('keep_alive')==0:return {'done':True,'done_reason':'unload','model':cfg['model']}
        return {'done':True,'done_reason':'stop','model':cfg['model'],'message':{'content':'{"answer":"UNKNOWN"}'}}
    reader.request=fake
    p=B.controls()[0]
    try:
        reader.ask('test',p['messages'],7,output_schema=B.B_SCHEMA)
        with pytest.raises(RuntimeError):reader.ask('test',p['messages'],7,output_schema=B.B_SCHEMA)
        assert len(list(B.A.rows(ledger)))==1 and len(native)==1
    finally:reader.release()
    assert not reader.lock.exists()


def test_retained_task_cap_stops_before_network_or_new_attempt(tmp_path):
    cfg=json.loads((B.DATA/'config.json').read_text(encoding='utf-8'));out=tmp_path/'run';out.mkdir();ledger=tmp_path/'ledger.jsonl'
    ledger.write_text(''.join(json.dumps({'key':str(i)})+'\n' for i in range(650)),encoding='utf-8')
    before=ledger.read_bytes();reader=B.Reader(cfg,out,ledger)
    reader.request=lambda *args:pytest.fail('No model request at retained cap.')
    p=B.controls()[0]
    try:
        with pytest.raises(RuntimeError):reader.ask('blocked',p['messages'],7,output_schema=B.B_SCHEMA)
        assert ledger.read_bytes()==before
    finally:reader.release()
