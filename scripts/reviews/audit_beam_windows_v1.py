"""All-source/window/packet reconstruction; no labels, inference or scoring."""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import ExitStack
from dataclasses import asdict
from itertools import groupby
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import prepare_beam_windows_v1 as P
W=P.W


def audit(prepared,output):
    started=time.monotonic();manifest=json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    original=json.loads((output/'started.json').read_text(encoding='utf-8'))
    if original['source']!=manifest['source'] or any(P.sha(ROOT/name)!=h for name,h in manifest['source']['sha256'].items()):raise ValueError('Execution source identity changed.')
    for name,key in [('reader/history.jsonl','history'),('reader/questions.jsonl','questions')]:
        if P.sha(prepared/name)!=original['input_sha256'][key]:raise ValueError('Prepared input changed.')
    if manifest['config']!=P.CONFIG or P.sha(output/'query-packets.jsonl')!=manifest['query_packets_sha256']:raise ValueError('Config/packets changed.')
    for row in manifest['indexes']:
        if P.sha(output/row['file'])!=row['sha256']:raise ValueError('Snapshot bytes changed.')
    for scope,h in manifest['source_partitions_sha256'].items():
        if P.sha(output/'sources'/f'{scope}.jsonl')!=h:raise ValueError('Source partition changed.')
    counts=Counter();window_count=0;window_text_bytes=0;roles=Counter()
    with ExitStack() as stack:
        snapshots={r['scope']:stack.enter_context(W.Snapshot(output/r['file'],scope=r['scope'],known_at=r['known_at'])) for r in manifest['indexes']}
        partitions={s:iter(P.rows(output/'sources'/f'{s}.jsonl')) for s in snapshots}
        originals={s:iter(db.connection.execute('SELECT body FROM sources ORDER BY rowid')) for s,db in snapshots.items()}
        groups={s:iter(groupby(db.connection.execute('SELECT source_id,body FROM windows ORDER BY source_id,rowid'),key=lambda r:r[0])) for s,db in snapshots.items()}
        for row in P.rows(prepared/'reader/history.jsonl'):
            source=P.source(row);scope=source.scope;snapshot=snapshots[scope]
            if next(partitions[scope])!=row or json.loads(next(originals[scope])[0])!=asdict(source):raise ValueError('Full original source/metadata lost.')
            if source.known_sequence>snapshot.meta['known_at']:raise ValueError('Future source in snapshot.')
            sid,group=next(groups[scope]);windows=[W.Window(**json.loads(r[1])) for r in group]
            if sid!=source.id or any(w.max_text_bytes!=P.CONFIG['max_text_bytes'] or w.overlap_bytes!=P.CONFIG['overlap_bytes'] for w in windows):raise ValueError('Window source/config differs.')
            W.verify(source,windows);counts[scope]+=1;roles[source.role]+=1;window_count+=len(windows)
            window_text_bytes+=sum(w.byte_end-w.byte_start for w in windows)
        sentinel=object()
        for scope in snapshots:
            if any(next(stream,sentinel) is not sentinel for stream in [partitions[scope],originals[scope],groups[scope]]):raise ValueError('Unaccounted extra source/window.')
            if counts[scope]!=snapshots[scope].meta['sources']:raise ValueError('Per-scope source count differs.')
        questions={r['id']:r for r in P.rows(prepared/'reader/questions.jsonl')};seen=set();packet_stats=[]
        for row in P.rows(output/'query-packets.jsonl'):
            q=questions[row['id']];scope=q['conversation_id'];snapshot=snapshots[scope];cutoff=snapshot.meta['known_at']
            if row['id'] in seen or any(row[k]!=q[k] for k in ['id','conversation_id','question']) or row['known_at']!=cutoff:raise ValueError('Question/view roster differs.')
            seen.add(row['id']);terms=P.L.query_tokens(q['question']);used=terms[:P.CONFIG['query_term_limit']]
            if row['terms']!=used or row['terms_truncated']!=(len(terms)>len(used)):raise ValueError('Frozen lexical terms differ.')
            windows=snapshot.search(used,scope=scope,known_at=cutoff,limit=P.CONFIG['candidate_limit'])
            if row['candidate_windows']!=[asdict(w) for w in windows]:raise ValueError('Actual retrieval candidates differ.')
            for field,items in [('retrieval_packet',windows),('no_memory_packet',[])]:
                packet=W.render_packet(q['question'],items,scope=scope,known_at=cutoff,max_message_bytes=P.CONFIG['max_message_bytes'])
                if row[field]!=packet or max(W.message_bytes(packet['messages']).values())>P.CONFIG['max_message_bytes']:raise ValueError('Reconstructed native-message packet differs/over budget.')
            packet_stats.append({'id':row['id'],'shown':len(row['retrieval_packet']['shown_ids']),
                'omitted':len(row['retrieval_packet']['omitted_ids']),'terms_truncated':row['terms_truncated'],
                'bytes':row['retrieval_packet']['message_bytes'],'partial_sources':row['retrieval_packet']['partial_sources']})
        if set(questions)!=seen or len(seen)!=200:raise ValueError('Incomplete query roster.')
    if sum(counts.values())!=187734 or window_count!=manifest['windows']:raise ValueError('Full source/window count differs.')
    return {'failures':[],'source_messages_reconstructed':sum(counts.values()),'windows_reconstructed':window_count,
        'query_pairs_reconstructed':len(seen),'native_message_packets_reconstructed':2*len(seen),
        'source_roles':dict(roles),'window_text_bytes_with_overlap':window_text_bytes,
        'all_message_budgets_hold':True,'empty_retrieval_packets':sum(r['shown']==0 for r in packet_stats),
        'shown_window_distribution':dict(Counter(r['shown'] for r in packet_stats)),
        'queries_with_omitted_candidates':sum(r['omitted']>0 for r in packet_stats),
        'queries_with_term_truncation':sum(r['terms_truncated'] for r in packet_stats),
        'queries_showing_partial_sources':sum(r['partial_sources']>0 for r in packet_stats),
        'maximum_message_bytes':{k:max(r['bytes'][k] for r in packet_stats) for k in ['utf8','ascii_escaped']},
        'source_manifest_sha256':P.sha(output/'manifest.json'),'audit_seconds':time.monotonic()-started,
        'new_model_calls':0,'benchmark_score':None,'claim':'Authored structural reconstruction, not semantic relevance or official memory accuracy.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['prepared','output','destination']:p.add_argument('--'+name,type=Path,required=True)
    args=vars(p.parse_args());destination=args.pop('destination');result=audit(**args)
    P.write(destination,result);print(json.dumps(result,indent=2))
