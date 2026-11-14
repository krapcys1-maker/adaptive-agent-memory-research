"""K1, control L10 / G2: rebuild the M plans from gold-free inputs only, under the audit hook (same as the pilot's
rebuild_worker.py). argv: stim_dir out_file. Allowed reads: BFCL task file (requests), extracted pools, task lists; code."""
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_audit_hook as hook  # noqa: E402
import k1_lib as kl  # noqa: E402

STIM, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
hook.install(read_files=[kl.TASKS_FILE, STIM / "k1_tasks.json"] + [STIM / f"k1_pool_{d}.json" for d in kl.DOMAINS],
             code_roots=[sys.base_prefix, sys.prefix, kl.SCRIPTS, kl.CODE], run_dirs=[OUT.parent])

import json  # noqa: E402

sys.path.insert(0, str(kl.SCRIPTS))
import experience_pilot_v0 as p0  # noqa: E402

mk = p0.load_kernel()
tasks = json.loads((STIM / "k1_tasks.json").read_text(encoding="utf-8"))
requests = {}
for line in kl.TASKS_FILE.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    r = json.loads(line)
    if 100 <= int(r["id"].rsplit("_", 1)[1]) < 150:
        continue
    requests[r["id"]] = [m[0]["content"] for m in r["question"]]
out = {"test": {}, "train": {}}
for d in kl.DOMAINS:
    pool = json.loads((STIM / f"k1_pool_{d}.json").read_text(encoding="utf-8"))
    idx = p0.build_index(mk, pool)
    out["test"][d] = {f"{t}:{ti}": [p0.pool_row_id(r) for r in p0.retrieve(mk, *idx, q, *p0.UNGATED)[0]]
                      for t in tasks[d]["test"] for ti, q in enumerate(requests[t])}
    out["train"][d] = {}
    for t in tasks[d]["train"]:
        rows = [r for r in pool if r["source_task"] != t]
        ix = p0.build_index(mk, rows) if rows else None
        for ti, q in enumerate(requests[t]):
            out["train"][d][f"{t}:{ti}"] = [] if ix is None else [p0.pool_row_id(r) for r in p0.retrieve(mk, *ix, q, *p0.UNGATED)[0]]
OUT.write_text(json.dumps(out, sort_keys=True), encoding="utf-8")
print("REBUILT")
