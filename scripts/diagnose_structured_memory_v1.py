"""Post-hoc, model-free decomposition. Never used to construct an inference plan."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import string

import structured_memory_paths_v5 as V5
import nie_reader_pilot as P


def normalized(text):
    # Same normalization as the pinned upstream utils/eval_other_utils.py.
    text=''.join(c for c in text.lower() if c not in string.punctuation)
    return ' '.join(re.sub(r'\b(a|an|the)\b',' ',text).split())


def subem(value, gold):
    return isinstance(value,str) and any(normalized(g) in normalized(value) for g in gold if normalized(g))


class Oldest(V5.Memory):
    """Deliberately wrong state intervention, same latest-state-selected plans.

    This is not an independent end-to-end baseline: option selection is held
    fixed. It demonstrates sensitivity to the source versions used by execution.
    """
    def resolve(self, scope, subject, predicate, *, valid_at, known_at):
        eligible=[c for c in self.by_key.get((scope,V5.key(subject),predicate),[])
                  if self.sources[c.source].recorded<=known_at and
                  self.sources[c.source].start<=valid_at and c.polarity=='affirm']
        if not eligible:
            return {'status':'no_evidence','values':[],'sources':[]}
        first=min(eligible,key=lambda c:(self.sources[c.source].start,self.sources[c.source].recorded))
        return {'status':'ok','values':[first.object],'sources':[first.source]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['store','questions','gold','answers','output','details']:
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    questions={r['id']:r['question'] for r in P.read_rows(args.questions)}
    gold={r['id']:r['answers'] for r in P.read_rows(args.gold)}
    answers=P.read_rows(args.answers/'answers.jsonl')
    counts=Counter(); details=[]
    with V5.Memory(args.store) as m, Oldest(args.store) as old:
        for row in answers:
            qid=row['id']; expected=gold[qid]
            plans,trace=V5.options(m,'mab-dev',questions[qid],valid_at=20000,known_at=20000)
            values=[]
            for plan in plans:
                result=m.execute('mab-dev',questions[qid],plan,valid_at=20000,known_at=20000)
                values.append(result.get('value'))
            actual=row['result'].get('value')
            exact=isinstance(actual,str) and actual.casefold().strip() in {g.casefold().strip() for g in expected}
            official=subem(actual,expected)
            coverage=any(subem(v,expected) for v in values)
            old_result=old.execute('mab-dev',questions[qid],row['plan'],valid_at=20000,known_at=20000)
            counts['exact']+=exact; counts['upstream_subem']+=official
            counts['gold_in_any_enumerated_path_posthoc']+=coverage
            counts['correct_path_available_but_not_selected']+=coverage and not official
            counts['gold_not_in_enumerated_paths']+=not coverage
            counts['oldest_intervention_subem']+=subem(old_result.get('value'),expected)
            counts['state_intervention_changes_output']+=actual!=old_result.get('value')
            details.append({'id':qid,'exact':exact,'subem':official,'gold_path_available':coverage,
                            'oldest_subem':subem(old_result.get('value'),expected),
                            'selected_value':actual,'gold':expected,'possible_values':values,
                            'question':questions[qid]})
    P.write(args.details,details)
    P.write(args.output,{'n':len(answers),'counts':dict(counts),
        'semantics':'Post-hoc diagnostic and fixed-plan state intervention. No change to primary exact scores, no new inference calls, no claimed universal/oracle upper bound.',
        'upstream_metric_source':'https://github.com/HUST-AI-HYZ/MemoryAgentBench/blob/538026089d1a8a8eff05121d0db89b388f360eba/utils/eval_other_utils.py#L27',
        'details_sha256':V5.V1.file_sha(args.details)})
    print(json.dumps(dict(counts),indent=2))


if __name__=='__main__':
    main()
