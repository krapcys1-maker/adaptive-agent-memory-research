"""Offline, standard-library interface for the source-grounded memory candidate.

Capture source text first, attach a separately obtained model proposal, inspect
state or execute an explicit lookup plan. No model credential is needed here.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.structured_memory_v1 import Memory, Source


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('source', 'extract'):
        p = commands.add_parser(command)
        p.add_argument('--input', type=Path, required=True)
        if command == 'extract':
            p.add_argument('--source-id', required=True)
            p.add_argument('--learn', action='store_true')
    commands.add_parser('status')
    for command in ('resolve', 'query'):
        p = commands.add_parser(command)
        p.add_argument('--scope', required=True)
        p.add_argument('--valid-at', type=int, required=True)
        p.add_argument('--known-at', type=int, required=True)
        if command == 'resolve':
            p.add_argument('--subject', required=True)
            p.add_argument('--predicate', required=True)
        else:
            p.add_argument('--question', required=True)
            p.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args(argv)
    with Memory(args.store, writable=args.command in ('source','extract')) as m:
        if args.command == 'source':
            source = Source(**json.loads(args.input.read_text(encoding='utf-8')))
            result = {'added': m.add_source(source), 'source': asdict(source)}
        elif args.command == 'extract':
            proposal = json.loads(args.input.read_text(encoding='utf-8'))
            result = {'claims': [asdict(c) for c in m.extract(args.source_id, proposal, learn=args.learn)]}
        elif args.command == 'status':
            result = {'sources': len(m.sources), 'extracted': len(m.extracted), 'claims': len(m.claims),
                      'unprocessed': sorted(set(m.sources)-m.extracted), 'events': m.events,
                      'head': m.head, 'scope_policy': m.scope_policy}
        elif args.command == 'resolve':
            result = m.resolve(args.scope, args.subject, args.predicate,
                               valid_at=args.valid_at, known_at=args.known_at)
        else:
            plan = json.loads(args.plan.read_text(encoding='utf-8'))
            result = m.execute(args.scope, args.question, plan,
                               valid_at=args.valid_at, known_at=args.known_at)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
