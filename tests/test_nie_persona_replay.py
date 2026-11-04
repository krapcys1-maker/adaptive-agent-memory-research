import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / 'scripts/nie_persona_replay.py'
spec = importlib.util.spec_from_file_location('nie_persona_replay', PATH)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def row(**changes):
    return dict(kiedy='2026-11-01T12:00:00+00:00', typ_zadania='notka_zycie', id_notki='synthetic-1',
                tekst='I repaired my blue bicycle beside the harbour workshop.', zrodlo='improwizacja',
                supersedes=None, run_id=42, zasiew='fixture', wersja=1, **changes)


def raw(*rows):
    return ('\n'.join(json.dumps(r) for r in rows)+'\n').encode()


OPEN = {'names': False, 'lex_tau': 1e-9, 'min_evidence': 0.0}


def test_existing_journal_layout_preserves_fictional_provenance_and_is_deterministic():
    source = raw(row())
    a = R.replay(source, 'blue bicycle harbour workshop', '2026-11-02T00:00:00Z')
    b = R.replay(source, 'blue bicycle harbour workshop', '2026-11-02T00:00:00Z')
    assert a == b
    assert len(a['shown_items']) == 1
    item = a['shown_items'][0]
    assert item['origin'] == 'fiction_autobio'
    assert item['meta']['source'] == 'improwizacja' and item['meta']['publication_id'] == 'synthetic-1'
    assert R.HEADING in a['context']


def test_future_text_never_enters_index_or_changes_earlier_context():
    future = row();future.update(id_notki='future', kiedy='2026-11-03T00:00:00Z',tekst='blue bicycle '*200)
    a = R.replay(raw(row()), 'blue bicycle', '2026-11-02T00:00:00Z', profile=OPEN)
    b = R.replay(raw(row(),future), 'blue bicycle', '2026-11-02T00:00:00Z', profile=OPEN)
    assert b['future_publications_excluded_before_index'] == 1
    assert a['shown_items'] == b['shown_items'] and a['context'] == b['context']


def test_origin_restriction_keeps_persona_out_of_general_comment_task():
    r = R.replay(raw(row()), 'blue bicycle harbour workshop', '2026-11-02T00:00:00Z', task_type='comment')
    assert r['shown_items'] == [] and r['context'] == ''


def test_timezone_and_subsecond_availability_are_not_backdated_by_story_dates():
    early=row();early.update(id_notki='first',kiedy='2026-11-01T14:00:00+02:00')
    late=row();late.update(id_notki='later',kiedy='2026-11-01T12:00:00.500000Z',
                           tekst='In 2019 I repaired my blue bicycle beside the harbour workshop.')
    rows=R.entries(raw(late,early))
    assert [x['publication_id'] for x in rows]==['first','later']
    result=R.replay(raw(late,early),'blue bicycle harbour workshop','2026-11-01T12:00:00.100000Z')
    assert result['available_publications']==1
    assert result['future_publications_excluded_before_index']==1


def test_exact_duplicate_deduplicates_but_conflicting_publication_fails():
    assert len(R.entries(raw(row(),row()))) == 1
    changed = row();changed['tekst'] = 'A different invented detail.'
    with pytest.raises(ValueError, match='Conflicting'):
        R.entries(raw(row(),changed))


@pytest.mark.parametrize('key,value', [('kiedy','2026-11-01T12:00:00'), ('tekst',''),
    ('zrodlo','world_knowledge'), ('typ_zadania','comment'), ('supersedes','older'),('id_notki',None)])
def test_unsupported_or_ambiguous_input_fails_explicitly(key,value):
    r=row();r[key]=value
    with pytest.raises(ValueError): R.entries(raw(r))


def test_budget_counts_heading_and_dates_and_never_truncates_a_fact():
    source=raw(row())
    full=R.replay(source,'blue bicycle harbour workshop','2026-11-02T00:00:00Z')
    exact=R.replay(source,'blue bicycle harbour workshop','2026-11-02T00:00:00Z',max_context_words=full['context_words'])
    small=R.replay(source,'blue bicycle harbour workshop','2026-11-02T00:00:00Z',max_context_words=full['context_words']-1)
    assert exact['context']==full['context']
    assert small['kernel_ranked_ids'] and not small['shown_items'] and small['context']==''


def test_cli_is_read_only_and_refuses_output_overwrite(tmp_path):
    source=tmp_path/'journal.jsonl';source.write_bytes(raw(row()));before=source.read_bytes()
    out=tmp_path/'replay.json'
    args=['--input',str(source),'--output',str(out),'--query','blue bicycle harbour workshop',
          '--as-of','2026-11-02T00:00:00Z']
    assert R.main(args)==0
    saved=out.read_bytes()
    with pytest.raises(FileExistsError):R.main(args)
    assert out.read_bytes()==saved and source.read_bytes()==before


def test_offline_bridge_refuses_embedding_profile():
    with pytest.raises(ValueError,match='offline lexical'):
        R.replay(raw(row()),'bicycle','2026-11-02T00:00:00Z',profile={'embed':'required'})
