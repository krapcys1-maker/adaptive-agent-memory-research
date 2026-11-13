import pytest
from scripts import prepare_beam_transfer_v1 as V1
from scripts import prepare_beam_transfer_v2 as V2


def test_explicit_unknown_time_roundtrips_without_fabricated_clock():
    messages=[{'role':'user','content':'A statement.','time_anchor':None},
              {'role':'assistant','content':'A response.'}]
    raw=[{'plan-1':[{'turns':[messages]}]}]
    with pytest.raises(ValueError,match='time anchor'):V1.project_history(raw,'C')
    history,audit=V2.project_history(raw,'C')
    assert [r['time_anchor_raw'] for r in history]==[None,None]
    assert [r['had_time_anchor'] for r in audit]==[True,False]
    restored=[]
    for r,a in zip(history,audit):
        message={'role':r['role'],'content':r['text'],**a['metadata']}
        if a['had_time_anchor']:message['time_anchor']=r['time_anchor_raw']
        restored.append(message)
    assert restored==messages


def test_unknown_clock_is_not_permission_for_arbitrary_metadata_types():
    raw=[{'plan-1':[{'turns':[[{'role':'user','content':'Data','time_anchor':{'guess':'tomorrow'}}]]}]}]
    with pytest.raises(ValueError,match='string or explicit unknown'):V2.project_history(raw,'C')
