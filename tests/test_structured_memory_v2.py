from tools.structured_memory_v1 import Source, Claim, Template
from tools.structured_memory_v2 import Memory, informative


def test_function_only_shell_cannot_capture_unseen_attributes():
    bare = Template.learn('Mira is Koral.', Claim('a','Mira','is','Koral'))
    specific = Template.learn('The keeper of Atrium is Mira.', Claim('a','Atrium','keeper','Mira'))
    assert not informative(bare)
    assert informative(specific)


def test_specific_shell_wins_over_general_without_new_model_call(tmp_path):
    with Memory(tmp_path/'m',writable=True) as m:
        examples = [('a','The keeper of Atrium is Mira.','Atrium','keeper','Mira'),
                    ('b','Atrium is Koral.','Atrium','is','Koral')]
        for sid,text,s,p,o in examples:
            m.add_source(Source(sid,'test',text,1))
            m.extract(sid,{'claims':[{'subject':s,'predicate':p,'object':o}]},learn=True)
        m.add_source(Source('c','test','The keeper of Zefir is Uma.',2))
        assert m.cached('c').subject == 'Zefir'
        assert m.cached('c').predicate == 'keeper'
        m.add_source(Source('d','test','The pilot of Zefir is Uma.',2))
        assert m.cached('d') is None
    with Memory(tmp_path/'m') as m:
        assert m.cached('c').object == 'Uma'
        assert len(m.templates) == 1
