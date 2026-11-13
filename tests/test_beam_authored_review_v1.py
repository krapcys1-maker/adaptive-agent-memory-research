"""Evaluation-boundary checks; synthetic references, no model or BEAM gold."""
from copy import deepcopy
import json
import pytest
from scripts.reviews import beam_reader_authored_review_v1 as R


def answer(text='UNKNOWN',valid=True,raw=None):
    return {'valid_output':valid,'delivered_answer':text,'raw_answer':text if raw is None else raw}


def case():
    candidates,mapping=R.group_answers('q',{'N':answer(),'B':answer('Keep enabled.'),
        'Craw':answer(raw='Keep enabled.'),'Cdelivered':answer()})
    packet={'id':'q','candidates':candidates}
    verdict={'id':'q','reference_status':'usable','reference_note':'',
        'candidates':[{'candidate_id':c['candidate_id'],'pass':c['text']=='Keep enabled.',
            'material_contradiction':False,'reason':'Correct policy.' if c['text']=='Keep enabled.' else 'Required policy is missing.'} for c in candidates]}
    return packet,mapping,verdict


def test_exact_dedup_is_within_question_and_preserves_raw_vs_delivered():
    p,m,v=case()
    assert len(p['candidates'])==2
    assert m['B']==m['Craw'] and m['N']==m['Cdelivered'] and m['B']!=m['Cdelivered']
    assert R.candidate_id('other','UNKNOWN')!=R.candidate_id('q','UNKNOWN')
    assert R.candidate_id('q','UNKNOWN ')!=R.candidate_id('q','UNKNOWN')


def test_malformed_safe_fallback_cannot_inherit_a_correct_unknown_verdict():
    p,m,v=case();v['candidates'][0]['pass']=True
    validated=R.validate_verdicts([p],[v])['q']
    result=R.outcome(validated,{'candidate_id':None,'valid_output':False})
    assert not result['pass'] and not result['uncertain'] and result['format_failure']


def test_ambiguous_reference_stays_in_denominator_and_only_upper_bound():
    p,m,v=case();v['reference_status']='ambiguous';v['reference_note']='Reference names inconsistent constraints.'
    validated=R.validate_verdicts([p],[v])['q']
    result=R.outcome(validated,m['B'])
    report=R.summarize([{'outcomes':{t:result for t in R.TARGETS}}])
    assert report['B']['cases']==1 and report['B']['passes']==0 and report['B']['upper_pass_bound']==1


def test_correct_raw_answer_lost_to_guard_remains_a_delivered_failure():
    p,m,v=case();validated=R.validate_verdicts([p],[v])['q']
    assert R.outcome(validated,m['Craw'])['pass']
    assert not R.outcome(validated,m['Cdelivered'])['pass']


@pytest.mark.parametrize('mutation',['duplicate_case','missing_answer','extra_answer','pass_contradiction','not_boolean'])
def test_review_rejects_incomplete_or_inconsistent_author_verdicts(mutation):
    p,m,v=case();rows=[v]
    if mutation=='duplicate_case':rows.append(deepcopy(v))
    if mutation=='missing_answer':v['candidates'].pop()
    if mutation=='extra_answer':v['candidates'].append(dict(v['candidates'][0],candidate_id='extra'))
    if mutation=='pass_contradiction':v['candidates'][0].update({'pass':True,'material_contradiction':True})
    if mutation=='not_boolean':v['candidates'][0]['pass']=1
    with pytest.raises(ValueError):R.validate_verdicts([p],rows)


def test_reference_join_rejects_uncommitted_raw_before_reading_labels(tmp_path,monkeypatch):
    output=tmp_path/'output';output.mkdir();(output/'raw-freeze.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(R.subprocess,'check_output',lambda *a,**k:b'different committed freeze')
    with pytest.raises(ValueError,match='Commit the complete raw freeze'):
        R.prepare(output,tmp_path/'labels-must-not-be-opened',tmp_path/'audit',tmp_path/'review')
    assert not (tmp_path/'review').exists()
