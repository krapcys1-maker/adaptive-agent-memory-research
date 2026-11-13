"""Diagnostic evidence interventions and fixed cumulative-cap behavior."""
import json

import pytest

from scripts import h1_obsolete_controls_v1 as control


def test_conflict_arms_keep_same_evidence_but_reverse_order():
    arms=control.condition_ids(['extra','new'], 'new', 'old')
    assert arms['original']==['extra','new']
    assert arms['oracle_only']==['new']
    assert arms['old_then_new']==list(reversed(arms['new_then_old']))
    assert set(arms['old_then_new'])=={'old','new'}
    with pytest.raises(ValueError,match='distinct'):
        control.condition_ids(['same'],'same','same')


def test_phase_refuses_a_cap_that_cannot_cover_every_condition(tmp_path):
    ledger=tmp_path/'ledger'
    ledger.write_text('\n'.join(json.dumps({'key':str(i)}) for i in range(2701)),encoding='utf-8')
    assert control.validate_ledger(ledger)==2701
    with ledger.open('a',encoding='utf-8') as f:f.write('\n'+json.dumps({'key':'last'}))
    with pytest.raises(ValueError,match='entire control phase'):
        control.validate_ledger(ledger)


@pytest.mark.parametrize('text',['{"answer":5}','{"other":"text"}','[]','broken'])
def test_invalid_native_answers_are_retained_as_scoring_failures(text):
    assert control.parse(text) is None
