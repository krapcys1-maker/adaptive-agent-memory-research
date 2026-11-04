"""Post-diagnosis descriptive follow-up: fixed L1 development seeds 5..24 only.

Inspect actual stream-frequency counts and slot-bearing core/padding layout.
No thresholds, generator settings or canonical gate definitions are modified.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from corpus.lifesim import schema as S
from corpus.lifesim.scorers import Scorer
from lifesim import gates as G
from lifesim import systems as SY
from lifesim.interface import count_units, records_from_world, run_stream


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    groups = defaultdict(lambda: {'n':0, 'words':0, 'core_words':0, 'pre_words':0,
                                  'padding_sentences':0, 'slots':0, 'clause':[0]*4})
    predictions = []
    for seed in range(5,25):
        b = G.make_bundle(seed, S.TierCfg.for_tier('L1'), 'C0')
        ev = G.evidence_oids(b.queries)
        for spec, part, (cp, _) in zip(b.world.obs_specs, b.parts, G.position_bins(b)):
            flag = 'evidence' if spec.oid in ev else 'other'
            for dimension, value in [('kind',part.kind), ('scene',part.scene),
                                     ('slot_count',str(len(spec.slots)))]:
                row = groups[(dimension,value,flag)]
                row['n'] += 1
                row['words'] += count_units(part.text)
                row['core_words'] += count_units(part.core)
                row['pre_words'] += sum(map(count_units,part.pre))
                row['padding_sentences'] += len(part.pre)+len(part.post)
                row['slots'] += len(spec.slots)
                row['clause'][cp] += 1
        scorer = Scorer(b.world)
        def capture(q,a,m):
            slot = SY.infer_slot(q.text)
            cnt = m._counts.get(slot,{})
            predictions.append({'seed':seed,'qid':q.qid,'family':q.family,'ask':q.ask,
                'inferred_slot':slot,'gold':q.gold.value,'guess':a.text,
                'correct':bool(scorer.score(q,a).correct), 'chance':G._item_chance(b.world,q),
                'seen_distinct_values':len(cnt),'mode_stream_count':max(cnt.values(),default=0),
                'gold_stream_count':cnt.get(q.gold.value,0),'stream_counts':dict(sorted(cnt.items()))})
        qs=[q for q in b.queries if q.family in ('IN4','SE4','SE5') and not q.tags.prior_answerable]
        run_stream(SY.Heuristic.for_world(b.world),records_from_world(b.world,b.obs),qs,0,
                   card=b.world.card,on_query=capture)
    payload={'interpretation':'Post-initial-diagnosis characterization, not preregistered or a causal repair.',
        'git_head_at_start':head,'seeds':list(range(5,25)),'tier':'L1','cell':'C0',
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'layout':[{'dimension':d,'value':v,'label':f,**r} for (d,v,f),r in sorted(groups.items())],
        'B0h_stream_predictions':predictions}
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(payload,stream,indent=2,sort_keys=True)
        stream.write('\n')
    print(f'Recorded {len(predictions)} chronological blind predictions and {len(groups)} layout strata.')


if __name__ == '__main__':
    main()
