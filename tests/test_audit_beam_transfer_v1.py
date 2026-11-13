import json
import pytest
from scripts import prepare_beam_transfer_v2 as B
from scripts.reviews import audit_beam_transfer_v1 as A


def test_reader_gold_leak_is_detected_even_if_output_hash_is_redeclared(tmp_path):
    source=tmp_path/'source';d=source/'1';(d/'probing_questions').mkdir(parents=True)
    raw=[{'plan-1':[{'turns':[[{'role':'user','content':'Original context.','time_anchor':None,'question_type':'hidden'}]]}]}]
    (d/'chat_trunecated.json').write_text(json.dumps(raw),encoding='utf-8')
    probes={k:[{'question':'Question?','answer':'secret','rubric':'Correctness'} for _ in range(2)] for k in B.ABILITIES}
    (d/'probing_questions/probing_questions.json').write_text(json.dumps(probes),encoding='utf-8')
    out=tmp_path/'private';B.prepare(source,out,1)
    result=A.audit(source,out)
    assert result['messages_reconstructed']==1
    assert result['construction_metadata_excluded']=={'question_type':1}
    p=out/'reader/questions.jsonl';rows=B.read_rows(p);rows[0]['answer']='secret'
    p.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    manifest=B.load(out/'manifest.json');manifest['output_files_sha256']['reader/questions.jsonl']=B.sha(p)
    (out/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError,match='Reader question key leak'):A.audit(source,out)
