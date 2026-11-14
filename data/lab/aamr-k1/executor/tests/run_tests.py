"""K1 executor: offline tests. No model, no Ollama, no GPU, no network, no paid API. Scratch bases under tests/_tmp/.
Nothing outside D:/aamr-k1-executor is written; NIGHT-2 data, the pilot and D:/kordynator are only read (the coordinator's
night_wrapper.py and leakage check are imported/run from their files, unchanged).

 U0  frozen prototypes byte-identical to k1/v0.4/testy; their self-tests (T-stan, T-odczyt, T-komórki) on scratch copies
 U1  preparation on a fresh base: L10 (G1, G2), corpus through L4a, L1/L2/L3, L4b, header, P length, predicted D12 balance
 U2  negative cases: L4a, L1/L2, L3, gate arithmetic, hook policy of the worker and of the draw process (exit 97),
     L8 tamper, real model refused without approvals, --only-arms outside the replay transport
 U3  T-zgodność: block A, arms N and M, replayed from NIGHT-2 responses; every request byte-identical (or identical after
     executor-instance normalisation) to NIGHT-2
 U4  fake end-to-end through the supervisor: T (c_d, T-length, m), A, S1-S3, freeze, checker, analysis, report; blindness
     (L7); post-run leak check; coordinator leak check (aamr_coord.lab.verify.leakage_check) pass, and fail-closed cases
 U5  crash in every block -> restarts resume without repeating or losing episodes; result equal to U4
 U6  budget gates: stop before A (exit 4); S3 skipped by its gate (2 blocks analysed); hard limit inside a block (incomplete)
 U7  coordinator night_wrapper + mock runner: DONE.json + raw-freeze.json, idempotence, STOPPED.json for codes 3 and 4,
     relaunch after a crash
 U8  analysis on synthetic outcomes: detected effects, INVALID at 8 (not 7) excluded tasks, no forbidden sentence
 U9  T-analiza-b: NIGHT-2 gains/losses 22/12 and 11/9; dependence diagnostic rho_hat -0.059, null mean -0.041, rho_tilde -0.018
Run: python -I -X utf8 -B tests/run_tests.py [U0 U1 ...]"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CODE = ROOT / "code"
TMP = HERE / "_tmp"
sys.path.insert(0, str(CODE))
import k1_lib as kl  # noqa: E402

PY = [sys.executable, "-I", "-X", "utf8", "-B"]
V04 = Path("D:/aamr-audit-2026-11-13/k1/v0.4/testy")
KORD = Path("D:/kordynator")
WRAPPER = KORD / "aamr_coord" / "lab" / "night_wrapper.py"
ONLY = set(sys.argv[1:])
out, ok = [], {}
t00 = time.time()


def P(*a):
    print(*a, flush=True)
    out.append(" ".join(map(str, a)))


def want(name):
    return not ONLY or name in ONLY


def sh(cmd, env=None, timeout=3600, cwd=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=e, cwd=cwd)


def prepared(name):
    b = TMP / name
    if b.exists():
        shutil.rmtree(b)
    r = sh(PY + [str(CODE / "prepare.py"), "--base", str(b)])
    assert r.returncode == 0, r.stdout[-500:] + r.stderr[-1500:]
    return b


def clone(src, name, with_run=False):
    b = TMP / name
    if b.exists():
        shutil.rmtree(b)
    shutil.copytree(src, b, ignore=None if with_run else shutil.ignore_patterns("run", "eval", "report", "out", "testdata"))
    if not with_run:
        (b / "meta" / "state.json").unlink(missing_ok=True)
        for f in ("supervisor.log", "worker.log", "pipeline.log", "RAW.json"):
            (b / "meta" / f).unlink(missing_ok=True)
    return b


def sup(base, transport="fake", env=None):
    return sh(PY + [str(CODE / "supervisor.py"), "--base", str(base), "--transport", transport], env=env)


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def nrows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()] if Path(p).exists() else []


TMP.mkdir(exist_ok=True)

# ---------------------------------------------------------------- U0 prototypes
if want("U0"):
    import hashlib
    same = {}
    for f in ("k1_audit_hook.py", "k1_l4.py", "k1_length.py", "k1_v04_reading.py", "t_w6_cells.py"):
        same[f] = hashlib.sha256((CODE / f).read_bytes()).hexdigest() == hashlib.sha256((V04 / f).read_bytes()).hexdigest()
    sc = TMP / "u0"
    if sc.exists():
        shutil.rmtree(sc)
    sc.mkdir()
    res = {}
    for f in ("k1_v04_reading.py", "t_w6_cells.py"):
        shutil.copy2(CODE / f, sc / f)
        r = sh(PY + [str(sc / f)])
        res[f] = (r.returncode, (r.stdout.strip().splitlines() or [""])[-1][:80])
    P(f"U0 prototypes identical to k1/v0.4/testy: {same}; self-tests on scratch copies: {res}")
    ok["U0"] = all(same.values()) and all(rc == 0 and "PASS" in s for rc, s in res.values())

# ---------------------------------------------------------------- U1 preparation
if want("U1") or any(want(u) for u in ("U2", "U3", "U4", "U5", "U6", "U7", "U8", "U10", "U11", "U12", "U15", "U16")):
    B1 = prepared("u1")
    prov = rj(B1 / "meta" / "provenance.json")
    man = rj(B1 / "meta" / "MANIFEST.json")
    imb = prov["predicted_length_imbalance_pct"]
    P(f"U1 prepare: tasks {prov['tasks']}, G1 rows {prov['G1_rows']}, G2 keys {prov['G2_keys']}, corpus {prov['corpus_sentences']} "
      f"(L4a failures {prov['L4a_failures']}), L1 {[(k, v['violations'], v['checked']) for k, v in prov['L1'].items()]}, L2 {prov['L2']}, "
      f"L3 {prov['L3_violations']}, L4b max {prov['L4b_max']:.3f}, P len dev max {prov['P_len_dev_max']}, header failures "
      f"{prov['header_failures']}, predicted imbalance M vs X/S {imb} (spec: +1.8/+2.2), draws {prov['draws']}; manifest {len(man['files'])} files")
    ok["U1"] = (prov["tasks"] == 148 and prov["G1_rows"] == 114 and prov["G2_keys"] == 520 and prov["corpus_sentences"] >= 150
                and prov["L4a_failures"] == 0 and all(v["violations"] == 0 and v["checked"] > 0 for v in prov["L1"].values())
                and all(prov["L2"].values()) and all(v == 0 for v in prov["L3_violations"].values()) and prov["L4b_max"] <= 0.05
                and prov["P_len_dev_max"] <= 12 and prov["header_failures"] == 0 and abs(imb["X"] - 1.8) < 0.15
                and abs(imb["S"] - 2.2) < 0.15 and not prov["failures"])

# ---------------------------------------------------------------- U2 negative cases
if want("U2"):
    import k1_l4 as l4
    lists = rj(B1 / "stim" / "k1_l4_lists.json")
    stems = set(lists["domain_stems"])
    badsent = ["The tanks hold water.", "Forty ferns grew there.", "Granite is hard, as you know.", "Basalt formed 3 ages ago.",
               "Quartz (a mineral) is hard.", "The café sits on rock.", "Moss grows on the fuel line.", "Shale holds petrol.",
               "Twenty-five oaks stood here.", "Lichens see the file system."]
    stopped = [s for s in badsent if l4.l4a(s, stems)]
    weather = {w for w in rj(CODE / "k1_config.json")["corpus"]["weather_words"]}
    wstop = bool({"rain"} & weather)
    good = [s for s in kl.read_json(B1 / "stim" / "k1_corpus_P.json")["sentences"]][:30]
    passed = [s for s in good if not l4.l4a(s, stems)]
    # L1/L2/L3 on constructed data
    tasks = kl.read_json(B1 / "stim" / "k1_tasks.json")
    idx = kl.task_index(tasks)
    plans = kl.plan_turns(kl.read_json(B1 / "stim" / "k1_plans_M.json"), idx)
    pools = {d: kl.read_json(B1 / "stim" / f"k1_pool_{d}.json") for d in kl.DOMAINS}
    src_of = {f"{r['source_task']}:t{r['turn']}": r["source_task"] for d in kl.DOMAINS for r in pools[d]}
    train = {t for t, v in idx.items() if v[0] == "E1"}
    t_train = sorted(train)[0]
    own = next(i for i, s in src_of.items() if s == t_train)
    bad_l1 = {t_train: {0: [own]}}
    l1_own = kl.check_l1(bad_l1, idx, src_of, train)[0]
    l1_zero = kl.check_l1({t_train: {0: []}}, idx, src_of, train)[0]
    t_test = sorted(t for t in idx if idx[t][0] == "E3" and plans[t].get(0))[0]
    m_ids = {t_test: plans[t_test]}
    s_bad = {t_test: {ti: list(ids) for ti, ids in plans[t_test].items()}}          # S identical to M
    s_cnt = {t_test: {ti: ids[:-1] for ti, ids in plans[t_test].items()}}          # wrong count
    l3a, l3b, l3c = kl.check_l3(s_bad, m_ids, src_of), kl.check_l3(s_cnt, m_ids, src_of), kl.check_l3({}, {}, src_of)
    cfg = kl.load_cfg()
    gA = kl.gate_before_a(300, 9.6, cfg)
    g140, g141 = kl.gate_before_a(300, 14.0, cfg), kl.gate_before_a(300, 14.1, cfg)
    gS = kl.gate_before_s(22000, 10.0, cfg)
    P(f"U2 L4a stops {len(stopped)}/{len(badsent)} planted sentences, passes {len(passed)}/{len(good)} corpus sentences, weather word "
      f"listed {wstop}; L1 own-task {bool(l1_own)}, zero sources {bool(l1_zero)}; L3 shared {bool(l3a)}, count {bool(l3b)}, empty {bool(l3c)}; "
      f"gate A at m 9.6: P_A {gA['P_A']} P_S {gA['P_S']} go {gA['go']}; m 14.0 go {g140['go']}, 14.1 go {g141['go']}; S at used 22000 m 10 go {gS['go']}")
    u2 = (len(stopped) == len(badsent) and len(passed) == len(good) and wstop and l1_own and l1_zero and l3a and l3b and l3c
          and gA["P_A"] == 4689 and gA["P_S"] == 7815 and gA["go"] and g140["go"] and not g141["go"] and not gS["go"])
    # hook policies (exit 97) in the worker and the draw process
    probe = TMP / "_probe.py"
    probe.write_text(
        "import sys; from pathlib import Path\n"
        f"sys.path.insert(0, r'{CODE}')\n"
        "import k1_audit_hook as h, k1_lib as kl\n"
        "L = kl.layout(Path(sys.argv[2])); h.install(**kl.worker_policy(L))\n"
        "c = sys.argv[1]\n"
        "if c == 'gold': open(kl.GOLD).read()\n"
        "if c == 'exposure': open(kl.SCRIPTS.parent / 'data/lab/experience-pilot-v0/exposure.json').read()\n"
        "if c == 'night2_sessions': open(kl.NRUN / 'sessions' / 'E3.jsonl').read()\n"
        "if c == 'night2_responses': open(kl.NRESP).read()\n"
        "if c == 'eval': open(L['eval'] / 'S1.jsonl', 'w').write('x')\n"
        "if c == 'net':\n  import socket; socket.create_connection(('192.0.2.1', 80), timeout=0.5)\n"
        "if c == 'spawn':\n  import subprocess; subprocess.run([sys.executable, '-c', 'print(1)'])\n"
        "if c == 'stim': [p.read_text() for p in L['stim'].glob('*.json')]\n"
        "print('NOT STOPPED')\n", encoding="utf-8")
    pol = {c: sh(PY + [str(probe), c, str(B1)]).returncode
           for c in ("gold", "exposure", "night2_sessions", "night2_responses", "eval", "net", "spawn", "stim")}
    probe2 = TMP / "_probe2.py"
    probe2.write_text(
        "import sys; from pathlib import Path\n"
        f"sys.path.insert(0, r'{CODE}')\n"
        "import k1_audit_hook as h, k1_lib as kl\n"
        "S = Path(sys.argv[1])\n"
        "h.install(read_files=[kl.NRESP, kl.CONFIG, S / 'k1_tasks.json', S / 'k1_plans_M.json'] + [S / f'k1_pool_{d}.json' for d in kl.DOMAINS],"
        " code_roots=[sys.base_prefix, sys.prefix, kl.SCRIPTS, kl.CODE], run_dirs=[S])\n"
        "open(kl.GOLD).read(); print('NOT STOPPED')\n", encoding="utf-8")
    pol["draw_process_gold"] = sh(PY + [str(probe2), str(B1 / "stim")]).returncode
    probe.unlink()
    probe2.unlink()
    # L8 tamper, approvals, --only-arms
    b7 = clone(B1, "u2_tamper")
    f = b7 / "stim" / "k1_draws_SX.json"
    f.write_text(f.read_text(encoding="utf-8").replace("multi_turn_base_", "multi_turn_base_ ", 1), encoding="utf-8")
    r7 = sup(b7)
    b8 = clone(B1, "u2_real")
    r8 = sh(PY + [str(CODE / "supervisor.py"), "--base", str(b8), "--transport", "ollama", "--check-approvals"])  # gate only
    import copy as _copy
    cfg0 = kl.load_cfg()
    gate_now = kl.approval_problems(cfg0)
    bad_cfgs = {"D5 not approved": dict(_copy.deepcopy(cfg0), decisions={**cfg0["decisions"], "D5": {"value": "x", "status": "open"}}),
                "T1-T12 not approved": dict(cfg0, technical_choices_approved=False),
                "wrong spec sha": dict(cfg0, spec_frozen_sha256="0" * 64),
                "wrong FREEZE sha": dict(cfg0, spec_freeze_json_sha256="0" * 64)}
    gate_neg = {k: bool(kl.approval_problems(v)) for k, v in bad_cfgs.items()}
    r9 = sh(PY + [str(CODE / "worker.py"), "--base", str(b8), "--phase", "A", "--transport", "fake", "--only-arms", "N"])
    P(f"U2 hook policy exit codes {pol} (97 = stopped; stim must be readable); L8 tamper: supervisor exit {r7.returncode}, run dir "
      f"created {(b7 / 'run').exists()}; real-model gate (--check-approvals, nothing started): exit {r8.returncode}, run dir {(b8 / 'run').exists()}, "
      f"'{r8.stdout.strip().splitlines()[-1][:150] if r8.stdout.strip() else r8.stderr[-150:]}'; gate on broken configs {gate_neg}; "
      f"--only-arms with fake: exit {r9.returncode}")
    u2 &= all(pol[c] == 97 for c in pol if c != "stim") and pol["stim"] == 0
    u2 &= r7.returncode == 3 and not (b7 / "run").exists() and not (b8 / "run").exists() \
        and ((r8.returncode == 0 and "APPROVALS COMPLETE" in r8.stdout) if not gate_now else
             (r8.returncode == 3 and all(p.split(" (")[0] in r8.stdout for p in gate_now))) \
        and all(gate_neg.values()) and not (b8 / "meta" / "state.json").exists() and r9.returncode != 0
    ok["U2"] = u2

# ---------------------------------------------------------------- U3 T-zgodność (replay of NIGHT-2, block A, N and M)
if want("U3"):
    # One replay per arm: where the M block of a turn is empty, the N and M requests are byte-identical while NIGHT-2 stored
    # different responses for them (two separate calls), so a single map keyed by request sha256 would mix the arms.
    n2, p0, xv, n1 = kl.import_harness()
    allresp = [r for r in kl.rows(kl.NRESP) if r["key"].startswith(("E3:N:", "E3:E*:", "E1:N:", "E1:R+:"))]
    first = {}
    with open(kl.NRUN / "attempts.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if '"attempt": 0' in line and kl.not_trading(line) and any(f'"key": "{p}' in line for p in ("E3:N:", "E3:E*:", "E1:N:", "E1:R+:")):
                a_ = json.loads(line)
                if a_.get("request"):
                    first[a_["key"]] = a_["request"]["messages"]
    tot, eps_n, rcs, t0 = {"sha": 0, "norm": 0, "miss": 0}, 0, [], time.time()
    for arm, prefixes in (("N", ("E3:N:", "E1:N:")), ("M", ("E3:E*:", "E1:R+:"))):
        b3 = clone(B1, f"u3_replay_{arm}")
        (b3 / "testdata").mkdir()
        by_key = {r["key"]: r for r in allresp if r["key"].startswith(prefixes)}
        by_sha = {r["request_sha256"]: {"text": r["text"], "done_reason": r.get("done_reason"), "usage": r.get("usage")} for r in by_key.values()}
        by_norm = {p0.sha(n2.norm_instances(json.dumps(first[k], ensure_ascii=False))): by_sha[r["request_sha256"]]
                   for k, r in by_key.items() if k in first}
        (b3 / "testdata" / "replay_map.json").write_text(json.dumps({"by_sha": by_sha, "by_norm": by_norm}), encoding="utf-8")
        r = sh(PY + [str(CODE / "worker.py"), "--base", str(b3), "--phase", "A", "--transport", "replay", "--only-arms", arm])
        rcs.append(r.returncode)
        hits = rj(b3 / "run" / "replay_hits.json") if (b3 / "run" / "replay_hits.json").exists() else {}
        for k in tot:
            tot[k] += hits.get(k, 0)
        eps_n += len(nrows(b3 / "run" / "sessions" / "A.jsonl"))
    mut = clone(B1, "u3_mutant_M")
    (mut / "testdata").mkdir()
    shutil.copy2(TMP / "u3_replay_M" / "testdata" / "replay_map.json", mut / "testdata" / "replay_map.json")
    rm = sh(PY + [str(CODE / "worker.py"), "--base", str(mut), "--phase", "A", "--transport", "replay", "--only-arms", "M"],
            env={"K1_TEST_MUTANT": "1"})
    mh = rj(mut / "run" / "replay_hits.json") if (mut / "run" / "replay_hits.json").exists() else {}
    P(f"U3 mutant 'block stays in history' (arm M): exit {rm.returncode}; requests not found in NIGHT-2 {mh.get('miss')} "
      f"(identical {mh.get('sha')}, after normalisation {mh.get('norm')})")
    P(f"U3 replay block A from NIGHT-2 responses (one replay per arm): worker exits {rcs} in {time.time() - t0:.0f} s; episodes {eps_n}; "
      f"requests byte-identical {tot['sha']}, identical after instance-name normalisation {tot['norm']}, not found {tot['miss']} "
      f"(v0.4 W1: 2 796 + 4 of 2 800)")
    ok["U3"] = rm.returncode == 0 and mh.get("miss", 0) >= 50 and rcs == [0, 0] and eps_n == 296 and tot["miss"] == 0 and tot["sha"] + tot["norm"] == 2800 and tot["sha"] >= 2790

# ---------------------------------------------------------------- U4 fake end-to-end
if any(want(u) for u in ("U4", "U5", "U7", "U8", "U10", "U11", "U12")):
    b4 = clone(B1, "u4_fake")
    t0 = time.time()
    r = sup(b4)
    run = b4 / "run"
    counts = {b: len(nrows(run / "sessions" / f"{b}.jsonl")) for b in ("A", "S1", "S2", "S3")}
    calls = len(nrows(run / "attempts.jsonl"))
    res = rj(b4 / "report" / "results.json") if (b4 / "report" / "results.json").exists() else {}
    wlog = (b4 / "meta" / "worker.log").read_text(encoding="utf-8", errors="replace") if (b4 / "meta" / "worker.log").exists() else ""
    prog = (run / "progress.log").read_text(encoding="utf-8", errors="replace") if (run / "progress.log").exists() else ""
    blind = "solved" not in prog.lower() and not any(f" {a}:" in prog or f"arm {a}" in prog for a in kl.ARMS5)
    pitems = [tu["memory"] for b in ("S1",) for e in nrows(run / "sessions" / f"{b}.jsonl") if e["arm"] == "P" for tu in e["episode"]["turns"]]
    p_ok = bool(pitems) and all(m["items"] == [] for m in pitems) and any(m["block_chars"] > 0 for m in pitems)
    P(f"U4 fake end-to-end: supervisor exit {r.returncode} in {time.time() - t0:.0f} s; episodes {counts}; local calls {calls} (limit 30 000); "
      f"c_d {rj(run / 'c_d.json')['c_d'] if (run / 'c_d.json').exists() else None}; states "
      f"{ {k: c['state'] for k, c in res.get('contrasts', {}).items()} }; post-run leak {res.get('postrun_leak', {}).get('violations')} of "
      f"{res.get('postrun_leak', {}).get('checked_sources')} sources; forbidden {res.get('forbidden_hits')}; blind progress log {blind} "
      f"({len(prog.splitlines())} lines); P items empty with blocks {p_ok}; hook violations {'K1-AUDIT-VIOLATION' in wlog}")
    u4 = (r.returncode == 0 and counts == {"A": 444, "S1": 740, "S2": 740, "S3": 740} and calls <= 30000 and res.get("reading")
          and res.get("postrun_leak", {}).get("violations") == 0 and res["postrun_leak"]["checked_sources"] > 0 and not res.get("forbidden_hits")
          and blind and p_ok and "K1-AUDIT-VIOLATION" not in wlog and (b4 / "meta" / "RAW.json").exists()
          and (b4 / "report" / "K1_RAPORT.md").exists())
    # coordinator leak check (read-only import of D:/kordynator), K1 declaration as in the integration template
    sys.path.insert(0, str(KORD))
    from aamr_coord.lab.verify import leakage_check  # noqa: E402
    decl = {"test_sessions": ["S1", "S2"], "memory_arms": ["M", "X", "S"], "placebo_arms": ["P"],
            "test_tasks": "file:" + str(b4 / "stim" / "k1_test_tasks_88.json")}
    lv, blocking = leakage_check(run, decl)
    lv2, bl2 = leakage_check(run, dict(decl, placebo_arms=[]))                      # P undeclared -> must fail
    lv3, bl3 = leakage_check(run, dict(decl, memory_arms=["M"]))                     # X, S undeclared -> must fail
    lv4, bl4 = leakage_check(run, dict(decl, test_tasks=sorted({t for t in rj(b4 / "stim" / "k1_tasks.json")["VC"]["train"]})))
    P(f"U4 coordinator leak check: K1 declaration -> {lv['status']} (sources {lv.get('memory_sources')}, test tasks {lv.get('test_tasks')}, "
      f"overlap {len(lv.get('overlap') or [])}); P undeclared -> {lv2['status']}; X/S undeclared -> {lv3['status']}; "
      f"training tasks declared held-out -> {lv4['status']} (overlap {len(lv4.get('overlap') or [])})")
    ok["U4"] = u4 and lv["status"] == "pass" and not blocking and bl2 and bl3 and bl4 and lv["test_tasks"] == 88

# ---------------------------------------------------------------- U5 crash in every block, resume
if want("U5"):
    b5 = clone(B1, "u5_crash")
    r = sup(b5, env={"K1_TEST_CRASH_AFTER": "100"})
    st = rj(b5 / "meta" / "state.json")
    same, diffs, dup = True, 0, 0
    for b in ("A", "S1", "S2", "S3"):
        e4 = {(e["task"], e["arm"]): e for e in nrows(b4 / "run" / "sessions" / f"{b}.jsonl")}
        e5l = nrows(b5 / "run" / "sessions" / f"{b}.jsonl")
        e5 = {(e["task"], e["arm"]): e for e in e5l}
        dup += len(e5l) - len(e5)
        same &= set(e4) == set(e5)
        strip = lambda e: [[s.get("text") for s in tu["steps"]] for tu in e["episode"]["turns"]]
        diffs += sum(strip(e4[k]) != strip(e5[k]) for k in e4 if k in e5)
    r4 = rj(b4 / "report" / "results.json")
    r5 = rj(b5 / "report" / "results.json") if (b5 / "report" / "results.json").exists() else {}
    P(f"U5 crash after 100 episodes in every block: supervisor exit {r.returncode}; restarts {st['restarts']}, errors per block {st['errors']}; "
      f"same (task, arm) sets as U4 {same}; duplicated episodes {dup}; episodes with different responses {diffs}; reading identical "
      f"{r4.get('reading') == r5.get('reading')}")
    ok["U5"] = r.returncode == 0 and st["restarts"] == 4 and same and dup == 0 and diffs == 0 and r4.get("reading") == r5.get("reading")

# ---------------------------------------------------------------- U6 gates and hard limit
if want("U6"):
    b6a = clone(B1, "u6_stopA")
    ra = sup(b6a, env={"K1_TEST_HARD_LIMIT": "12000"})
    ga = rj(b6a / "run" / "gate_A.json") if (b6a / "run" / "gate_A.json").exists() else {}
    b6b = clone(B1, "u6_skipS3")
    rb = sup(b6b, env={"K1_TEST_HARD_LIMIT": "17000"})
    resb = rj(b6b / "report" / "results.json") if (b6b / "report" / "results.json").exists() else {}
    skipped = rj(b6b / "run" / "S_SKIPPED.json") if (b6b / "run" / "S_SKIPPED.json").exists() else {}
    b6c = clone(B1, "u6_hard")
    rc_ = sup(b6c, env={"K1_TEST_HARD_LIMIT": "11000", "K1_TEST_MARGIN": "0.3"})
    resc = rj(b6c / "report" / "results.json") if (b6c / "report" / "results.json").exists() else {}
    used_c = len(nrows(b6c / "run" / "attempts.jsonl"))
    P(f"U6 gate before A (limit 12 000): exit {ra.returncode}, gate {ga.get('need')}+{ga.get('used')} go {ga.get('go')}, A run {(b6a / 'run' / 'sessions' / 'A.jsonl').exists()}; "
      f"limit 17 000: exit {rb.returncode}, skipped from {skipped.get('from')}, blocks {resb.get('blocks')}, analysed {resb.get('completed_sampled_blocks')}, "
      f"invalid {resb.get('invalid')}; hard limit 11 000 with margin 0.3: exit {rc_.returncode}, calls {used_c}, blocks {resc.get('blocks')}, "
      f"invalid {resc.get('invalid')}")
    ok["U6"] = (ra.returncode == 4 and ga.get("go") is False and not (b6a / "run" / "sessions" / "A.jsonl").exists()
                and rb.returncode == 0 and skipped.get("from") == "S3" and resb.get("completed_sampled_blocks") == ["S1", "S2"]
                and resb.get("invalid") is None and rc_.returncode == 0 and used_c <= 11000
                and "incomplete (hard limit)" in (resc.get("blocks") or {}).values() and resc.get("invalid") is not None)

# ---------------------------------------------------------------- U7 coordinator wrapper + mock runner
if want("U7"):
    def wrapped(base, env=None):
        return sh([sys.executable, "-B", str(WRAPPER), "--run-dir", str(base / "run"), "--out-dir", str(base / "out"),
                   "--stop-codes", "3,4", "--log", str(base / "meta" / "supervisor.log"), "--"]
                  + PY + [str(CODE / "supervisor.py"), "--base", str(base), "--transport", "fake"], env=env)

    def mock_runner(base, max_launches=6, env=None):
        """What aamr_coord.lab.runner does with the launch command: relaunch on a crash code, stop on DONE/STOPPED."""
        launches = []
        for _ in range(max_launches):
            if (base / "run" / "DONE.json").exists() or (base / "run" / "STOPPED.json").exists():
                break
            launches.append(wrapped(base, env).returncode)
        return launches
    b7a = clone(b4, "u7_done", with_run=True)
    l1 = mock_runner(b7a)
    frz = rj(b7a / "out" / "raw-freeze.json") if (b7a / "out" / "raw-freeze.json").exists() else {"files": {}}
    before = (b7a / "run" / "attempts.jsonl").stat().st_mtime
    again = wrapped(b7a).returncode
    idem = (b7a / "run" / "attempts.jsonl").stat().st_mtime == before
    b7b = clone(B1, "u7_stop3")
    f = b7b / "stim" / "k1_tasks.json"
    f.write_text(f.read_text(encoding="utf-8") + " ", encoding="utf-8")
    l2 = mock_runner(b7b)
    s3 = rj(b7b / "run" / "STOPPED.json") if (b7b / "run" / "STOPPED.json").exists() else {}
    b7c = clone(B1, "u7_stop4")
    l3 = mock_runner(b7c, env={"K1_TEST_HARD_LIMIT": "12000"})
    s4 = rj(b7c / "run" / "STOPPED.json") if (b7c / "run" / "STOPPED.json").exists() else {}
    b7d = clone(B1, "u7_crash")                                    # supervisor crash -> wrapper returns the code -> relaunch
    (b7d / "meta").mkdir(exist_ok=True)
    (b7d / "meta" / "state.json").write_text("{not json", encoding="utf-8")
    l4_ = mock_runner(b7d, max_launches=2)
    P(f"U7 wrapper on a finished run: launches {l1}, DONE {(b7a / 'run' / 'DONE.json').exists()}, raw-freeze files {len(frz['files'])} "
      f"(sessions {sum('sessions/' in k for k in frz['files'])}), second call exit {again} without work {idem}; L8 tamper: launches {l2}, "
      f"STOPPED rc {s3.get('wrapped_rc')}; gate before A: launches {l3}, STOPPED rc {s4.get('wrapped_rc')}; supervisor crash: launches {l4_} "
      f"(non-zero, no markers {not (b7d / 'run' / 'STOPPED.json').exists() and not (b7d / 'run' / 'DONE.json').exists()})")
    ok["U7"] = (l1 == [0] and (b7a / "run" / "DONE.json").exists() and sum("sessions/" in k for k in frz["files"]) == 4 and again == 0 and idem
                and l2 == [0] and s3.get("wrapped_rc") == 3 and l3 == [0] and s4.get("wrapped_rc") == 4
                and len(l4_) == 2 and all(x not in (0,) for x in l4_) and not (b7d / "run" / "STOPPED.json").exists())

# ---------------------------------------------------------------- U8 analysis on synthetic outcomes
if want("U8"):
    def synth(name, effect, tech_x=0, seed=5):
        b = clone(b4, name, with_run=True)
        rng = random.Random(seed)
        base_p = {t: rng.uniform(0.15, 0.75) for t in kl.task_index(rj(b / "stim" / "k1_tasks.json"))}
        for blk in ("S1", "S2", "S3", "A"):
            p = b / "eval" / f"{blk}.jsonl"
            rows_ = nrows(p)
            for e in rows_:
                q = base_p[e["task"]] + (effect / 100 if e["arm"] == "M" else 0)
                e["solved"] = rng.random() < min(0.98, q)
                e["eval_status"] = "ok"
            bad = sorted(base_p)[:tech_x]
            for e in rows_:
                if e["task"] in bad and e["arm"] == "X" and blk != "A":
                    e["eval_status"] = "technical_error"
            p.write_text("".join(json.dumps(e) + "\n" for e in rows_), encoding="utf-8")
        r = sh(PY + [str(CODE / "analyze.py"), "--base", str(b), "--final"])
        return r, rj(b / "report" / "results.json")
    r1, a1 = synth("u8_effect", 30)
    r2, a2 = synth("u8_null", 0)
    r3, a3 = synth("u8_ex7", 0, tech_x=7)
    r4_, a4 = synth("u8_ex8", 0, tech_x=8)
    st1 = {k: c["state"] for k, c in a1.get("contrasts", {}).items()}
    st2 = {k: c["state"] for k, c in a2.get("contrasts", {}).items()}
    P(f"U8 synthetic +30 pp for M: exit {r1.returncode}, states {st1}, composite B {any(s.startswith('ZŁOŻONE-B') for s in a1['reading'])}; "
      f"no effect: states {st2}, composite C {any(s.startswith('ZŁOŻONE-C') for s in a2['reading'])}; 7 tasks with technical errors -> "
      f"invalid {a3.get('invalid')}, excluded {len(a3.get('excluded_tasks', []))}; 8 -> invalid {a4.get('invalid')!r}, reading "
      f"'{a4['reading'][0][:60]}'; forbidden hits {[a['forbidden_hits'] for a in (a1, a2, a3, a4)]}")
    ok["U8"] = (r1.returncode == 0 and all(s in ("V1", "V2") for s in st1.values()) and len(st1) == 3
                and all(s in ("V4", "V5") for s in st2.values()) and a3.get("invalid") is None
                and len(a3.get("excluded_tasks", [])) == 7 and a4.get("invalid") and a4["reading"][0].startswith("NIEWAŻNY")
                and not any(a["forbidden_hits"] for a in (a1, a2, a3, a4)))

# ---------------------------------------------------------------- U9 T-analiza-b (NIGHT-2 reproduction)
if want("U9"):
    import numpy as np
    import analyze as an
    stim = (TMP / "u1" / "stim") if (TMP / "u1" / "stim").exists() else (ROOT / "base" / "stim")
    idx = kl.task_index(kl.read_json(stim / "k1_tasks.json"))
    cnt = an.night2_counts(idx)
    o = an.night2_outcomes()
    tasks = sorted(idx)
    d = np.array([o[(t, "M", idx[t][0])] - o[(t, "N", idx[t][0])] for t in tasks], float)
    dep = an.Dependence(kl.read_json(stim / "k1_shared_graph.json"), tasks)
    dg = dep.diag(d, 2000, 20261114)
    P(f"U9 NIGHT-2 M - N at temperature 0: {cnt}; graph pairs {len(dep.pairs)} (2L/n {dep.L2n:.2f}; spec 1 260 and 17.0); rho_hat "
      f"{dg['rho_hat']:+.3f}, null mean {dg['null_mean']:+.3f} (sd {dg['null_sd']:.3f}), rho_tilde {dg['rho_tilde']:+.3f}, p {dg['p']:.3f}")
    ok["U9"] = (cnt["E3"] == {"tasks": 88, "gains": 22, "losses": 12} and cnt["E1"] == {"tasks": 60, "gains": 11, "losses": 9}
                and round(dg["rho_hat"], 3) == -0.059 and abs(dg["null_mean"] + 0.041) <= 0.003 and abs(dg["rho_tilde"] + 0.018) <= 0.003
                and len(dep.pairs) == 1260 and len({v["first_group"] for v in kl.read_json(stim / "k1_shared_graph.json").values()}) == 68)

# ---------------------------------------------------------------- U10 T12 token reference check
if want("U10"):
    ref_ok = rj(b4 / "run" / "c_d.json").get("ref_check", []) if (b4 / "run" / "c_d.json").exists() else []
    b10 = clone(B1, "u10_cache")
    r10 = sup(b10, env={"K1_TEST_FAKE_CACHE": "1"})
    failed = rj(b10 / "run" / "T_ref_FAILED.json") if (b10 / "run" / "T_ref_FAILED.json").exists() else []
    P(f"U10 T12 in U4: {len(ref_ok)} reference calls, all equal {all(x['prompt_eval_count'] == x['reference'] for x in ref_ok)}; "
      f"fake with cache remainders: supervisor exit {r10.returncode}, mismatches {sum(x['prompt_eval_count'] != x['reference'] for x in failed)}, "
      f"c_d written {(b10 / 'run' / 'c_d.json').exists()}, block A started {(b10 / 'run' / 'sessions' / 'A.jsonl').exists()}, "
      f"calls {len(nrows(b10 / 'run' / 'attempts.jsonl'))}")
    ok["U10"] = (len(ref_ok) == 6 and all(x["prompt_eval_count"] == x["reference"] for x in ref_ok) and r10.returncode == 3
                 and sum(x["prompt_eval_count"] != x["reference"] for x in failed) == 3 and not (b10 / "run" / "c_d.json").exists()
                 and not (b10 / "run" / "sessions" / "A.jsonl").exists() and len(nrows(b10 / "run" / "attempts.jsonl")) <= 20)

# ---------------------------------------------------------------- U11 owner's condition to D1: no "no benefit" claims
if want("U11"):
    import itertools
    import re as _re
    import k1_v04_reading as rd
    import analyze as an
    NO_BENEFIT = [r"brak\w*\s+korzy", r"nie\s+(?:daje|przynosi|ma)\s+\w*\s*korzy", r"bez\s*użyteczn", r"nieużyteczn",
                  r"nie\s+pomaga", r"nie\s+ma\s+(?:żadnego\s+)?efektu", r"efekt\w*\s+nie\s+istnieje", r"nie\s+działa"]
    reps = [(-6, 4), (-2, 8), (2, 8), (3, 9.5), (-3, 12), (11, 20), (4, 16), (-9, -1), (0.5, 7)]
    hits, n_read, v35 = [], 0, 0
    est = {"MN": "0 pp", "PN": "0 pp"}
    for mp, mx, ms in itertools.product(reps, repeat=3):
        text = rd.read({"MP": mp, "MX": mx, "MS": ms}, est) + [an.D1_RULE]
        n_read += 1
        v35 += any(rd.state(*iv) in ("V3", "V5") for iv in (mp, mx, ms))
        joined = " ".join(text).replace(rd.SENT_C, "").replace(an.D1_RULE, "")
        hits += [p for p in NO_BENEFIT if _re.search(p, joined, _re.I)]
    rep = (b4 / "report" / "K1_RAPORT.md").read_text(encoding="utf-8") if (b4 / "report" / "K1_RAPORT.md").exists() else ""
    rule_ok = an.D1_RULE in rep and "mogą być rzeczywiste i użyteczne" in an.D1_RULE and not rd.forbidden_hits([an.D1_RULE])
    P(f"U11 D1 condition: {n_read} readings ({v35} with a V3/V5 contrast) contain no 'no benefit' claim: {not hits}; D1 rule printed in "
      f"the U4 report {an.D1_RULE in rep}; rule passes the frozen forbidden-phrase check {not rd.forbidden_hits([an.D1_RULE])}")
    ok["U11"] = not hits and rule_ok and v35 > 0

# ---------------------------------------------------------------- U12 owner checkpoint after stage T, then the runner path
if want("U12"):
    b12 = clone(B1, "u12_stopT")
    r1 = sh(PY + [str(CODE / "supervisor.py"), "--base", str(b12), "--transport", "fake", "--stop-after-T"])
    after_t = {"T_DONE": (b12 / "run" / "T_DONE.json").exists(), "c_d": (b12 / "run" / "c_d.json").exists(),
               "A": (b12 / "run" / "sessions" / "A.jsonl").exists(), "lock": (b12 / "run" / "supervisor.lock").exists()}
    r2 = sh([sys.executable, "-B", str(WRAPPER), "--run-dir", str(b12 / "run"), "--out-dir", str(b12 / "out"), "--stop-codes", "3,4",
             "--log", str(b12 / "meta" / "supervisor.log"), "--"] + PY + [str(CODE / "supervisor.py"), "--base", str(b12), "--transport", "fake"])
    same = all({(e["task"], e["arm"]): [[x.get("text") for x in tu["steps"]] for tu in e["episode"]["turns"]]
                for e in nrows(b12 / "run" / "sessions" / f"{b}.jsonl")} ==
               {(e["task"], e["arm"]): [[x.get("text") for x in tu["steps"]] for tu in e["episode"]["turns"]]
                for e in nrows(b4 / "run" / "sessions" / f"{b}.jsonl")} for b in ("A", "S1", "S2", "S3"))
    b12b = clone(B1, "u12_lock")
    (b12b / "run").mkdir()
    (b12b / "run" / "supervisor.lock").write_text("99999", encoding="utf-8")
    r3 = sh(PY + [str(CODE / "supervisor.py"), "--base", str(b12b), "--transport", "fake", "--stop-after-T"])
    P(f"U12 --stop-after-T: exit {r1.returncode}, state after T {after_t}; then wrapper (runner command): exit {r2.returncode}, "
      f"DONE {(b12 / 'run' / 'DONE.json').exists()}, episodes identical to the uninterrupted U4 run {same}; existing lock: exit {r3.returncode}, "
      f"T started {(b12b / 'run' / 'T.json').exists()}")
    ok["U12"] = (r1.returncode == 0 and after_t == {"T_DONE": True, "c_d": True, "A": False, "lock": False} and r2.returncode == 0
                 and (b12 / "run" / "DONE.json").exists() and same and r3.returncode == 3 and not (b12b / "run" / "T.json").exists())

# ---------------------------------------------------------------- U13 T-analiza-a: the executor's analysis functions vs the power simulation
if want("U13"):
    import numpy as np
    import analyze as an
    import k1_v04_reading as rd
    import t_w6_cells as cells
    sys.path.insert(0, "D:/aamr-audit-2026-11-13/k1/v0.3")
    import k1_power_sim_v3 as S
    w, b, base, R, level = 0.159, 0.307, 0.345, 3, 1 - 0.05 / 3
    nu = (1 - math.sqrt(1 - 2 * w)) / 2
    sd_share = max(0.0, (b - w) / (1 - 2 * w))
    tasks = [f"t{i}" for i in range(148)]

    def ours(delta, sims, seed):
        """Synthetic per-block 0/1 outcomes from the simulation's model -> t_w6_cells.analyse_sampled -> analyze.t_iv -> state."""
        rng = np.random.default_rng(seed)
        det = exc = 0
        for _ in range(sims):
            zM = (rng.random(148) < base).astype(int)
            zC = S.derive(zM, base, -delta, sd_share, nu, rng)
            Y = {}
            for z, arms in ((zM, ("M",)), (zC, ("N", "P", "X", "S"))):
                fl = rng.random((148, R)) < nu
                yy = np.where(fl, 1 - z[:, None], z[:, None])
                for i, t in enumerate(tasks):
                    for r_, blk in enumerate(("S1", "S2", "S3")):
                        for a in arms:
                            Y[(t, a, blk)] = {"status": "completed", "solved": bool(yy[i, r_])}
            res = cells.analyse_sampled(Y, tasks)
            d = [100 * (res["y"][t]["M"] - res["y"][t]["P"]) for t in tasks]
            st = rd.state(*an.t_iv(d, level)[1])
            det += st in ("V1", "V2", "V3")
            exc += st in ("V3", "V5", "V6")
        return det / sims, exc / sims

    sims = 2000
    d10, _ = ours(0.10, sims, 1)
    _, x0 = ours(0.0, sims, 2)
    ref10 = np.isin(S.run([0.10], w, b, "fixed", level, 6000, np.random.default_rng(1), R=R, base_m=base)[0][0], (0, 1, 2)).mean()
    ref0 = np.isin(S.run([0.0], w, b, "fixed", level, 6000, np.random.default_rng(2), R=R, base_m=base)[0][0], (2, 4, 5)).mean()
    tol = 4 * math.sqrt(0.25 / sims + 0.25 / 6000)
    P(f"U13 T-analiza-a ({sims} synthetic runs each, w {w}, b {b}, base {base}): executor detect at 10 pp {d10:.1%} vs simulation {ref10:.1%} "
      f"(spec v1.0.1: 64%); exclude 10 pp at 0 {x0:.1%} vs {ref0:.1%} (spec: 62%); tolerance +-{tol:.1%}")
    ok["U13"] = abs(d10 - ref10) <= tol and abs(x0 - ref0) <= tol

