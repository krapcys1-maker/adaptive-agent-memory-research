from types import SimpleNamespace

from tools.evidence_candidates_v1 import candidates
from tools.retrieval_metadata_v1 import AddressView
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory


def test_original_note_survives_failed_metadata_and_future_private_are_excluded(tmp_path):
    raw=tmp_path/'m'
    with Memory(raw,writable=True) as m:
        for s in [Source('old','public','Nera workspace used to be Cedar.',1),
                  Source('new','public','Correction: Nera workspace is Iris.',4),
                  Source('future','public','Nera workspace is Future.',9),
                  Source('private','secret','Nera workspace is Hidden.',2)]:
            m.add_source(s)
    metadata=[{'source':'old','proposal':{'addresses':[{'entity':'Nera','property':'workspace','kind':'fact'}]}}]
    indexed=[]
    fake=SimpleNamespace(PROFILES={'lexical':{}},Item=lambda sid,*a:SimpleNamespace(id=sid),
        build_index=lambda items,day:indexed.extend(i.id for i in items),
        retrieve=lambda *a:{'status':'ok','items':[SimpleNamespace(id='old')]})
    with AddressView(Memory(raw),metadata) as view:
        ids,trace=candidates(view,'public','Where is Nera workspace?',5,fake,lambda day:f'2026-01-{day:02d}')
        assert set(ids)=={'old','new'}
        assert set(indexed)=={'old','new'}
        assert trace['pools']==[{'anchor':'Nera','available_sources':2}]
