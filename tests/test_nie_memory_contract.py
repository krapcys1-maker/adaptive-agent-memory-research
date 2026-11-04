import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import nie_memory_contract as C
import nie_persona_replay as R


def item(value='teal', slot='kettle_colour', origin='fiction_autobio', identity='one'):
    return {'id':identity,'origin':origin,'text':f'My kitchen kettle colour is {value}.',
            'meta':{'typed_claim':{'slot':slot,'value':value}}}


def test_wrong_answer_is_replaced_only_from_shown_matching_evidence():
    result=C.guard_answer('kettle_colour','{"value":"amber"}',[item()])
    assert result=={'value':'teal','resolution':'corrected','source_ids':['one']}
    assert C.guard_answer('kettle_colour','{"value":"teal"}',[])['value']=='UNKNOWN'
    assert C.guard_answer('different_slot','{"value":"teal"}',[item()])['value']=='UNKNOWN'


def test_matching_value_is_accepted_with_source_and_case_normalization():
    r=C.guard_answer('kettle_colour','{"value":"TEAL"}',[item()])
    assert r['resolution']=='accepted' and r['value']=='teal' and r['source_ids']==['one']


@pytest.mark.parametrize('candidate',['not JSON','{"value":7}','{"value":"teal","other":true}','```json\n{"value":"teal"}\n```'])
def test_malformed_reader_output_is_not_accepted(candidate):
    assert C.guard_answer('kettle_colour',candidate,[item()])['resolution']=='corrected'


def test_conflicting_records_abstain_instead_of_guessing_latest():
    r=C.guard_answer('kettle_colour','{"value":"teal"}',[item(),item('amber',identity='two')])
    assert r=={'value':'UNKNOWN','resolution':'conflicting_evidence','source_ids':['one','two']}


def test_nonpersonal_or_nonfiction_evidence_cannot_authorize_personal_fact():
    assert C.guard_answer('kettle_colour','{}',[item()],task_type='comment')['value']=='UNKNOWN'
    assert C.guard_answer('kettle_colour','{}',[item(origin='account_history')])['value']=='UNKNOWN'


def test_untyped_legacy_text_is_not_silently_promoted():
    x=item();x['meta']={}
    assert C.guard_answer('kettle_colour','{}',[x])['resolution']=='no_evidence'


@pytest.mark.parametrize('broken',[None,{'origin':'fiction_autobio','meta':7},
    {'origin':'fiction_autobio','text':'teal','meta':{'typed_claim':{'slot':'kettle_colour','value':'teal'}}}])
def test_corrupt_retrieval_objects_abstain_without_authorizing_an_answer(broken):
    assert C.guard_answer('kettle_colour','{"value":"teal"}',[broken])['resolution']=='invalid_evidence'


@pytest.mark.parametrize('claim,text',[
    ({'slot':'x','value':'7 April'},'It happened on 17 April.'),
    ({'slot':'x','value':'red'},'I am tired.'),
    ({'slot':'x','value':'UNKNOWN'},'UNKNOWN'),
    ({'slot':'Bad Slot','value':'teal'},'teal'),
    ({'slot':'x','value':'teal','extra':1},'teal'),
])
def test_claim_validation_refuses_ambiguous_or_unsupported_data(claim,text):
    with pytest.raises(ValueError):C.validate_claim(claim,text)


def test_bridge_preserves_opt_in_claim_but_future_claim_never_reaches_guard():
    def row(identity,stamp,value):
        return {'kiedy':stamp,'id_notki':identity,'typ_zadania':'notka_zycie','zrodlo':'improwizacja',
                'tekst':f'My kitchen kettle colour is {value}.','supersedes':None,
                'typed_claim':{'slot':'kettle_colour','value':value}}
    source='\n'.join(json.dumps(x) for x in [row('one','2026-11-01T00:00:00Z','teal'),
                         row('two','2026-11-05T00:00:00Z','amber')]).encode()
    replay=R.replay(source,'kitchen kettle colour','2026-11-03T00:00:00Z')
    assert replay['schema_version']==2 and replay['future_publications_excluded_before_index']==1
    assert replay['shown_items'][0]['meta']['typed_claim']['value']=='teal'
    assert C.guard_answer('kettle_colour','{"value":"amber"}',replay['shown_items'])['value']=='teal'


def test_legacy_fixture_keeps_its_original_item_ids():
    root=Path(__file__).resolve().parents[1]/'data/lab/nie-offline-bridge-v1'
    old=json.loads((root/'personal.json').read_text(encoding='utf-8'))
    new=R.replay((root/'synthetic-journal.jsonl').read_bytes(),'blue bicycle harbour workshop','2026-11-03T00:00:00Z')
    assert [x['id'] for x in new['shown_items']]==[x['id'] for x in old['shown_items']]
