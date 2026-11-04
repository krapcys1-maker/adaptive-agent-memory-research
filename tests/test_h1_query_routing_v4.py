import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import h1_query_routing_v4 as V4
from tools.structured_memory_v1 import Source
from tools.structured_memory_v2 import Memory
from tools.retrieval_metadata_v1 import AddressView


def test_routes_synonymous_captured_properties_without_values_or_gold(tmp_path):
    raw=tmp_path/'m'
    sources=[Source('a','test','Nera workplace is Iris.',1),
             Source('b','test','The workplace for Nera changed to Cedar.',4),
             Source('c','test','Nera production site is Hidden.',2),
             Source('d','test','Nera workplace will be Future.',9),
             Source('e','private','Nera workplace is Secret.',3)]
    metadata=[]
    with Memory(raw,writable=True) as m:
        for source in sources: m.add_source(source)
    for sid,entity,prop in [('a','Nera','workspace'),('b','workplace for Nera','work_location'),
                             ('c','Nera','production_site'),('d','Nera','future_only'),('e','Nera','private_only')]:
        metadata.append({'source':sid,'proposal':{'addresses':[{'entity':entity,'property':prop,'kind':'fact'}]}})
    with AddressView(Memory(raw),metadata) as view:
        choices=V4.catalog(view,'test','Where is Nera workplace?',5,['a'])
        assert set(choices['Nera'])=={'workspace','work_location','production_site'}
        packed=json.dumps(V4.route_messages('Where is Nera workplace?',choices))
        assert all(value not in packed for value in ['Iris','Cedar','Hidden','Secret','Future'])
        plan={'entity':'Nera','properties':['workspace','work_location']}
        assert V4.selected_sources(view,'test',plan,5,choices)==['b','a']
        assert not V4.selected_sources(view,'test',{'entity':'Nera','properties':['invented']},5,choices)
        assert V4.selected_sources(view,'private',plan,5,choices)==[]


def test_retrieval_subject_match_is_not_an_unbounded_substring():
    assert V4.literal('The record for Nera says Iris.','Nera')
    assert not V4.literal('The record for Nerabel says Iris.','Nera')
