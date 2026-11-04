"""Read-only, exploratory LifeSim gate diagnosis; never run sealed/confirmation seeds.

Run from the repository root:
    python scripts/reviews/lifesim_development_diagnosis.py --output NEW_DIRECTORY
Existing instrument code is imported unchanged. Feature ablations temporarily replace
only an in-memory feature callback and are never reported as canonical gate passes.
This operational runner does not change the deterministic instrument. Timing and
execution metadata belong here, outside the clock-free lifesim library package.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))

# Bound BLAS parallelism before numpy/scipy are imported; this does not alter the grid.
for _key in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS'):
    os.environ[_key] = '1'

from corpus.lifesim import schema as S
from corpus.lifesim.appraisal import spearman
from corpus.lifesim.scorers import Scorer
from lifesim import gates as G
from lifesim import systems as SY
from lifesim.interface import records_from_world, run_stream


def validate_seeds(seeds):
    if not seeds or len(set(seeds)) != len(seeds) or any(s < 0 or s > 999 for s in seeds):
        raise ValueError('Use distinct development seeds 0..999 only; no sealed epoch.')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def source_digests():
    files = list((ROOT / 'scripts/corpus/lifesim').glob('*.py'))
    files += list((ROOT / 'scripts/lifesim').glob('*.py'))
    files += [Path(__file__), ROOT / 'data/lab/aam-lifesim/config.json',
              ROOT / 'docs/00-project/lifesim-development-diagnosis-protocol-2026-11-04.md']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in files if p.is_file()}


def gold_concentration(bundles):
    """Per-world/family/ask gold modes; these are not a blind arm's fitted accuracy."""
    rows = []
    for b in bundles:
        groups = defaultdict(Counter)
        for q in b.queries:
            if q.family != 'ME1' and not q.tags.prior_answerable:
                groups[(q.family, q.ask)][q.gold.value] += 1
        for (family, ask), counts in sorted(groups.items()):
            n = sum(counts.values())
            rows.append({'seed': b.seed, 'family': family, 'ask': ask, 'n': n,
                         'modal_gold_count': max(counts.values()),
                         'modal_gold_share': max(counts.values()) / n,
                         'distinct_gold': len(counts), 'gold_counts': dict(sorted(counts.items()))})
    return rows


def blind_diagnosis(bundles):
    groups = defaultdict(lambda: {'n': 0, 'correct': 0, 'chance_sum': 0.0,
                                 'predictions': Counter(), 'gold': Counter(), 'correct_predictions': Counter()})
    for b in bundles:
        mem = [q for q in b.queries if q.family != 'ME1' and not q.tags.prior_answerable]
        scorer = Scorer(b.world)
        for q, a in run_stream(SY.Heuristic.for_world(b.world), records_from_world(b.world, b.obs),
                               mem, 0, card=b.world.card):
            r = groups[(q.family, q.ask)]
            r['n'] += 1
            r['chance_sum'] += G._item_chance(b.world, q)
            r['correct'] += int(scorer.score(q, a).correct)
            r['predictions'][a.text] += 1
            r['gold'][q.gold.value] += 1
            if scorer.score(q, a).correct:
                r['correct_predictions'][a.text] += 1
    rows = []
    for (family, ask), row in sorted(groups.items()):
        rows.append({'family': family, 'ask': ask, **row,
                     'accuracy': row['correct'] / row['n'], 'chance': row['chance_sum'] / row['n']})
    return {'by_family_ask': rows, 'per_world_gold_concentration': gold_concentration(bundles)}


def feature_groups():
    names = ('length', 'digits', 'rare_share', 'capitals', 'day_position', 'day_offset')
    channels = len(S.CHANNELS)
    rows = {'numeric': (list(range(6)), [])}
    rows.update({name: ([i], []) for i, name in enumerate(names)})
    rows.update({'skeleton': ([], list(range(32))),
                 'channel': ([], list(range(32, 32 + channels))),
                 'ngrams': ([], list(range(32 + channels, 32 + channels + 256))),
                 'all_minus_rare': ([0, 1, 3, 4, 5], list(range(32 + channels + 256))),
                 'all_minus_ngrams': (list(range(6)), list(range(32 + channels)))})
    return rows


def tell_ablations(bundles, cached, emit):
    rows = {}
    for name, (num, cat) in feature_groups().items():
        matrices = {id(b): (cached[id(b)][0][:, num], cached[id(b)][1][:, cat]) for b in bundles}
        with patch.object(G, '_surface_matrix', side_effect=lambda b: matrices[id(b)]):
            result = G.g_tell(bundles, targets_to_test=('evidence',))
        rows[name] = result.to_dict()
        emit('tell-' + name, rows[name])
    proxy = {id(b): G._surface_matrix(dataclasses.replace(b, parts=None)) for b in bundles}
    with patch.object(G, '_surface_matrix', side_effect=lambda b: proxy[id(b)]):
        rows['all_text_prefix_proxy'] = G.g_tell(bundles, targets_to_test=('evidence',)).to_dict()
    emit('tell-text-prefix-proxy', rows['all_text_prefix_proxy'])
    return rows


