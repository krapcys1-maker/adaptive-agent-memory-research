from dataclasses import replace
import hashlib
import json
import sqlite3
import pytest
from tools import source_windows_v1 as W


def source(text='A factual record.',**kwargs):
    return W.Source('s1','scope-a',text,'user',0,**kwargs)


@pytest.mark.parametrize('text',['a','a'*701,'zażółć gęślą jaźń '*31,'🔧👩\u200d💻 e\u0301\n'*37,'x\n'+'word '*101+'TAIL'])
@pytest.mark.parametrize('cap,overlap',[(4,0),(17,3),(128,19),(1600,160)])
def test_unicode_exact_coverage_offsets_and_deterministic_ids(text,cap,overlap):
    s=source(text,time_anchor_raw=None);windows=list(W.split(s,max_text_bytes=cap,overlap_bytes=overlap))
    assert W.verify(s,windows)['source_bytes']==len(text.encode())
    assert windows==list(W.split(s,max_text_bytes=cap,overlap_bytes=overlap))
    rebuilt=b'';end=0
    for w in windows:
        assert len(w.text.encode())<=cap
        assert text[w.char_start:w.char_end]==w.text
        assert text.encode()[w.byte_start:w.byte_end].decode()==w.text
        rebuilt+=w.text.encode()[max(0,end-w.byte_start):];end=w.byte_end
    assert rebuilt.decode()==text and end==len(text.encode())


def test_large_unbroken_source_is_not_dropped_or_truncated():
    s=source('X'*329788+'🔧TAIL')
    windows=list(W.split(s));W.verify(s,windows)
    assert len(windows)>100 and windows[-1].text.endswith('🔧TAIL')
    assert windows[-1].byte_end==len(s.text.encode())


@pytest.mark.parametrize('change',[{'byte_start':1},{'char_end':1},{'role':'assistant'},{'known_sequence':3},{'time_anchor_raw':'guessed tomorrow'},{'source_sha256':'forged'}])
def test_forged_spans_and_source_metadata_fail(change):
    s=source('żółw '+('policy '*80));windows=list(W.split(s,max_text_bytes=96,overlap_bytes=8))
    windows[0]=replace(windows[0],**change)
    with pytest.raises(ValueError):W.verify(s,windows)


def test_tail_gap_and_reordered_windows_fail():
    s=source('abcdef '*100);windows=list(W.split(s,max_text_bytes=64,overlap_bytes=4))
    with pytest.raises(ValueError):W.verify(s,windows[:-1])
    with pytest.raises(ValueError):W.verify(s,[windows[1],windows[0],*windows[2:]])
    assert list(W.split(s))[0].id!=list(W.split(replace(s,role='tool')))[0].id


def test_visibility_and_integer_clocks_are_strict():
    with pytest.raises(ValueError):replace(source(),known_sequence=True)
    w=list(W.split(source()))
    with pytest.raises(ValueError):replace(w[0],known_sequence=False)
    with pytest.raises(ValueError):W.render_packet('Question',w,scope='other',known_at=1)
    with pytest.raises(ValueError):W.render_packet('Question',w,scope='scope-a',known_at=True)
    future=list(W.split(replace(source(),known_sequence=9)))
    with pytest.raises(ValueError):W.render_packet('Question',future,scope='scope-a',known_at=1)


def test_full_message_budget_accounts_for_headers_unicode_escapes_and_question():
    s=source('🔧'*80+' policy must stay enabled.');windows=list(W.split(s,max_text_bytes=100,overlap_bytes=8))
    empty=W.render_packet('What is the policy?',[],scope=s.scope,known_at=0)
    cap=max(empty['message_bytes'].values())+500
    packet=W.render_packet('What is the policy?',windows,scope=s.scope,known_at=0,max_message_bytes=cap)
    assert all(n<=cap for n in W.message_bytes(packet['messages']).values())
    assert packet['omitted_ids']
    payload=json.loads(packet['messages'][1]['content'])
    assert payload['history']['omitted_candidates']==len(packet['omitted_ids'])
    assert [m['role'] for m in packet['messages']]==['system','user']
    with pytest.raises(ValueError,match='alone exceed'):W.render_packet('X'*10000,[],scope=s.scope,known_at=0,max_message_bytes=cap)


def test_foreign_and_future_sources_cannot_change_ranking_or_model_packet(tmp_path):
    visible=[W.Source('a','public','alpha beta note','user',0),W.Source('b','public','beta gamma note','assistant',1)]
    hidden=[W.Source('future','public','futuremarker alpha '*200,'user',9),W.Source('secret','private','alpha beta '*2000,'user',0)]
    one=tmp_path/'one.sqlite';two=tmp_path/'two.sqlite';later=tmp_path/'later.sqlite'
    W.build_snapshot(one,visible,scope='public',known_at=1)
    W.build_snapshot(two,[*visible,*hidden],scope='public',known_at=1)
    W.build_snapshot(later,[*visible,*hidden],scope='public',known_at=9)
    with W.Snapshot(one,scope='public',known_at=1) as a,W.Snapshot(two,scope='public',known_at=1) as b:
        x=a.search(['alpha','beta'],scope='public',known_at=1);y=b.search(['alpha','beta'],scope='public',known_at=1)
        assert x and x==y
        assert W.render_packet('Question?',x,scope='public',known_at=1)==W.render_packet('Question?',y,scope='public',known_at=1)
        assert not b.search(['futuremarker'],scope='public',known_at=1)
        with pytest.raises(ValueError):b.search(['alpha'],scope='public',known_at=9)
    with W.Snapshot(later,scope='public',known_at=9) as c:
        assert c.search(['futuremarker'],scope='public',known_at=9)
    with pytest.raises(ValueError):W.Snapshot(one,scope='private',known_at=1)


def test_snapshot_is_read_only_exclusive_and_detects_changed_source(tmp_path):
    path=tmp_path/'snapshot with spaces.sqlite';s=source('alpha current policy')
    W.build_snapshot(path,[s],scope=s.scope,known_at=0)
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):W.build_snapshot(path,[s],scope=s.scope,known_at=0)
    with W.Snapshot(path,scope=s.scope,known_at=0) as snapshot:
        assert snapshot.search(['alpha'],scope=s.scope,known_at=0)
        with pytest.raises(sqlite3.OperationalError):snapshot.connection.execute('DELETE FROM sources')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    db=sqlite3.connect(path);body=json.loads(db.execute('SELECT body FROM sources').fetchone()[0]);body['text']='Altered original'
    db.execute('UPDATE sources SET body=?',(json.dumps(body),));db.commit();db.close()
    with W.Snapshot(path,scope=s.scope,known_at=0) as snapshot:
        with pytest.raises(ValueError,match='original source'):snapshot.search(['alpha'],scope=s.scope,known_at=0)


def test_duplicate_sources_leave_an_incomplete_snapshot_not_an_overwrite(tmp_path):
    path=tmp_path/'duplicate.sqlite';s=source()
    with pytest.raises(sqlite3.IntegrityError):W.build_snapshot(path,[s,s],scope=s.scope,known_at=0)
    assert path.exists()
    with pytest.raises(ValueError):W.Snapshot(path,scope=s.scope,known_at=0)
