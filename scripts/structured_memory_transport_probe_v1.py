"""Paired local instruction-transport canaries, not benchmark questions."""
import json
from pathlib import Path
import sys

import structured_memory_pipeline_v1 as S
import nie_reader_pilot as P


def flattened(messages):
    return [{'role':'user', 'content': '\n\n'.join(m['content'] for m in messages)}]


def main():
    output = Path(sys.argv[1])
    S.start(output, 'local14b', [])
    reader = S.client('local14b', output, None)
    try:
        P.write(output/'preflight.json', reader.preflight())
        for i, token in enumerate(('teal-271', 'amber-594')):
            messages = [{'role':'system','content':'Return JSON with exactly one key value set to '+token+'.'},
                        {'role':'user','content':'Follow the instruction and return its specified value.'}]
            for style in ('native','flattened'):
                result = S.ask(reader, 'local14b', f'{style}-{i}', messages if style=='native' else flattened(messages))
                P.append(output/'checks.jsonl', {'key': f'{style}-{i}', 'correct': result.get('value') == token})
        for style in ('native','flattened'):
            messages = S.extraction_messages('Mira lives in Koral.', [])
            result = S.ask(reader, 'local14b', 'extraction-'+style,
                           messages if style=='native' else flattened(messages))
            P.append(output/'extractions.jsonl', {'style':style, 'proposal':result})
        S.finish(reader, output)
    finally:
        reader.release()


if __name__ == '__main__':
    main()
