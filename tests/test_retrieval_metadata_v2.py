import pytest

from tools.structured_memory_v1 import Source
from tools.retrieval_metadata_v2 import canonical_proposal


def proposal(entity):
    return {'addresses':[{'entity':entity,'property':'test_command','kind':'procedure'}]}


def test_case_is_grounded_to_actual_source_spelling():
    source=Source('a','test','Test suite uses pytest.',1)
    fixed=canonical_proposal(source,proposal('test suite'))
    assert fixed['addresses'][0]['entity']=='Test suite'
    assert fixed['addresses'][0]['kind']=='procedure'


@pytest.mark.parametrize('entity',['clean_modules','test','cafe','Mira'])
def test_not_an_alias_or_subword_repair(entity):
    source=Source('a','test','The latest café task belongs to Mirabel.',1)
    with pytest.raises(ValueError):
        canonical_proposal(source,proposal(entity))
