"""Step 2 of the FactConsolidation label screen (model-free): rule-consistent answers for flagged items and
internal contradictions between released labels. Optionally re-scores a project run at MH 262K.

    python scripts/mab_fc_label_adjudicate_v1.py --parquet PATH --dir DIR [--prepared DIR --runs DIR]

DIR is the output directory of scripts/mab_fc_label_screen_v1.py (it must hold items.jsonl); this script adds
adjudication.jsonl and results.json there. --prepared is a folder with questions.jsonl and gold.jsonl for MH 262K,
--runs a folder whose sub-folders named by --run hold answers.jsonl. Both are private project artifacts.
"""
import argparse, collections, importlib.util, json, pathlib, sys

_spec = importlib.util.spec_from_file_location('mab_fc_label_screen_v1', pathlib.Path(__file__).with_name('mab_fc_label_screen_v1.py'))
A = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = A
_spec.loader.exec_module(A)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--parquet', required=True, type=pathlib.Path)
    ap.add_argument('--dir', required=True, type=pathlib.Path)
    ap.add_argument('--prepared', type=pathlib.Path)
    ap.add_argument('--runs', type=pathlib.Path)
    ap.add_argument('--run', action='append', default=None)
    args = ap.parse_args(argv)
    import pyarrow.parquet as pq
    HERE = args.dir
    rows = pq.read_table(args.parquet).to_pylist()
    ctx = {r['metadata']['source'].split('_')[2]: r['context'] for r in rows}
    graphs = {k: A.Graph(v) for k, v in ctx.items()}
    items = [json.loads(l) for l in open(HERE / 'items.jsonl', encoding='utf-8')]

    # Verdicts entered by the auditor after reading review_mh.txt / review_sh.txt. Default for a flagged item: CONFIRMED.
    MANUAL = {
        ('factconsolidation_mh_32k', 78): ('PROBABLE', 'question wording (institution that created) does not name the religion relation used by the only gold path'),
        ('factconsolidation_mh_64k', 6): ('PROBABLE', 'question names 3 relations, gold path has 4 (developer, founder, citizenship, continent); the final hop is superseded on every gold path'),
        ('factconsolidation_mh_64k', 49): ('PROBABLE', 'question says hails from; the only gold path goes through sport and country of origin; the final hop is superseded'),
        ('factconsolidation_mh_64k', 51): ('PROBABLE', 'garbled question; gold path is producer, founder, citizenship, capital'),
        ('factconsolidation_mh_262k', 17): ('PROBABLE', 'question says founded Duquesne University; gold path goes through religion and founder'),
    }

    adj = []
    used = collections.defaultdict(lambda: collections.defaultdict(set))
    for it in items:
        length = it['variant'].split('_')[2]
        g = graphs[length]
        flagged = it['class'] != 'CONSISTENT'
        if '_mh_' in it['variant']:
            paths = it.get('paths', [])
            for p in paths[:1]:
                for h in p['hops']:
                    used[length][(A.key(h['s']), h['r'])].add((h['o'], h['is_latest'], it['index']))
            if flagged and paths:
                p = paths[0]
                rels = [h['r'] for h in p['hops']]
                value, trail = g.follow_latest(p['anchor'], rels)
                verdict, note = MANUAL.get((it['variant'], it['index']), ('CONFIRMED', ''))
                adj.append({'variant': it['variant'], 'index': it['index'], 'question': it['question'],
                            'released_answer': it['answers'], 'screen_class': it['class'], 'verdict': verdict, 'note': note,
                            'relation_path': rels,
                            'superseded_hops': [{'key': [h['s'], h['r']], 'used': h['o'], 'used_serial': h['serial'],
                                                 'current': h['latest_o'], 'current_serial': h['latest_serial']}
                                                for h in p['hops'] if not h['is_latest']],
                            'rule_consistent_answer': value, 'rule_consistent_trail': trail})
        elif flagged and it.get('hits'):
            # single hop: pick the hit whose relation the question names (only one item has several hits)
            hits = it['hits']
            h = next((x for x in hits if x['r'] == 'worked_in_city'), hits[0]) if 'work' in it['question'] else hits[0]
            adj.append({'variant': it['variant'], 'index': it['index'], 'question': it['question'],
                        'released_answer': it['answers'], 'screen_class': it['class'], 'verdict': 'CONFIRMED', 'note': '',
                        'relation_path': [h['r']],
                        'superseded_hops': [{'key': [h['s'], h['r']], 'used': h['o'], 'used_serial': h['serial'],
                                             'current': h['latest_o'], 'current_serial': h['latest_serial']}],
                        'rule_consistent_answer': h['latest_o'], 'rule_consistent_trail': []})

    with open(HERE / 'adjudication.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for a in adj:
            f.write(json.dumps(a, ensure_ascii=False) + '\n')

    res = {'per_variant': {}, 'contradictions': {}}
    for v in sorted({it['variant'] for it in items}):
        sub = [it for it in items if it['variant'] == v]
        a = [x for x in adj if x['variant'] == v]
        res['per_variant'][v] = {
            'questions': len(sub),
            'consistent_upper_bound': sum(it['class'] == 'CONSISTENT' for it in sub),
            'flagged': len(a),
            'confirmed': sum(x['verdict'] == 'CONFIRMED' for x in a),
            'probable': sum(x['verdict'] == 'PROBABLE' for x in a),
            'superseded_final_hop': sum(x['screen_class'] in ('SUPERSEDED_FINAL_HOP', 'SUPERSEDED_VALUE') for x in a),
            'superseded_intermediate_hop': sum(x['screen_class'] == 'SUPERSEDED_INTERMEDIATE_HOP' for x in a),
            'rule_consistent_answer_differs': sum(x['rule_consistent_answer'] is not None and A.key(x['rule_consistent_answer']) not in {A.key(y) for y in x['released_answer']} for x in a),
            'rule_consistent_answer_missing': sum(x['rule_consistent_answer'] is None for x in a),
        }

    # Internal contradictions: one (subject, relation) key used with two different values by the gold paths of
    # two questions of the same context. This needs no reading of question wording.
    for length, keys in used.items():
        bad = {k: v for k, v in keys.items() if len({o for o, _, _ in v}) > 1}
        res['contradictions'][length] = {
            'keys_used_with_two_values': len(bad),
            'questions_involved': len({i for v in bad.values() for _, _, i in v}),
            'examples': [{'key': list(k), 'uses': sorted([o, 'latest' if l else 'superseded', 'Q%d' % i] for o, l, i in v)}
                         for k, v in list(bad.items())[:5]]}

    # Optional: re-score project runs at MH 262K (private artifacts; skipped when the folders are not given).
    if args.prepared and args.runs:
        rd = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
        qs = rd(args.prepared / 'questions.jsonl')
        gold = {r['id']: r['answers'] for r in rd(args.prepared / 'gold.jsonl')}
        mh = next(r for r in rows if r['metadata']['source'] == 'factconsolidation_mh_262k')
        assert [q['question'] for q in qs] == list(mh['questions']), 'prepared question order differs from the parquet'
        adj262 = {a['index']: a for a in adj if a['variant'] == 'factconsolidation_mh_262k'}
        res['project_262k'] = {}
        for run in (args.run or ['local-path-answers', 'flash-path-answers']):
            ans = {a['id']: a for a in rd(args.runs / run / 'answers.jsonl')}
            c = collections.Counter()
            for i, q in enumerate(qs):
                v = ans[q['id']]['result'].get('value')
                ok = isinstance(v, str) and A.key(v) in {A.key(x) for x in gold[q['id']]}
                fl = adj262.get(i)
                c['released_correct'] += ok
                if fl is None:
                    c['unflagged'] += 1
                    c['unflagged_correct'] += ok
                else:
                    c['flagged'] += 1
                    c['flagged_released_correct'] += ok
                    rc = fl['rule_consistent_answer']
                    c['flagged_answer_equals_rule_consistent'] += (isinstance(v, str) and rc is not None and A.key(v) == A.key(rc))
                    c['flagged_no_answer'] += (not isinstance(v, str))
            res['project_262k'][run] = dict(c)

    json.dump(res, open(HERE / 'results.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(res['per_variant'], indent=0))
    print(json.dumps(res.get('project_262k', {})))
    print(json.dumps({k: {x: v[x] for x in ('keys_used_with_two_values', 'questions_involved')} for k, v in res['contradictions'].items()}))
    print(json.dumps(res['contradictions']['6k']['examples'], ensure_ascii=False)[:1200])



if __name__ == '__main__':
    main()
