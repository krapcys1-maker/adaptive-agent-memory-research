"""EXPLORATORY. Build a turn-level table from frozen K1 data (read-only). All metrics are computed by code, identically for every arm."""
import sys, re, ast, pickle; sys.path.insert(0, '.')
from common import *
idx = tasks_index(); tasks = sorted(idx)
HDR = "EXPERIENCE FROM EARLIER TASKS (it may or may not be relevant; use it only if it helps):"
GOLDF = "[machine-local path omitted]"
gold = {}
for line in open(GOLDF, encoding="utf-8"):
    if line.strip():
        r = json.loads(line)
        if r["id"] in idx: gold[r["id"]] = r["ground_truth"]
def fname(call): 
    m = re.match(r"\s*([A-Za-z_]\w*)\(", call); return m.group(1) if m else None
def scalars(call):
    out = []
    try:
        node = ast.parse(call.strip(), mode="eval").body
        for kw in node.keywords:
            try: v = ast.literal_eval(kw.value)
            except Exception: continue
            stack = [v]
            while stack:
                x = stack.pop()
                if isinstance(x, (list, tuple)): stack += list(x)
                elif isinstance(x, dict): stack += list(x.values())
                elif isinstance(x, bool) or x is None: pass
                else: out.append(x)
    except Exception: pass
    return out
def informative(v):
    if isinstance(v, str): return len(v) >= 4
    if isinstance(v, (int, float)): return abs(v) >= 100 and float(v) != round(float(v), -2)   # skip tiny / round numbers
    return False
def present(v, text):
    s = str(v)
    if isinstance(v, float) and v == int(v): return str(int(v)) in text or s in text
    return s in text
def block_calls(block):
    """call strings shown in a block: lines of the form '      call(...) -> result'"""
    out = []
    for ln in (block or "").split("\n"):
        m = re.match(r"^\s{6}([A-Za-z_]\w*\(.*\)) -> ", ln)
        if m: out.append(m.group(1))
    return out
norm = lambda s: re.sub(r"\s+", "", s)
EV = {}; SES = {}
for b in BLOCKS + ("A",):
    EV.update({(t, a, b): e for (t, a), e in load_eval(b).items()})
    for r in rows(BASE / f"run/sessions/{b}.jsonl"): SES[(r["task"], r["arm"], b)] = r["episode"]
# M block per (task, turn): from any M episode
Mblk = {}
for (t, a, b), ep in SES.items():
    if a == "M":
        for tu in ep["turns"]: Mblk[(t, tu["index"])] = tu["memory"].get("block_text") or ""
rowsout = []
for (t, a, b), ep in SES.items():
    ev = EV[(t, a, b)]; g = gold[t]; seen = ""
    for tu in ep["turns"]:
        i = tu["index"]; lab = ev["labels"][i] if i < len(ev["labels"]) else "NA"
        blk = tu["memory"].get("block_text") or ""
        mb = Mblk.get((t, i))
        gcalls = g[i]; gf = [fname(c) for c in gcalls]; gset = set(gf); gnorm = {norm(c) for c in gcalls}
        calls = [c["call"] for s in tu["steps"] for c in s.get("calls", []) if c.get("valid")]
        raw_invalid = sum(1 for s in tu["steps"] for c in s.get("calls", []) if not c.get("valid"))
        errs = sum(1 for s in tu["steps"] for c in s.get("calls", []) if c.get("valid") and c.get("error"))
        mf = [fname(c) for c in calls]; mset = set(mf)
        requests = " ".join(x["request"] for x in ep["turns"][:i + 1])
        def blockfeat(bt):
            bc = block_calls(bt); bf = {fname(c) for c in bc}; bn = {norm(c) for c in bc}
            return {"cov": (len(gset & bf) / len(gset)) if gset else None, "hit": len(gnorm & bn), "nlines": len(bc)}
        def contamination(bt):
            """values/functions used by the model in this turn that are present in block bt but absent from requests so far and from earlier tool results of the episode"""
            if not bt: return {"vals": 0, "fns": 0, "exact_copy": 0}
            body = bt[len(HDR) + 1:]; bc = block_calls(bt); bf = {fname(c) for c in bc}; bn = {norm(c) for c in bc}
            vals = set(); s2 = seen
            for s in tu["steps"]:
                for c in s.get("calls", []):
                    if not c.get("valid"): continue
                    for v in scalars(c["call"]):
                        if informative(v) and present(v, body) and not present(v, requests) and not present(v, s2): vals.add(str(v))
                    s2 += " " + str(c.get("result"))
            fns = {f for f in mset if f in bf and f not in gset}
            return {"vals": len(vals), "fns": len(fns), "exact_copy": sum(norm(c) in bn for c in calls), "vlist": sorted(vals)[:5]}
        rowsout.append({"task": t, "arm": a, "block": b, "turn": i, "label": lab, "nturns": len(g), "status": ep["status"],
                        "n_gold": len(gcalls), "n_calls": len(calls), "n_steps": len(tu["steps"]), "invalid": raw_invalid, "errors": errs,
                        "missing_f": len(gset - mset), "extra_f": len(mset - gset), "exact_gold": sum(norm(c) in gnorm for c in calls),
                        "all_gold_exact": gnorm <= {norm(c) for c in calls}, "gold_empty": not gcalls,
                        "own": blockfeat(blk) if blk and a in "MSX" else None, "mfeat": blockfeat(mb) if mb else None,
                        "cont_own": contamination(blk) if a in "MSX" else None, "cont_m": contamination(mb) if mb else None,
                        "has_block": bool(blk), "has_mblock": bool(mb), "calls": calls, "gold": gcalls})
        for s in tu["steps"]:
            for c in s.get("calls", []):
                if c.get("valid"): seen += " " + str(c.get("result"))
pickle.dump(rowsout, open("turns.pkl", "wb"))
print("turn rows:", len(rowsout), collections.Counter(r["label"] for r in rowsout))
