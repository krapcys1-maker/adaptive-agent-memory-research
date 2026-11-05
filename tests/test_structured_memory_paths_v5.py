import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import structured_memory_paths_v5 as V5
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory


def put(m,sid,scope,text,s,p,o):
    m.add_source(Source(sid,scope,text,1))
    m.extract(sid,{'claims':[{'subject':s,'predicate':p,'object':o}]},learn=True)


def test_options_are_executable_without_terminal_answers_in_model_input(tmp_path):
    path=tmp_path/'m'
    with Memory(path,writable=True) as m:
        put(m,'a','public','Mira lives in Koral.','Mira','lives_in','Koral')
        put(m,'b','public','Koral belongs to Zefir.','Koral','belongs_to','Zefir')
        put(m,'c','secret','SecretOmega says Uma lives in Hush.','Uma','lives_in','Hush')
    with V5.Memory(path) as m:
        plans,trace=V5.options(m,'public','Which country contains Mira?',valid_at=3,known_at=3)
        assert len(plans)==2
        packed=json.dumps(V5.messages(m,'Which country contains Mira?',plans,'public'))
        for forbidden in ['Koral','Zefir','SecretOmega','Hush','Uma']:
            assert forbidden not in packed
        assert m.execute('public','Which country contains Mira?',plans[-1],valid_at=3,known_at=3)['value']=='Zefir'
        assert not trace['search_truncated']


def test_query_view_refuses_writes_before_touching_path(tmp_path):
    with pytest.raises(ValueError,match='read-only'):
        V5.Memory(tmp_path/'m',writable=True)
    assert not list(tmp_path.iterdir())


def test_unknown_anchor_has_no_options_and_cannot_create_a_fact(tmp_path):
    path=tmp_path/'m'
    with Memory(path,writable=True) as m:
        put(m,'a','public','Mira lives in Koral.','Mira','lives_in','Koral')
    before=path.read_bytes()
    with V5.Memory(path) as m:
        plans,trace=V5.options(m,'public','Where is Nobody?',valid_at=3,known_at=3)
        assert plans==[]
        assert trace['literal_anchors']==[]
    assert path.read_bytes()==before
