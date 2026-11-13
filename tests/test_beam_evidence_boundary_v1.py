import pytest
from scripts import beam_evidence_boundary_v1 as E


@pytest.mark.parametrize('value', [True, False, -1, 1.5, '1.0', 'turn 1', '١', {'guess': 'chat_id=8'}])
def test_diagnostic_never_guesses_reference_ids(value):
    with pytest.raises(ValueError): E.raw_id(value)


def test_reference_ids_are_deduplicated_within_case_only_and_nested_lists_are_explicit():
    assert E.reference_ids({'original': [8, '9'], 'updated': [9, 10]}) == [8, 9, 10]
    assert E.reference_ids(None) == []
    assert E.reference_ids([]) == []
    assert E.reference_ids(['0008', 8]) == [8]
    with pytest.raises(ValueError): E.reference_ids({'source': ['not an integer']})


def test_interval_coverage_does_not_double_count_overlap_or_repeated_windows():
    assert E.covered_chars([(0, 10), (5, 20), (0, 10), (20, 25), (30, 40)], 50) == 35
    assert E.covered_chars([], 50) == 0


@pytest.mark.parametrize('span', [(0, 51), (-1, 10), (5, 5), (9, 1), (False, 8)])
def test_forged_character_coverage_cannot_inflate_recall(span):
    with pytest.raises(ValueError): E.covered_chars([span], 50)


def test_failure_partition_distinguishes_archive_retrieval_budget_and_partial_context():
    source = E.W.Source('s', 'scope', 'abcdef ' * 100, 'user', 0)
    windows = list(E.W.split(source, max_text_bytes=100, overlap_bytes=20))
    target = {'id': 's', 'chars': len(source.text)}
    assert E.classify(None, windows, windows) == ('not_in_source_archive', 0)
    assert E.classify(target, [], []) == ('not_retrieved', 0)
    assert E.classify(target, windows, []) == ('retrieved_not_shown', 0)
    status, chars = E.classify(target, windows, windows[:1])
    assert status == 'shown_partial' and 0 < chars < target['chars']
    assert E.classify(target, windows, windows) == ('shown_full', len(source.text))


def case(state, declared, shown=0):
    return {'annotation_state': state, 'declared_targets': declared,
        'target_states': {k: 0 for k in E.STATES}, 'candidate_targets': shown,
        'shown_targets': shown, 'context_targets': shown, 'old_windows': 1, 'new_windows': 1}


def test_absent_or_empty_annotations_are_not_perfect_all_target_retrieval():
    missing = case('missing', 0); empty = case('empty', 0); present = case('nonempty', 2, 2)
    present['target_states']['shown_full'] = 2
    result = E.summarize([missing, empty, present])
    assert result['cases'] == 3 and result['nonempty_annotation_cases'] == 1
    assert result['no_annotation_cases'] == 1 and result['empty_annotation_cases'] == 1
    assert result['all_candidate_target_cases'] == result['all_shown_target_cases'] == 1
    assert result['all_shown_full_source_cases'] == result['all_new_context_target_cases'] == 1
