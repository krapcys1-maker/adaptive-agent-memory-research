"""K1 preparation (offline, no model): extract stimuli, provenance L10 (G1, G2), corpus P through L4a, token reference and
S/X draws (separate process under the audit hook), leak checks L1-L3, L4b at c = 1, header and P-length checks, stage-T task
lists, test_tasks for the coordinator, graph of shared traces (7.4), L8 manifest. Any failed check: exit 2 and no manifest.
Usage: python -I -X utf8 -B prepare.py [--base DIR]   (default: D:/aamr-k1-executor/base)"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import shutil
import site
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_l4 as l4  # noqa: E402
import k1_lib as kl  # noqa: E402

PY = [sys.executable, "-I", "-X", "utf8", "-B"]


def sub(script, *args):
    p = subprocess.run(PY + [str(CODE / script)] + [str(a) for a in args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=3600)
    return p.returncode, p.stdout, p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(kl.ROOT / "base"))
    a = ap.parse_args()
    L = kl.layout(a.base)
    if (L["run"] / "sessions").exists() and any((L["run"] / "sessions").iterdir()):
        raise SystemExit("run directory already has episodes; preparation is frozen")
    for k in ("stim", "meta"):
        if L[k].exists():
            shutil.rmtree(L[k])
        L[k].mkdir(parents=True)
    cfg = kl.load_cfg()
    n2, p0, xv, n1 = kl.import_harness()
    bfcl = n1.BfclN(kl.BFCL)               # preparation/verifier process: may read gold (population only, G1); not a stimulus process
    D = kl.DOMAINS
    train, test = n2.train_tasks(), n2.test_tasks(bfcl)
    tasks = {d: {"train": train[d], "test": test[d]} for d in D}
    pools = {d: n2.success_pool(d) for d in D}
    plans = {"test": {d: n2.test_plan(d) for d in D},
             "train": {d: p0.read_json(kl.NRUN / "artifacts" / n2.E1_RETRIEVAL)[d] for d in D}}
    kl.write_json(L["stim"] / "k1_tasks.json", tasks)
    for d in D:
        kl.write_json(L["stim"] / f"k1_pool_{d}.json", pools[d])
    kl.write_json(L["stim"] / "k1_plans_M.json", plans)
    bad, info = [], {}
    idx = kl.task_index(tasks)
    train_set = {t for d in D for t in tasks[d]["train"]}
    test_set = {t for d in D for t in tasks[d]["test"]}

    # ---- G1: pool provenance
    recs = n2.training_records()
    bad += kl.check_g1_rows(pools, tasks, p0.pool_row_id)
    for d, rws in pools.items():
        order = {t: i for i, t in enumerate(tasks[d]["train"])}
        rebuilt = [row for t in tasks[d]["train"] for row in p0.pool_rows_from_episode(*recs[t], order[t]) if row["label"] == "PASSED"]
        key = lambda r: (r["source_task"], r["turn"])
        if json.dumps(sorted(rebuilt, key=key), sort_keys=True) != json.dumps(sorted(rws, key=key), sort_keys=True):
            bad.append(f"G1 {d}: pool differs from rows rebuilt from training episodes")
    # ---- G2: plans rebuilt under the hook from gold-free inputs
    rc, so, se = sub("rebuild_worker.py", L["stim"], L["meta"] / "rebuilt_plans.json")
    rb = kl.read_json(L["meta"] / "rebuilt_plans.json") if rc == 0 else {}
    if rc != 0:
        bad.append(f"G2 rebuild exit {rc}: {se.strip()[-300:]}")
    g2, nkeys = kl.check_g2_plans(plans, rb)
    bad += g2
    n_tasks = len(idx)
    if n_tasks != 148 or nkeys < 400 or len(test_set) != 88 or len(train_set) != 60:
        bad.append(f"scope: {n_tasks} tasks ({len(test_set)} test, {len(train_set)} train), {nkeys} plan keys")
    info.update(G1_rows=sum(map(len, pools.values())), G2_keys=nkeys, tasks=n_tasks)

    # ---- L4a lists and corpus P
    dwords, dstems = l4.build_domain_list(kl.DOC_FILES, [r for d in D for r in pools[d]])
    lists = {"domain_words": sorted(dwords), "domain_stems": sorted(dstems), "function_words": sorted(l4.FUNCTION_WORDS),
             "number_words": sorted(l4.NUMBER_WORDS), "domain_variants": sorted(l4.DOMAIN_VARIANTS),
             "second_person": sorted(l4.SECOND_PERSON), "weather_words": sorted(cfg["corpus"]["weather_words"])}
    kl.write_json(L["stim"] / "k1_l4_lists.json", lists)
    src = kl.CORPUS_SOURCE.read_text(encoding="utf-8")
    sentences = [s.strip() for s in src.splitlines() if s.strip() and not s.lstrip().startswith("#")]
    weather = set(cfg["corpus"]["weather_words"])
    l4fail = []
    for s in sentences:
        why = l4.l4a(s, dstems)
        ws = {w.lower() for w in kl.WORD.findall(s)}
        if ws & weather:
            why.append("weather:" + ",".join(sorted(ws & weather)))
        if not s.endswith("."):
            why.append("not a declarative sentence ending with '.'")
        if why:
            l4fail.append((s, why))
    if l4fail:
        bad += [f"L4a: {w} | {s}" for s, w in l4fail[:20]]
    if len(sentences) < cfg["corpus"]["min_sentences"] or len(set(sentences)) != len(sentences):
        bad.append(f"corpus: {len(sentences)} sentences ({len(set(sentences))} distinct), need {cfg['corpus']['min_sentences']}")
    kl.write_json(L["stim"] / "k1_corpus_P.json", {"sentences": sentences, "source_sha256": kl.sha_file(kl.CORPUS_SOURCE)})
    info.update(L4a_domain_words=len(dwords), L4a_domain_stems=len(dstems), corpus_sentences=len(sentences), L4a_failures=len(l4fail))

    # ---- token reference and S/X draws (separate process under the hook)
    rc, so, se = sub("draw_worker.py", L["stim"])
    if rc != 0:
        bad.append(f"draw worker exit {rc}: {se.strip()[-300:]}")
        draws, tokref = {"X": {}, "S": {}}, {"nref": {}, "rho_dom": {}, "m_t0_tokens": {}}
    else:
        draws, tokref = kl.read_json(L["stim"] / "k1_draws_SX.json"), kl.read_json(L["stim"] / "k1_tokref.json")
        info["draws"] = draws["stats"]
        info["draw_rule"] = draws["rule"]
    turns = kl.plan_turns(plans, idx)
    src_of = {p0.pool_row_id(r): r["source_task"] for d in D for r in pools[d]}
    dom_of = {p0.pool_row_id(r): d for d in D for r in pools[d]}
    as_turns = lambda flat: {t: {ti: flat.get(f"{t}:{ti}", []) for ti in turns[t]} for t in turns}

    # ---- L1 (M, X, S), L2 (positive control), L3 (S)
    l1 = {}
    for arm, inst_maps in (("M", {"0": None}), ("X", draws["X"]), ("S", draws["S"])):
        for inst, flat in inst_maps.items():
            ids = turns if arm == "M" else as_turns(flat)
            v, n = kl.check_l1(ids, idx, src_of, train_set)
            l1[f"{arm}{'' if arm == 'M' else inst}"] = {"violations": len(v), "checked": n}
            bad += [f"L1 {arm}{inst}: {x}" for x in v[:5]]
            if arm == "X":
                same_dom = sum(1 for t, tt in ids.items() for ii in tt.values() for i in ii if dom_of[i] == idx[t][1])
                if same_dom:
                    bad.append(f"X{inst}: {same_dom} traces from the task's own domain")
    planted = {t: {ti: list(ids) for ti, ids in tt.items()} for t, tt in turns.items()}
    tr_t = next(t for t in sorted(train_set) if any(src_of[i] == t for i in src_of))
    own = next(i for i in sorted(src_of) if src_of[i] == tr_t)
    planted[tr_t][0] = [own] + planted[tr_t].get(0, [])[1:]
    test_src, test_dst = sorted(test_set)[:2]                     # a trace whose source is a held-out test task
    planted[test_dst][0] = ["PLANTED:t0"] + planted[test_dst].get(0, [])[1:]
    v2, _ = kl.check_l1(planted, idx, {**src_of, "PLANTED:t0": test_src}, train_set)
    l2 = {"own_task_detected": any(x.startswith(f"{tr_t}:0 own-task") for x in v2),
          "test_source_detected": any(x.startswith(f"{test_dst}:0 trace PLANTED:t0 from a non-training") for x in v2)}
    if not all(l2.values()):
        bad.append(f"L2 positive control failed: {l2}")
    l3 = {}
    for inst, flat in draws["S"].items():
        v = kl.check_l3(as_turns(flat), turns, src_of)
        l3[inst] = len(v)
        bad += [f"L3 S{inst}: {x}" for x in v[:5]]
    for inst, flat in draws["X"].items():
        cnt = [f"{t}:{ti}" for t, tt in turns.items() for ti, ids in tt.items() if len(flat.get(f"{t}:{ti}", [])) != len(ids)]
        bad += [f"X{inst}: count differs from M at {k}" for k in cnt[:5]]
    info.update(L1=l1, L2=l2, L3_violations=l3)

    # ---- P at c = 1 (and 0.8, 1.2): header, length to target, L4b; X/S/M header; predicted length balance (D9, D12)
    reqs = {t: [q[0]["content"] for q in bfcl.tasks[t]["question"]] for t in idx}
    by_id = {p0.pool_row_id(r): r for d in D for r in pools[d]}
    m_text = {(t, ti): p0.render_block([by_id[i] for i in ids]) for t, tt in turns.items() for ti, ids in tt.items()}
    hdr_bad, dev, jac = 0, [], []
    for (t, ti), mb in m_text.items():
        if not mb:
            continue
        for c in (0.8, 1.0, 1.2):
            for inst in (0, 1, 2, 3):
                pb = kl.build_p(mb, sentences, c, kl.p_seed(t, ti, inst))
                hdr_bad += pb.split("\n", 1)[0] != kl.HEADER
                dev.append(abs(len(kl.content(pb)) - round(c * len(kl.content(mb)))))
                if c == 1.0:
                    jac.append(kl.l4b(pb, reqs[t][ti], l4.FUNCTION_WORDS))
        hdr_bad += mb.split("\n", 1)[0] != kl.HEADER
    for arm in ("X", "S"):
        for inst, flat in draws[arm].items():
            for k, ids in flat.items():
                if ids and p0.render_block([by_id[i] for i in ids]).split("\n", 1)[0] != kl.HEADER:
                    hdr_bad += 1
    if hdr_bad or not dev or max(dev) > 12:
        bad.append(f"T-header/T-length(a): header failures {hdr_bad}, max |len - target| {max(dev) if dev else None}")
    if not jac or max(jac) > cfg["l4b_max_jaccard"]:
        bad.append(f"L4b: max Jaccard {max(jac) if jac else None} > {cfg['l4b_max_jaccard']}")
    info.update(P_blocks_checked=len(jac), P_len_dev_max=max(dev) if dev else None, L4b_max=max(jac) if jac else None,
                header_failures=hdr_bad)
    rho = tokref["rho_dom"]
    HDR = len(kl.HEADER) + 1
    cch = lambda ids: max(0, len(p0.render_block([by_id[i] for i in ids])) - HDR) if ids else 0
    bal = {"X": [], "S": []}
    for t, (st, d, part) in idx.items():
        rM = tokref["rho_task"].get(t, rho.get(d, 0.3))
        TM = sum(cch(ids) for ids in turns[t].values()) * rM
        if TM == 0:
            continue
        for arm in ("X", "S"):
            TC = sum(cch(draws[arm][i].get(f"{t}:{ti}", [])) * rho[d if arm == "S" else cfg["x_domain_map"][d]]
                     for i in ("1", "2", "3") for ti in turns[t]) / 3
            bal[arm].append(math.log(TM / TC))
    info["predicted_length_imbalance_pct"] = {a: round(100 * (math.exp(sum(v) / len(v)) - 1), 2) for a, v in bal.items() if v}

    # ---- stage-T task lists, test tasks, graph of shared traces, L6a allowlist
    exact = [t for t in tokref.get("m_t0_tokens", {})]
    order = lambda key, ts: sorted(ts, key=lambda t: hashlib.sha256(f"{key}|{t}".encode()).hexdigest())
    tcfg = cfg["T"]
    tl = {"cal": {}, "len": {}, "recal": {}, "len2": {}, "m_tasks": []}
    for d in D:
        o = order("K1-T", [t for t in exact if idx[t][1] == d])
        need = [("cal", tcfg["cal_blocks_per_domain"]), ("len", tcfg["len_blocks_per_domain"]),
                ("recal", tcfg["recal_blocks_per_domain"]), ("len2", tcfg["len_blocks_per_domain"])]
        pos = 0
        for name, n in need:
            tl[name][d] = [o[(pos + j) % len(o)] for j in range(n)] if o else []
            pos += n
        tl["m_tasks"] += order("K1-Tm", tasks[d]["train"])[:tcfg["m_tasks_per_domain"]]
        if len(o) < 20:
            bad.append(f"stage T: only {len(o)} tasks with an exact M token count in {d}")
    kl.write_json(L["stim"] / "k1_T_tasks.json", tl)
    kl.write_json(L["stim"] / "k1_test_tasks_88.json", sorted(test_set))
    # Graph of shared M traces (spec 7.4, L8), definition of v0.3 (k1_v03_checks.py, k1_v03_graph.json): traces in the
    # turns that NIGHT-2's M episodes (E3: E*, E1: R+) actually recorded. Only memory.items are read from the sessions.
    # The full-plan variant (every planned turn) is reported in provenance.json for information (technical choice, sec. 6.6).
    rec_items = {}
    for sess in ("E3", "E1"):
        for r in kl.rows(kl.NRUN / "sessions" / f"{sess}.jsonl"):
            if r["arm"] == kl.NIGHT2_M_ARM[sess] and r["task"] in idx and idx[r["task"]][0] == sess:
                rec_items[r["task"]] = [list((tu.get("memory") or {}).get("items") or []) for tu in r["episode"]["turns"]]
    if set(rec_items) != set(idx):
        bad.append(f"graph: NIGHT-2 M episodes for {len(rec_items)} of {len(idx)} tasks")
    graph = {t: {"stratum": [idx[t][0], idx[t][1]], "traces": sorted({i for ids in rec_items.get(t, []) for i in ids}),
                 # WR2 groups (v0.2 sec. 8.2): source task of the first trace of the M block of turn 0, within the stratum;
                 # an empty turn-0 block gives a one-task group
                 "first_group": (f"{idx[t][0]}-{idx[t][1]}|{src_of[turns[t][0][0]]}" if turns[t].get(0) else f"single|{t}")}
             for t in idx}
    kl.write_json(L["stim"] / "k1_shared_graph.json", graph)
    pairs = lambda gr: sum(1 for a in idx for b in idx if a < b and idx[a][:2] == idx[b][:2] and set(gr[a]) & set(gr[b]))
    info["shared_graph"] = {"definition": "traces of the turns recorded in NIGHT-2 M episodes (v0.3)",
                            "pairs": pairs({t: v["traces"] for t, v in graph.items()}),
                            "first_trace_groups": len({v["first_group"] for v in graph.values()}),
                            "pairs_full_plan_variant": pairs({t: [i for ids in turns[t].values() for i in ids] for t in idx})}
    pol = kl.worker_policy(L)
    kl.write_json(L["stim"] / "k1_l6a_allow.json", {"read_files": [str(p) for p in pol["read_files"] if "k1_l6a_allow" not in str(p)]
                                                   + ["<stim>/k1_l6a_allow.json"],
                                                   "code_roots": [str(p) for p in pol["code_roots"]],
                                                   "spawn_allow": [str(p) for p in pol["spawn_allow"]], "net_allow": pol["net_allow"]})
    info["T_tasks"] = {k: ({d: len(v) for d, v in tl[k].items()} if isinstance(tl[k], dict) else len(tl[k])) for k in tl}
    info["failures"] = bad
    kl.write_json(L["meta"] / "provenance.json", info, indent=1)
    if bad:
        print("PREPARATION FAILED:", bad[:8])
        raise SystemExit(2)

    # ---- L8 manifest
    startup = []
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        startup += glob.glob(str(Path(sp) / "*.pth"))
    for m in ("sitecustomize", "usercustomize"):
        for sp in sys.path:
            f = Path(sp) / f"{m}.py"
            if f.exists():
                startup.append(str(f))
    rel = lambda f: (str(Path(f).relative_to(L["base"])).replace("\\", "/") if Path(f).is_relative_to(L["base"]) else str(f))
    man = {"files": {rel(f): kl.sha_file(f) for f in kl.manifest_files(L)},
           "startup_files_before_hook": {f: kl.sha_file(Path(f)) for f in sorted(startup)},
           "python": sys.version, "harness_git_head": "0cdce5b (aamr-night2-worktree)",
           "status": "PREPARED, NOT FROZEN: decisions D1, D3, D4, D7, D8, D12 open; spec v0.4 not frozen"}
    kl.write_json(L["meta"] / "MANIFEST.json", man, indent=1)
    print(f"PREPARED: tasks {n_tasks}, pool rows {info['G1_rows']}, plan keys {nkeys} rebuilt gold-free; corpus {len(sentences)}; "
          f"L1 {l1}; L3 {l3}; L4b max {info['L4b_max']:.3f}; predicted imbalance {info['predicted_length_imbalance_pct']}; "
          f"manifest {len(man['files'])} files, start-up files {len(startup)}")


if __name__ == "__main__":
    main()
