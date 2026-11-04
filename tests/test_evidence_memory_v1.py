import json

import pytest

from tools.evidence_memory_v1 import EvidenceMemory, main
from tools.structured_memory_v1 import Memory, Source


def proposal(entity,property='workspace',kind='fact'):
    return {'addresses':[{'entity':entity,'property':property,'kind':kind}]}


def test_persistent_recall_preserves_scope_time_and_raw_truth(tmp_path,capsys):
    raw,meta=tmp_path/'raw',tmp_path/'meta'
    with Memory(raw,writable=True) as m:
        m.add_source(Source('a','public','Nera workspace is Iris.',1))
        m.add_source(Source('b','secret','Nera workspace is Hidden.',2))
        m.add_source(Source('c','public','Nera workspace is Cedar.',8))
    memory=EvidenceMemory(raw,meta)
    for sid in ['a','b','c']:
        memory.attach(sid,proposal('nera'),source_role='agent_note',provenance='local-test-response:'+sid)
    before={p:p.read_bytes() for p in [raw,meta]}
    fresh=EvidenceMemory(raw,meta)
    assert [r['source'] for r in fresh.recall('public','Nera','workspace',known_at=5)['records']]==['a']
    assert fresh.recall('public','Missing','workspace',known_at=9)['status']=='no_history'
    assert main(['--raw',str(raw),'--metadata',str(meta),'recall','--scope','public','--entity','Nera',
                 '--property','workspace','--known-at','9'])==0
    assert 'Hidden' not in capsys.readouterr().out
    assert all(p.read_bytes()==data for p,data in before.items())
    with Memory(raw) as m: assert not m.claims


def test_revision_is_explicit_and_keeps_prior_attachment(tmp_path):
    raw,meta=tmp_path/'raw',tmp_path/'meta'
    with Memory(raw,writable=True) as m: m.add_source(Source('a','test','Nera must run checks.',1))
    memory=EvidenceMemory(raw,meta)
    first=memory.attach('a',proposal('Nera','checks','instruction'),provenance='response-a')
    assert not memory.attach('a',proposal('Nera','checks','instruction'),provenance='response-a')['added']
    with pytest.raises(ValueError,match='superseded'):
        memory.attach('a',proposal('Nera','checks','procedure'),provenance='response-b')
    second=memory.attach('a',proposal('Nera','checks','procedure'),provenance='response-b',supersedes=first['attachment'])
    assert first['attachment']!=second['attachment']
    assert len(meta.read_text(encoding='utf-8').splitlines())==2
    assert memory.recall('test','Nera','checks',known_at=2)['records'][0]['kinds']==['procedure']


def test_corrupt_derived_log_is_rejected_without_repair(tmp_path):
    raw,meta=tmp_path/'raw',tmp_path/'meta'
    with Memory(raw,writable=True) as m: m.add_source(Source('a','test','Nera runs checks.',1))
    memory=EvidenceMemory(raw,meta)
    memory.attach('a',proposal('Nera'),provenance='response-a')
    meta.write_text(meta.read_text(encoding='utf-8').replace('workspace','corrupted'),encoding='utf-8')
    before=meta.read_bytes()
    with pytest.raises(ValueError,match='Corrupt'):
        memory.recall('test','Nera','workspace',known_at=2)
    assert meta.read_bytes()==before