# ---------------------------------------------------------------- U14 T-budżet: Monte Carlo of the executor's gates
if want("U14"):
    import numpy as np
    cfg = kl.load_cfg()
    HARD = cfg["hard_limit"]
    rng = np.random.default_rng(14)
    epi = lambda mean, n: np.clip(rng.poisson(rng.gamma(4.0, mean / 4.0, n)), 1, 40)
    rows = []
    over = 0
    for m_true in (9.0, 9.5, 10.2, 11.0, 12.0, 13.0):
        for xm in (1.0, 1.3, 1.6):
            valid = stopA = 0
            for _ in range(300):
                tcalls = epi(m_true, 12)
                used = int(tcalls.sum()) + 69 + 6
                hist = list(tcalls)
                g = kl.gate_before_a(used, float(np.mean(hist)), cfg)
                if not g["go"]:
                    stopA += 1
                    continue
                used += int(epi(m_true, 444).sum())
                done = 0
                for _b in range(3):
                    if not kl.gate_before_s(used, float(np.mean(hist)), cfg)["go"]:
                        break
                    calls = np.concatenate([epi(m_true * (xm if a == "X" else 1.0), 148) for a in "NPXSM"])
                    if used + int(calls.sum()) > HARD:
                        used = HARD
                        break
                    used += int(calls.sum())
                    hist += list(calls)
                    done += 1
                over += used > HARD
                valid += done >= 2
            rows.append((m_true, xm, valid / 300, stopA / 300))
    P("U14 T-budżet (300 runs per cell; m, X multiplier -> valid run >= 2 blocks / stop before A): " +
      "; ".join(f"{m} x{x}: {v:.0%}/{s_:.0%}" for m, x, v, s_ in rows) + f"; runs above {HARD}: {over}")
    ok["U14"] = over == 0 and all(v >= 0.9 for m, x, v, s_ in rows if m <= 10.2)

