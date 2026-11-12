"""Model-free label screen for MemoryAgentBench FactConsolidation (SH and MH, 6K/32K/64K/262K).

Rule under test (MemoryAgentBench, arXiv:2507.05257, App. B.4.2): every fact carries a serial number; for a
(subject, relation) key the fact with the larger serial number is the current one ("newest wins").

For every question the screen asks whether the released answer can be obtained by a reasoner that applies that
rule at EVERY hop. No model is called. The grammar is the 36 MQuAKE cloze templates that occur in the contexts
plus the generic office-holder template "The <office> is <person>.".

The benchmark file is not in this repository. Download the Conflict_Resolution parquet of
ai-hyz/MemoryAgentBench (MIT) and pass its path:

    python scripts/mab_fc_label_screen_v1.py --parquet PATH --out DIR

Outputs in DIR: items.jsonl, summary.json, review_mh.txt, review_sh.txt. They quote benchmark questions and
answers, so write them outside the repository. See data/lab/mab-fc-label-screen-v1/README.md.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, re, unicodedata

MAX_HOPS = 4

# (relation id, regex with groups S and O). Specific templates first; the generic office-holder last.
SPECIFIC = [
    ('died_in_city', r'(?P<S>.+?) died in the city of (?P<O>.+)\.'),
    ('citizen_of', r'(?P<S>.+?) is a citizen of (?P<O>.+)\.'),
    ('religion', r'(?P<S>.+?) is affiliated with the religion of (?P<O>.+)\.'),
    ('sport', r'(?P<S>.+?) is associated with the sport of (?P<O>.+)\.'),
    ('employer', r'(?P<S>.+?) is employed by (?P<O>.+)\.'),
    ('famous_for', r'(?P<S>.+?) is famous for (?P<O>.+)\.'),
    ('continent', r'(?P<S>.+?) is located in the continent of (?P<O>.+)\.'),
    ('spouse', r'(?P<S>.+?) is married to (?P<O>.+)\.'),
    ('position', r'(?P<S>.+?) plays the position of (?P<O>.+)\.'),
    ('speaks', r'(?P<S>.+?) speaks the language of (?P<O>.+)\.'),
    ('born_in_city', r'(?P<S>.+?) was born in the city of (?P<O>.+)\.'),
    ('created_in_country', r'(?P<S>.+?) was created in the country of (?P<O>.+)\.'),
    ('created_by', r'(?P<S>.+?) was created by (?P<O>.+)\.'),
    ('developed_by', r'(?P<S>.+?) was developed by (?P<O>.+)\.'),
    ('founded_by', r'(?P<S>.+?) was founded by (?P<O>.+)\.'),
    ('founded_in_city', r'(?P<S>.+?) was founded in the city of (?P<O>.+)\.'),
    ('founded_in', r'(?P<S>.+?) was founded in (?P<O>.+)\.'),
    ('performed_by', r'(?P<S>.+?) was performed by (?P<O>.+)\.'),
    ('written_in_language', r'(?P<S>.+?) was written in the language of (?P<O>.+)\.'),
    ('worked_in_city', r'(?P<S>.+?) worked in the city of (?P<O>.+)\.'),
    ('field_of_work', r'(?P<S>.+?) works in the field of (?P<O>.+)\.'),
    ('child', r"(?P<S>.+?)'s child is (?P<O>.+)\."),
    ('author', r'The author of (?P<S>.+?) is (?P<O>.+)\.'),
    ('capital', r'The capital of (?P<S>.+?) is (?P<O>.+)\.'),
    ('chairperson', r'The chairperson of (?P<S>.+?) is (?P<O>.+)\.'),
    ('ceo', r'The chief executive officer of (?P<S>.+?) is (?P<O>.+)\.'),
    ('producer_company', r'The company that produced (?P<S>.+?) is (?P<O>.+)\.'),
    ('director', r'The director of (?P<S>.+?) is (?P<O>.+)\.'),
    ('head_coach', r'The head coach of (?P<S>.+?) is (?P<O>.+)\.'),
    ('headquarters_city', r'The headquarters of (?P<S>.+?) is located in the city of (?P<O>.+)\.'),
    ('head_of_state', r'The name of the current head of state in (?P<S>.+?) is (?P<O>.+)\.'),
    ('head_of_government', r'The name of the current head of the (?P<S>.+?) government is (?P<O>.+)\.'),
    ('official_language', r'The official language of (?P<S>.+?) is (?P<O>.+)\.'),
    ('original_broadcaster', r'The origianl broadcaster of (?P<S>.+?) is (?P<O>.+)\.'),
    ('original_language', r'The original language of (?P<S>.+?) is (?P<O>.+)\.'),
    ('music_genre', r'The type of music that (?P<S>.+?) plays is (?P<O>.+)\.'),
    ('educated_at', r'The univeristy where (?P<S>.+?) was educated is (?P<O>.+)\.'),
]
GENERIC = ('officeholder', r'The (?P<S>.+?) is (?P<O>.+)\.')
COMPILED = [(name, re.compile(rx + r'$')) for name, rx in SPECIFIC]
GENERIC_C = (GENERIC[0], re.compile(GENERIC[1] + r'$'))
LINE = re.compile(r'^(\d+)\.\s+(.*)$')


def key(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def parse_fact(sentence: str):
    hits = [(name, m.group('S'), m.group('O')) for name, rx in COMPILED if (m := rx.match(sentence))]
    if len(hits) > 1:  # e.g. founded_in_city also matches founded_in: keep the first (more specific) one
        hits = hits[:1]
    if not hits:
        m = GENERIC_C[1].match(sentence)
        if m:
            hits = [(GENERIC_C[0], m.group('S'), m.group('O'))]
    return hits[0] if hits else None


class Graph:
    def __init__(self, context: str):
        self.hist = collections.defaultdict(list)       # (subject_key, relation) -> [(serial, object, sentence)]
        self.name = {}                                  # subject_key -> surface
        self.rels = collections.defaultdict(set)        # subject_key -> relations
        self.rev = collections.defaultdict(set)         # object_key -> subject_keys (any version)
        self.unparsed = []
        self.lines = 0
        for raw in context.split('\n'):
            m = LINE.match(raw.strip())
            if not m:
                continue
            self.lines += 1
            serial, sentence = int(m.group(1)), m.group(2).strip()
            fact = parse_fact(sentence)
            if fact is None:
                self.unparsed.append((serial, sentence)); continue
            rel, s, o = fact
            sk = key(s)
            self.hist[(sk, rel)].append((serial, o, sentence))
            self.name.setdefault(sk, s); self.rels[sk].add(rel); self.rev[key(o)].add(sk)
        for v in self.hist.values():
            v.sort()

    def latest(self, sk, rel):
        return self.hist[(sk, rel)][-1]

    def anchors(self, question: str):
        q = key(question)
        found = [sk for sk in self.name if re.search(r'(?<!\w)' + re.escape(sk) + r'(?!\w)', q)]
        return sorted((a for a in found if not any(a != b and a in b for b in found)), key=lambda a: -len(a))

    def dist_to(self, targets: set, limit: int):
        dist = {t: 0 for t in targets}
        frontier = list(targets)
        for d in range(1, limit + 1):
            nxt = []
            for node in frontier:
                for sk in self.rev.get(node, ()):
                    if sk not in dist:
                        dist[sk] = d; nxt.append(sk)
            frontier = nxt
        return dist

    def paths(self, anchor: str, golds: set, limit: int = MAX_HOPS, cap: int = 400):
        """All simple paths anchor -> gold of at most `limit` hops over ANY historical value."""
        dist = self.dist_to(golds, limit)
        out = []

        def walk(node, hops, visited):
            if len(out) >= cap:
                return
            for rel in sorted(self.rels.get(node, ())):
                history = self.hist[(node, rel)]
                newest = history[-1][0]
                for serial, obj, _ in history:
                    ok = key(obj)
                    step = {'s': self.name[node], 'r': rel, 'o': obj, 'serial': serial, 'is_latest': serial == newest,
                            'latest_o': history[-1][1], 'latest_serial': newest, 'n_versions': len(history)}
                    if ok in golds:
                        out.append(hops + [step])
                    if len(hops) + 1 < limit and ok not in visited and dist.get(ok, 99) <= limit - len(hops) - 1 and ok in self.rels:
                        walk(ok, hops + [step], visited | {ok})

        if dist.get(anchor, 99) <= limit:
            walk(anchor, [], {anchor})
        return out

    def follow_latest(self, anchor: str, relations):
        node = anchor; trail = []
        for rel in relations:
            if (node, rel) not in self.hist:
                return None, trail
            serial, obj, _ = self.latest(node, rel)
            trail.append((self.name.get(node, node), rel, obj, serial)); node = key(obj)
        return trail[-1][2] if trail else None, trail


def classify_mh(g: Graph, question: str, answers):
    golds = {key(a) for a in answers}
    anchors = g.anchors(question)
    allp = []
    for a in anchors:
        for p in g.paths(a, golds):
            allp.append((a, p))
    if not anchors:
        return {'class': 'NO_ANCHOR', 'anchors': [], 'paths': []}
    if not allp:
        return {'class': 'UNREACHABLE', 'anchors': anchors, 'paths': []}
    multi = [x for x in allp if len(x[1]) >= 2]
    pool = multi or allp
    clean = [x for x in pool if all(h['is_latest'] for h in x[1])]
    if clean:
        cls = 'CONSISTENT'
        show = sorted(clean, key=lambda x: len(x[1]))[:3]
    else:
        final_only = [x for x in pool if all(h['is_latest'] for h in x[1][:-1]) and not x[1][-1]['is_latest']]
        cls = 'SUPERSEDED_FINAL_HOP' if final_only else 'SUPERSEDED_INTERMEDIATE_HOP'
        show = sorted(final_only or pool, key=lambda x: (sum(not h['is_latest'] for h in x[1]), len(x[1])))[:4]
    return {'class': cls, 'anchors': anchors, 'n_paths': len(allp), 'only_single_hop_paths': not multi,
            'paths': [{'anchor': a, 'hops': p} for a, p in show]}


def classify_sh(g: Graph, question: str, answers):
    golds = {key(a) for a in answers}
    anchors = g.anchors(question)
    if not anchors:
        return {'class': 'NO_ANCHOR', 'anchors': [], 'hits': []}
    hits = []
    for a in anchors:
        for rel in sorted(g.rels[a]):
            h = g.hist[(a, rel)]
            for serial, obj, _ in h:
                if key(obj) in golds:
                    hits.append({'s': g.name[a], 'r': rel, 'o': obj, 'serial': serial, 'is_latest': serial == h[-1][0],
                                 'latest_o': h[-1][1], 'latest_serial': h[-1][0], 'n_versions': len(h)})
    if not hits:
        return {'class': 'UNREACHABLE', 'anchors': anchors, 'hits': []}
    cls = 'CONSISTENT' if any(x['is_latest'] for x in hits) else 'SUPERSEDED_VALUE'
    return {'class': cls, 'anchors': anchors, 'hits': hits[:4]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--parquet', required=True, type=pathlib.Path, help='MemoryAgentBench Conflict_Resolution parquet')
    ap.add_argument('--out', required=True, type=pathlib.Path, help='output directory (keep it outside the repository)')
    args = ap.parse_args(argv)
    import pyarrow.parquet as pq  # imported here so that the grammar and the classifiers can be tested without it
    HERE = args.out
    HERE.mkdir(parents=True, exist_ok=True)
    rows = pq.read_table(args.parquet).to_pylist()
    items, summary = [], {}
    graphs = {}
    for r in rows:
        src = r['metadata']['source']
        kind, length = src.split('_')[1], src.split('_')[2]
        g = graphs.setdefault(length, Graph(r['context']))
        counts = collections.Counter()
        for i, (q, ans) in enumerate(zip(r['questions'], r['answers'])):
            res = (classify_mh if kind == 'mh' else classify_sh)(g, q, ans)
            counts[res['class']] += 1
            items.append({'variant': src, 'index': i, 'question': q, 'answers': list(ans), **res})
        keys_multi = sum(1 for v in g.hist.values() if len({key(o) for _, o, _ in v}) > 1)
        summary[src] = {'questions': len(r['questions']), 'classes': dict(counts), 'facts': g.lines,
                        'unparsed': len(g.unparsed), 'keys': len(g.hist), 'keys_with_conflicting_history': keys_multi,
                        'max_versions_per_key': max(len(v) for v in g.hist.values())}
    with open(HERE / 'items.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + '\n')
    json.dump(summary, open(HERE / 'summary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    def fmt(h):
        tag = 'LATEST' if h['is_latest'] else 'SUPERSEDED (latest: %s @%d)' % (h['latest_o'], h['latest_serial'])
        return '      [%d] %s --%s--> %s   %s' % (h['serial'], h['s'], h['r'], h['o'], tag)

    with open(HERE / 'review_mh.txt', 'w', encoding='utf-8', newline='\n') as f:
        for it in items:
            if '_mh_' in it['variant'] and it['class'] != 'CONSISTENT':
                f.write('%s #%d  %s\n  Q: %s\n  GOLD: %s  anchors: %s\n' % (it['variant'], it['index'], it['class'], it['question'], it['answers'], it['anchors']))
                for p in it.get('paths', []):
                    f.write('    path:\n' + '\n'.join(fmt(h) for h in p['hops']) + '\n')
                f.write('\n')
    with open(HERE / 'review_sh.txt', 'w', encoding='utf-8', newline='\n') as f:
        for it in items:
            if '_sh_' in it['variant'] and it['class'] != 'CONSISTENT':
                f.write('%s #%d  %s\n  Q: %s\n  GOLD: %s  anchors: %s\n' % (it['variant'], it['index'], it['class'], it['question'], it['answers'], it['anchors']))
                for h in it.get('hits', []):
                    f.write(fmt(h) + '\n')
                f.write('\n')
    for k, v in summary.items():
        print(k, v)


if __name__ == '__main__':
    main()