def surface_diagnosis(bundles, cached):
    frames = defaultdict(lambda: {'evidence': {'n': 0, 'clause': [0]*4, 'words': 0, 'slots': 0},
                                 'other': {'n': 0, 'clause': [0]*4, 'words': 0, 'slots': 0}})
    world_rows = []
    pooled = {'GS': ([], []), 'rare_share': ([], [])}
    for b in bundles:
        ev = G.evidence_oids(b.queries)
        bins = G.position_bins(b)
        rare = cached[id(b)][0][:, 2].tolist()
        recs = sorted(records_from_world(b.world, b.obs), key=lambda r: r.timestamp)
        gate = SY.GatedMemory(SY.BM25Time(b.cfg.start_date), 'GS', .10, b.seed)
        gate.reset(b.world.card)
        weights = {r.id: gate._weight(r) for r in recs}
        gs = [weights[s.oid] for s in b.world.obs_specs]
        flags = [s.oid in ev for s in b.world.obs_specs]
        row = {'seed': b.seed, 'n': len(flags), 'evidence': sum(flags),
               'GS_rare_spearman': spearman(gs, rare)}
        for name, values in (('GS', gs), ('rare_share', rare)):
            pos = [v for v, flag in zip(values, flags) if flag]
            neg = [v for v, flag in zip(values, flags) if not flag]
            row[name] = {'auc': G.auc(pos, neg), 'evidence_mean': sum(pos)/len(pos),
                         'other_mean': sum(neg)/len(neg)}
            pooled[name][0].extend(pos)
            pooled[name][1].extend(neg)
        world_rows.append(row)
        for s, o, (cp, _tp) in zip(b.world.obs_specs, b.obs, bins):
            r = frames[s.frame]['evidence' if s.oid in ev else 'other']
            r['n'] += 1
            r['clause'][cp] += 1
            r['words'] += len(o.text.split())
            r['slots'] += len(s.slots)
    return {'by_world': world_rows, 'pooled_auc': {k: G.auc(*v) for k, v in pooled.items()},
            'by_frame': dict(sorted(frames.items()))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--seeds', type=int, nargs='+', default=list(range(5, 25)))
    args = ap.parse_args(argv)
    validate_seeds(args.seeds)
    args.output.mkdir(parents=True, exist_ok=False)
    before = source_digests()
    start = time.monotonic()

    def emit(name, result):
        (args.output / (name + '.json')).write_text(json.dumps(result, indent=2, sort_keys=True)+'\n',
                                                  encoding='utf-8', newline='\n')
        print(f'{time.monotonic()-start:.1f}s {name}', flush=True)

    cfg = S.TierCfg.for_tier('L1')
    bundles = [G.make_bundle(s, cfg, 'C0') for s in args.seeds]
    canonical = {}
    for name in G.GATE_NAMES:
        canonical[name] = G.x0_gates(bundles, include=(name,))[name].to_dict()
        emit('canonical-' + name, canonical[name])
    cached = {id(b): G._surface_matrix(b) for b in bundles}
    emit('blind-diagnosis', blind_diagnosis(bundles))
    emit('surface-diagnosis', surface_diagnosis(bundles, cached))
    emit('depth-prefixes', [{'worlds': i, 'seeds': args.seeds[:i], **G.g_depth(bundles[:i]).to_dict()}
                            for i in range(1, len(bundles)+1)])
    tell_ablations(bundles, cached, emit)
    feas = {}
    identities = []
    for cell in ('C0', 'C0r', 'C+', 'C-'):
        bs = bundles if cell == 'C0' else [G.make_bundle(s, cfg, cell) for s in args.seeds]
        for r in (.10, .25):
            result = G.g_feas(bs, r).to_dict()
            feas[f'{cell}@{r}'] = result
            emit(f'feas-{cell}-{r}', result)
        if cell == 'C0r':
            for old, new in zip(bundles, bs):
                identities.append({'seed': old.seed,
                    'world_equal': old.world.to_json() == new.world.to_json(),
                    'observations_equal': old.obs == new.obs,
                    'queries_equal': old.queries == new.queries,
                    'C0_query_digest': digest([q.to_json() for q in old.queries]),
                    'C0r_query_digest': digest([q.to_json() for q in new.queries])})
    emit('cell-identities', identities)
    after = source_digests()
    if before != after:
        raise RuntimeError('Input/source files changed during diagnosis.')
    emit('manifest', {'tier': 'L1', 'seeds': args.seeds, 'partition': 'development',
        'interpretation': 'Descriptive diagnosis; canonical failures remain failures. No instrument changed.',
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.version, 'platform': platform.platform(), 'source_sha256': before,
        'source_unchanged': True, 'elapsed_seconds': time.monotonic()-start,
        'failed_canonical_gates': [k for k,v in canonical.items() if v['passed'] is False]})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
