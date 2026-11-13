import pytest
from scripts import beam_evidence_boundary_v1 as V1
from scripts import beam_evidence_boundary_v2 as V2


def test_v1_rejection_is_preserved_and_v2_retains_unknown_slots_separately():
    refs = [[8, 9], [9, 10], ['--']]
    with pytest.raises(ValueError): V1.reference_ids(refs)
    ids, unresolved = V2.reference_targets(refs)
    assert ids == [8, 9, 10] and unresolved == [[2, 0]]
    assert V2.reference_targets({'older': [8, '--'], 'newer': [10, '--']}) == ([8, 10], [['older', 1], ['newer', 1]])


@pytest.mark.parametrize('bad', [True, -1, 'chat 8', 'N/A', '?', 1.5])
def test_v2_does_not_turn_other_malformed_values_into_silent_unknowns(bad):
    with pytest.raises(ValueError): V2.reference_targets([8, bad])


def test_unknown_slot_prevents_all_target_success_without_discarding_valid_siblings():
    states = {k: 0 for k in V2.STATES}; states.update(shown_full=2, unresolved_reference=1)
    case = {'annotation_state': 'nonempty', 'declared_targets': 3, 'target_states': states,
        'candidate_targets': 2, 'shown_targets': 2, 'context_targets': 2, 'old_windows': 2, 'new_windows': 2}
    result = V2.summarize([case])
    assert result['any_shown_target_cases'] == 1 and result['declared_targets'] == 3
    assert result['all_shown_target_cases'] == result['all_candidate_target_cases'] == result['all_shown_full_source_cases'] == 0
    assert result['unresolved_marker_cases'] == 1 and result['target_states']['unresolved_reference'] == 1
