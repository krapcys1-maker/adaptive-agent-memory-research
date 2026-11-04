"""Read-only offline replay of NIE's published improvised-persona journal.

This does not call a model, change an agent, write memories back, resolve
supersession or prove answer consistency. Real input/output remains local.
"""
from __future__ import annotations

import argparse
import dataclasses
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / 'scripts/wmb/kernel/memory_kernel.py'


def utc(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be an explicit timezone-aware ISO string.')
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid ISO timestamp.') from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('Naive timestamp: availability must have a timezone.')
    return stamp.astimezone(timezone.utc)


def iso(stamp):
    return stamp.isoformat().replace('+00:00', 'Z')


def load_kernel():
    name = '_nie_replay_kernel_020'
    spec = importlib.util.spec_from_file_location(name, KERNEL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def entries(raw):
    """Validate the existing journal contract without reading unrelated local files."""
    publications = {}
    for number, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f'Invalid JSON on journal line {number}.') from exc
        if not isinstance(row, dict):
            raise ValueError(f'Expected object on line {number}.')
        if row.get('typ_zadania') != 'notka_zycie' or row.get('zrodlo') != 'improwizacja':
            raise ValueError(f'Unsupported task/origin on line {number}.')
        if row.get('supersedes') is not None:
            raise ValueError('Supersession is not supported by this bridge version.')
        text, publication = row.get('tekst'), row.get('id_notki')
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'Missing published text on line {number}.')
        if isinstance(publication, bool) or not isinstance(publication, (str, int)) or not str(publication).strip():
            raise ValueError(f'Missing publication ID on line {number}.')
        stamp = utc(row.get('kiedy'))
        payload = {'publication_id': str(publication), 'available_at': iso(stamp),
                   'text': text, 'source': 'improwizacja', 'task': 'notka_zycie',
                   'run_id': row.get('run_id'), 'seed_id': row.get('zasiew'), 'version': row.get('wersja')}
        key = str(publication)
        if key in publications and publications[key] != payload:
            raise ValueError('Conflicting rows for the same publication ID; reconcile explicitly.')
        publications[key] = payload
    return sorted(publications.values(), key=lambda r: (utc(r['available_at']), r['publication_id']))


HEADING = 'Fictional improvised autobiographical records; these are not canonical biography:'


def replay(raw, query, as_of, *, task_type='personal', max_context_words=200, profile=None):
    now = utc(as_of)
    if not isinstance(query, str) or not query.strip():
        raise ValueError('Query must be nonempty.')
    if isinstance(max_context_words, bool) or not isinstance(max_context_words, int) or max_context_words < 0:
        raise ValueError('Word budget must be a nonnegative integer.')
    mk = load_kernel()
    cfg = dict(mk.PROFILES['lexical'], timeout_ms=float('inf'), require_zone=True,
               name='NIE-offline-lexical')
    if profile is not None:
        cfg.update(profile)
    if cfg.get('embed') != 'off':
        raise ValueError('Only offline lexical replay is supported; no embedding calls.')
    rows = entries(raw)
    available = [r for r in rows if utc(r['available_at']) <= now]
    items = []
    for row in available:
        encoded = json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
        item_id = 'nie-detail-' + hashlib.sha256(encoded).hexdigest()
        items.append(mk.Item(item_id, 'event', 'fiction_autobio', row['available_at'], row['text'],
                             meta={k: v for k, v in row.items() if k != 'text'}))
    index = mk.build_index(items, now.date().isoformat())
    result = mk.retrieve(index, query, task_type, iso(now), cfg)
    if result.get('error') or result.get('status') == 'degraded':
        raise ValueError('Kernel refused the replay: ' + str(result.get('error', result.get('status'))))
    shown = []
    context = ''
    for item in result['items']:
        candidate = shown + [item]
        rendered = HEADING + '\n' + mk.render(candidate, mode='raw', max_item_chars=0)
        if len(rendered.split()) > max_context_words:
            break
        shown, context = candidate, rendered
    safe_cfg = {k: ('infinity' if isinstance(v, float) and v == float('inf') else v) for k, v in cfg.items()}
    return {'schema_version': 1, 'mode': 'read-only-offline-no-reader', 'as_of': iso(now),
            'query': query, 'task_type': task_type, 'profile': safe_cfg,
            'input_sha256': hashlib.sha256(raw).hexdigest(),
            'kernel_version': mk.VERSION, 'kernel_sha256': hashlib.sha256(KERNEL.read_bytes()).hexdigest(),
            'bridge_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'validated_unique_publications': len(rows), 'available_publications': len(available),
            'future_publications_excluded_before_index': len(rows) - len(available),
            'kernel_status': result['status'], 'kernel_ranked_ids': [i.id for i in result['items']],
            'shown_items': [dataclasses.asdict(i) for i in shown], 'context': context,
            'context_words': len(context.split()), 'max_context_words': max_context_words,
            'budget_definition': 'Whitespace words of full context, including provenance heading/date labels.',
            'kernel_tokens_est_before_bridge_budget': result['tokens_est'],
            'kernel_token_definition': 'Kernel characters/4 estimate; distinct from this bridge word budget.',
            'limitations': ['No generated answer or consistency score.', 'No supersession/write-back/live injection.',
                            'Profile is an engineering replay setting, not an adoption recommendation.']}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--query', required=True)
    ap.add_argument('--as-of', required=True)
    ap.add_argument('--task-type', default='personal')
    ap.add_argument('--max-context-words', type=int, default=200)
    ap.add_argument('--profile-json', type=Path)
    args = ap.parse_args(argv)
    if args.output.exists() or args.output.resolve() == args.input.resolve():
        raise FileExistsError('Replay never overwrites inputs or earlier outputs.')
    raw = args.input.read_bytes()
    profile = json.loads(args.profile_json.read_text(encoding='utf-8')) if args.profile_json else None
    if profile is not None and not isinstance(profile, dict):
        raise ValueError('Profile override must be a JSON object.')
    result = replay(raw, args.query, args.as_of, task_type=args.task_type,
                    max_context_words=args.max_context_words, profile=profile)
    if args.input.read_bytes() != raw:
        raise RuntimeError('Input changed during replay; no output written.')
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(f"{len(result['shown_items'])} items; {result['context_words']}/{args.max_context_words} words; offline only.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