# ---------------------------------------------------------------- U15 T-pochodzenie: L10 negative controls on the executor's checks
if want("U15"):
    import copy
    n2, p0, xv, n1 = kl.import_harness()
    tasks = kl.read_json(B1 / "stim" / "k1_tasks.json")
    plans = kl.read_json(B1 / "stim" / "k1_plans_M.json")
    rebuilt = kl.read_json(B1 / "meta" / "rebuilt_plans.json")
    pools = {d: kl.read_json(B1 / "stim" / f"k1_pool_{d}.json") for d in kl.DOMAINS}
    clean = (kl.check_g1_rows(pools, tasks, p0.pool_row_id), kl.check_g2_plans(plans, rebuilt)[0])
    pl2 = copy.deepcopy(plans)
    k0 = sorted(pl2["test"]["VC"])[0]
    pl2["test"]["VC"][k0] = list(reversed(pl2["test"]["VC"][k0])) + ["multi_turn_base_60:t0"]
    neg = {"plan entry changed": bool(kl.check_g2_plans(pl2, rebuilt)[0]),
           "empty comparison": bool(kl.check_g2_plans({"test": {}, "train": {}}, {})[0])}
    for name, mut in (("origin G row", {"origin": "G"}), ("failed-turn row", {"label": "FAILED"}),
                      ("test-task source", {"source_task": tasks["VC"]["test"][0]})):
        p2 = copy.deepcopy(pools)
        p2["VC"][0].update(mut)
        neg[name] = bool(kl.check_g1_rows(p2, tasks, p0.pool_row_id))
    neg["empty pools"] = bool(kl.check_g1_rows({d: [] for d in kl.DOMAINS}, tasks, p0.pool_row_id))
    P(f"U15 L10 on the prepared stimuli: G1 {len(clean[0])} and G2 {len(clean[1])} failures; negative controls detected: {neg}")
    ok["U15"] = clean == ([], []) and all(neg.values())

