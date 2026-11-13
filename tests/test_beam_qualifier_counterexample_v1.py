"""Reproduce a literal-quote guard limitation; passing means the defect exists."""
import json
from scripts import beam_reader_evidence_v1 as B


def test_valid_source_span_can_lose_hypothetical_frame_and_pass_literal_guard():
    frame='All quotations below are hypothetical examples. No actual conversation is recorded.\n'
    claim='Rika recommended using route blue.'
    source=B.W.Source('synthetic-example','scope',frame+'Neutral context filler. '*100+'\n'+claim,'assistant',0)
    windows=list(B.W.split(source));B.W.verify(source,windows)
    tail=next(w for w in reversed(windows) if claim in w.text)
    assert frame not in tail.text and tail.char_start>len(frame)
    packet=B.project('What did Rika actually recommend?',[tail],scope='scope',known_at=0,system=B.C_SYSTEM,total_candidates=len(windows))
    reply=json.dumps({'answer':claim,'unknown':False,'evidence':[{'window':'E0','quote':claim}]})
    result=B.grade_output(reply,'C',packet['messages'],packet['aliases'])
    assert result['valid_output'] and result['guard_reason']=='literal_evidence_valid'
    assert result['delivered_answer']==claim
    # This is structurally accepted but not an actual observed recommendation.
    # A passing test documents the missing semantic-frame boundary; no repair
    # or memory-accuracy gain is claimed.
