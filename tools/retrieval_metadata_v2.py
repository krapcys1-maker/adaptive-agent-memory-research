"""Ground case variants back to an actual source span; never invent an alias."""
import re

from tools.retrieval_metadata_v1 import checked


def canonical_proposal(source,proposal):
    if not isinstance(proposal,dict) or not isinstance(proposal.get('addresses'),list):
        raise ValueError('Expected address proposal.')
    normalized=[]
    for row in proposal['addresses']:
        if not isinstance(row,dict) or not isinstance(row.get('entity'),str) or not row['entity']:
            raise ValueError('Entity text required.')
        entity=row['entity']
        if len(entity)>160 or entity!=entity.strip():
            raise ValueError('Unbounded entity span.')
        match=re.search(r'(?<!\w)'+re.escape(entity)+r'(?!\w)',source.text,re.I)
        if match is None or match.group().casefold()!=entity.casefold():
            raise ValueError('Entity is not a whole literal source span, even ignoring case.')
        normalized.append(dict(row,entity=match.group()))
    result=dict(proposal,addresses=normalized)
    checked(source,result)
    return result