# ---------------------------------------------------------------- U16 C4: block A after a second error / hard limit is NIEUKOŃCZONY
if want("U16"):
    b16 = clone(B1, "u16_A2err")
    r1 = sup(b16, env={"K1_TEST_CRASH_AFTER": "100", "K1_TEST_CRASH_TIMES": "2"})
    inc = rj(b16 / "run" / "A_INCOMPLETE.json") if (b16 / "run" / "A_INCOMPLETE.json").exists() else {}
    nA1 = len(nrows(b16 / "run" / "sessions" / "A.jsonl"))
    log1 = (b16 / "meta" / "supervisor.log").read_text(encoding="utf-8", errors="replace")
    r2 = sup(b16)                                                  # owner decides to continue: no new attempt of block A
    nA2 = len(nrows(b16 / "run" / "sessions" / "A.jsonl"))
    res = rj(b16 / "report" / "results.json") if (b16 / "report" / "results.json").exists() else {}
    rep = (b16 / "report" / "K1_RAPORT.md").read_text(encoding="utf-8") if (b16 / "report" / "K1_RAPORT.md").exists() else ""
    raw = rj(b16 / "meta" / "RAW.json") if (b16 / "meta" / "RAW.json").exists() else {"files": {}}
    b16b = clone(B1, "u16_Ahard")
    r3 = sup(b16b, env={"K1_TEST_HARD_LIMIT": "2600", "K1_TEST_MARGIN": "0.2"})
    inc3 = rj(b16b / "run" / "A_INCOMPLETE.json") if (b16b / "run" / "A_INCOMPLETE.json").exists() else {}
    calls3 = len(nrows(b16b / "run" / "attempts.jsonl"))
    P(f"U16 two errors in A: exit {r1.returncode}, A_INCOMPLETE {inc.get('status')} ({inc.get('reason')}), A_DONE "
      f"{(b16 / 'run' / 'A_DONE.json').exists()}, episodes {nA1}; continued run: exit {r2.returncode}, A episodes {nA2} (no new attempt "
      f"{nA2 == nA1}), report blocks A = {res.get('blocks', {}).get('A')}, block_A {res.get('block_A', {}).get('status')}, checker on A "
      f"{(b16 / 'eval' / 'A.jsonl').exists()}, A in raw freeze {any('sessions' in f and f.endswith('A.jsonl') for f in raw['files'])}, "
      f"NIEUKOŃCZONY in report {'NIEUKOŃCZONY' in rep}, analysed blocks {res.get('completed_sampled_blocks')}; hard limit inside A: exit "
      f"{r3.returncode}, A_INCOMPLETE {inc3.get('status')} ({str(inc3.get('reason'))[:40]}), calls {calls3}")
    ok["U16"] = (r1.returncode == 3 and inc.get("status") == "NIEUKOŃCZONY" and not (b16 / "run" / "A_DONE.json").exists()
                 and "NIEUKOŃCZONY" in log1 and r2.returncode == 0 and nA2 == nA1 and res.get("blocks", {}).get("A") == "NIEUKOŃCZONY"
                 and res.get("block_A", {}).get("status") == "NIEUKOŃCZONY" and not (b16 / "eval" / "A.jsonl").exists()
                 and "NIEUKOŃCZONY" in rep and res.get("completed_sampled_blocks") == ["S1", "S2", "S3"]
                 and str(res.get("block_A", {}).get("M-P", {}).get("state", "")).startswith("NIEWAŻNY")
                 and r3.returncode == 4 and inc3.get("status") == "NIEUKOŃCZONY" and calls3 <= 2600)

P(f"RESULT K1 EXECUTOR TESTS: {'PASS' if ok and all(ok.values()) else 'FAIL'} {ok}; {time.time() - t00:.0f} s")
name = "WYNIKI_TESTOW.out" if not ONLY else f"WYNIKI_{'_'.join(sorted(ONLY))}.out"
(HERE / name).write_text("\n".join(out) + "\n", encoding="utf-8")
