"""Offline successor CLI: exact-text cache, visible plans and query packets.

No model or credential. `extract` attaches a separately supplied interpretation;
`cache` inspects and `replay` persists a validated exact derivation, if available.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.structured_memory_v1 import Source
from tools.structured_memory_v3 import Memory, CACHE_POLICY
from tools.structured_paths_v1 import QueryView, options, messages


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['source', 'extract']:
        p = sub.add_parser(name); p.add_argument('--input', type=Path, required=True)
        if name == 'extract':
            p.add_argument('--source-id', required=True); p.add_argument('--learn', action='store_true')
    sub.add_parser('status')
    for name in ['cache', 'replay']:
        p = sub.add_parser(name); p.add_argument('--source-id', required=True)
    for name in ['resolve', 'query', 'packet']:
        p = sub.add_parser(name)
        p.add_argument('--scope', required=True)
        p.add_argument('--valid-at', type=int, required=True); p.add_argument('--known-at', type=int, required=True)
        if name == 'resolve':
            p.add_argument('--subject', required=True); p.add_argument('--predicate', required=True)
        else:
            p.add_argument('--question', required=True)
            if name == 'query': p.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args(argv)
    cls = QueryView if args.command == 'packet' else Memory
    writable = args.command in ['source', 'extract', 'replay']
    with cls(args.store, writable=writable) as memory:
        if args.command == 'source':
            source = Source(**json.loads(args.input.read_text(encoding='utf-8')))
            result = {'added': memory.add_source(source), 'source': asdict(source)}
        elif args.command == 'extract':
            proposal = json.loads(args.input.read_text(encoding='utf-8'))
            result = {'claims': [asdict(c) for c in memory.extract(args.source_id, proposal, learn=args.learn)]}
        elif args.command in ['cache', 'replay']:
            result = memory.cache_info(args.source_id)
            if args.command == 'replay' and result['claim']:
                claim = {k:v for k,v in result['claim'].items() if k!='source'}
                result['persisted'] = [asdict(c) for c in memory.extract(args.source_id, {'claims': [claim]}, method='template')]
        elif args.command == 'status':
            result = {'cache_policy': CACHE_POLICY, 'sources': len(memory.sources),
                      'claims': len(memory.claims), 'events': memory.events, 'head': memory.head}
        elif args.command == 'resolve':
            result = memory.resolve(args.scope, args.subject, args.predicate, valid_at=args.valid_at, known_at=args.known_at)
        elif args.command == 'packet':
            plans, trace = options(memory, args.scope, args.question, valid_at=args.valid_at, known_at=args.known_at)
            result = {'plans': plans, 'trace': trace, 'messages': messages(memory, args.question, plans,
                args.scope, valid_at=args.valid_at, known_at=args.known_at)}
        else:
            plan = json.loads(args.plan.read_text(encoding='utf-8'))
            result = memory.execute(args.scope, args.question, plan, valid_at=args.valid_at, known_at=args.known_at)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
