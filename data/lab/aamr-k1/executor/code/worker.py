"""K1 episode process. The audit hook is installed before any harness import (spec sec. 5, L6a).
Phases:
  T  preflight (version, digest, foreign models, 3 transport probes), c_d calibration and T-length (b) (spec sec. 2, 6.3),
     P checks with c_d (header, length to target, L4b), freeze of c_d, and the m measurement (arm N, 12 training tasks,
     temperature 0.7; call counts only)
  A  budget gate before A (spec sec. 10), block A (temperature 0, arms N, M, P)
  S  sampled blocks S1-S3, each behind its own budget gate (arms N, P, X, S, M)
The process never sees outcomes (the checker runs in a separate process after the raw data are closed).
Usage: python -I -X utf8 -B worker.py --base DIR --phase {T,A,S} --transport {ollama,fake,replay} [--only-arms N,M]
--only-arms is accepted only with the replay transport (T-zgodność test)."""
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
import k1_audit_hook as hook  # noqa: E402
import k1_lib as kl  # noqa: E402

ARGS = dict(zip(sys.argv[1::2], sys.argv[2::2]))
BASE = Path(ARGS["--base"]).resolve()
PHASE, TRANSPORT = ARGS["--phase"], ARGS.get("--transport", "ollama")
ONLY = ARGS.get("--only-arms")
L = kl.layout(BASE)
REPLAY_MAP = BASE / "testdata" / "replay_map.json"
hook.install(**kl.worker_policy(L, [REPLAY_MAP] if TRANSPORT == "replay" else []))

import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402
from types import SimpleNamespace  # noqa: E402

if ONLY and TRANSPORT != "replay":
    raise SystemExit("--only-arms is a test option of the replay transport")
n2, p0, xv, n1 = kl.import_harness()
if TRANSPORT == "replay" and os.environ.get("K1_TEST_MUTANT"):     # T-zgodność mutant (replay only): block stays in history
    import inspect
    _src = inspect.getsource(xv.run_episode_x)
    _old = 'history[start] = {"role": "user", "content": request}'
    if _src.count(_old) != 1:
        raise SystemExit("mutation anchor not found exactly once")
    _ns = dict(vars(xv))
    exec(compile(_src.replace(_old, "pass"), "<mutant run_episode_x>", "exec"), _ns)
    xv.run_episode_x = _ns["run_episode_x"]
for name in ("RUN", "NWORK", "NDATA", "OUT"):                      # NIGHT-1 logging and ledger write only into this run dir
    setattr(n1, name, L["run"])
cfg = kl.load_cfg()
if TRANSPORT == "fake" and os.environ.get("K1_TEST_HARD_LIMIT"):  # test seam: smaller hard limit, fake transport only
    cfg["hard_limit"] = cfg["budgets"]["total_local"] = int(os.environ["K1_TEST_HARD_LIMIT"])
if TRANSPORT == "fake" and os.environ.get("K1_TEST_MARGIN"):      # test seam: too small a margin -> hard limit inside a block
    cfg["margin"] = float(os.environ["K1_TEST_MARGIN"])
CRASH_AFTER = int(os.environ.get("K1_TEST_CRASH_AFTER", "0")) if TRANSPORT == "fake" else 0
L["run"].mkdir(parents=True, exist_ok=True)
STIM = L["stim"]


class ReplayTransport:
    """Test transport (T-zgodność): answers /api/chat with NIGHT-2's stored response for a byte-identical request (sha256),
    else for a request identical after executor-instance normalisation; counts misses. No model."""

    def __init__(self):
        m = json.loads(REPLAY_MAP.read_text(encoding="utf-8"))
        self.by_sha, self.by_norm = m["by_sha"], m["by_norm"]
        self.hits = {"sha": 0, "norm": 0, "miss": 0}

    def __call__(self, path, body=None, timeout=None):
        if path != "/api/chat":
            return {"version": "replay", "models": []}
        r = self.by_sha.get(p0.sha(body))
        kind = "sha"
        if r is None:
            r = self.by_norm.get(p0.sha(n2.norm_instances(json.dumps(body["messages"], ensure_ascii=False))))
            kind = "norm"
        if r is None:
            kind, r = "miss", {"text": '{"calls": []}', "done_reason": "stop", "usage": {}}
        self.hits[kind] += 1
        (L["run"] / "replay_hits.json").write_text(json.dumps(self.hits), encoding="utf-8")
        return dict({"model": body["model"], "done": True, "done_reason": r.get("done_reason"), "message": {"content": r["text"]}},
                    **(r.get("usage") or {}))


class CachingFake:
    """Test seam (K1_TEST_FAKE_CACHE=1, fake transport only): a repeated identical request reports only a cache remainder
    as prompt_eval_count, the behaviour the T12 reference check must catch."""

    def __init__(self, inner):
        self.inner, self.seen = inner, set()

    def __call__(self, path, body=None, timeout=None):
        r = self.inner(path, body, timeout)
        if path == "/api/chat":
            k = p0.sha(body["messages"])
            if k in self.seen:
                r = dict(r, prompt_eval_count=7)
            self.seen.add(k)
        return r


def transport():
    if TRANSPORT == "fake":
        fake = n1.FakeOllama(cfg)
        return (CachingFake(fake) if os.environ.get("K1_TEST_FAKE_CACHE") else fake), (lambda s: None)
    if TRANSPORT == "replay":
        return ReplayTransport(), (lambda s: None)
    return None, time.sleep


def heartbeat(stage, extra=None):
    """Best effort: on Windows os.replace onto heartbeat.json fails (WinError 5) while the coordinator's runner is reading
    it; a heartbeat must never crash the episode process (found by tests/test_coordinator_runner.py). A missed write only
    makes the heartbeat older; the stall detectors (supervisor 40 min, runner 45 min) are far above one episode."""
    for i in range(5):
        try:
            n1.atomic_json(L["run"] / "heartbeat.json", dict({"at": n1.now_iso(), "stage": stage, "pid": os.getpid()}, **(extra or {})))
            return
        except PermissionError:
            time.sleep(0.05 * (i + 1))


def preflight(gw, bfcl):
    ps = gw.transport("/api/ps", None).get("models", [])
    foreign = [m.get("name") for m in ps if m.get("name") != cfg["models"]["q14"]["name"]]
    if foreign:                                   # never unload another process's model; stop instead
        return {"status": "failed", "reason": "foreign model loaded: " + ", ".join(map(str, foreign))}
    return n1.transport_check(SimpleNamespace(gw=gw, bfcl=bfcl, cfg=cfg), "q14", "T")


# ----------------------------------------------------------------------------- stage T: c_d and T-length (b)

def t_stage(gw, bfcl, provs, idx):
    tl = kl.read_json(STIM / "k1_T_tasks.json")
    tok = kl.read_json(STIM / "k1_tokref.json")
    corpus = kl.read_json(STIM / "k1_corpus_P.json")["sentences"]
    lo, hi = cfg["T"]["plausible_tokens_per_char"]

    def nref(t, messages_n):
        # real model: NIGHT-2's prompt_eval_count of arm N, turn 0, step 0 (spec sec. 2, P: "odjęty od wartości N z NIGHT-2");
        # fake transport: the fake's own count of the N prompt (FakeOllama counts characters), so the test is consistent
        return tok["nref"][t] if TRANSPORT == "ollama" else len(json.dumps(messages_n)) // 3

    def measure(label, d, tasks, c):
        out = []
        for t in tasks:
            task = bfcl.tasks[t]
            _, _, part = idx[t]
            req = task["question"][0][0]["content"]
            mb = provs["_m_text"](part, d, t, 0, req)
            pb = kl.build_p(mb, corpus, c, (t, 0, label))
            sysm = {"role": "system", "content": p0.system_prompt(bfcl, task)}
            msgs = [sysm, {"role": "user", "content": pb + "\n\n" + req}]
            r = gw.ask(f"T:{label}:{t}", "q14cal", msgs, p0.output_schema(bfcl, task), "T", 7)
            pec = (r.get("usage") or {}).get("prompt_eval_count")
            if pec is None:
                raise n1.ProtocolError(f"no prompt_eval_count for T:{label}:{t}")
            ptok = pec - nref(t, [sysm, {"role": "user", "content": req}])
            chars = len(pb)                                    # C1: rho = block tokens / block characters (v1.0 sec. 2)
            if not lo <= ptok / chars <= hi:
                raise n1.ProtocolError(f"implausible P token count for T:{label}:{t}: {ptok} tokens / {chars} chars")
            out.append({"task": t, "p_tokens": ptok, "p_chars": chars, "m_tokens": tok["m_t0_tokens"][t]})
            heartbeat("T", {"label": label, "local_calls": gw.total_local})
        return out

    # T12 (proposed, not approved): token reference check before calibration. For the first calibration task of each
    # domain the arm-N turn-0 prompt is sent twice (num_predict 1); both prompt_eval_count values must equal the
    # reference. Detects counts that are cache remainders (second identical call) and a tokenizer/template change against
    # NIGHT-2 (first call), both of which would silently bias c_d. 6 calls inside the T budget.
    ref = []
    for d in kl.DOMAINS:
        t = tl["cal"][d][0]
        task = bfcl.tasks[t]
        msgs = [{"role": "system", "content": p0.system_prompt(bfcl, task)}, {"role": "user", "content": task["question"][0][0]["content"]}]
        for rep in (1, 2):
            r = gw.ask(f"T:ref:{t}:{rep}", "q14cal", msgs, p0.output_schema(bfcl, task), "T", 7)
            got = (r.get("usage") or {}).get("prompt_eval_count")
            ref.append({"task": t, "rep": rep, "prompt_eval_count": got, "reference": nref(t, msgs)})
        heartbeat("T", {"label": "ref", "local_calls": gw.total_local})
    bad_ref = [x for x in ref if x["prompt_eval_count"] != x["reference"]]
    if bad_ref:
        n1.atomic_json(L["run"] / "T_ref_FAILED.json", ref)
        raise n1.ProtocolError(f"token reference check failed (cache remainder or tokenizer change): {bad_ref[:2]}")

    rho_m = tok["rho_dom"]
    res = {"rho_M": rho_m, "domains": {}, "ref_check": ref}
    c_d = {}
    for d in kl.DOMAINS:
        cal = measure("cal", d, tl["cal"][d], 1.0)
        rho_p = sum(x["p_tokens"] for x in cal) / sum(x["p_chars"] for x in cal)
        c = rho_m[d] / rho_p
        chk = measure("len", d, tl["len"][d], c)
        rel = sum(x["p_tokens"] for x in chk) / sum(x["m_tokens"] for x in chk) - 1
        rec = {"rho_P": rho_p, "c_d": c, "T_length_rel": rel, "pass": abs(rel) <= cfg["T"]["len_tolerance"], "cal": cal, "len": chk}
        if not rec["pass"]:                                        # one recalibration on 20 new blocks, then one new check
            rcal = measure("recal", d, tl["recal"][d], 1.0)
            rho_p2 = sum(x["p_tokens"] for x in rcal) / sum(x["p_chars"] for x in rcal)
            c = rho_m[d] / rho_p2
            chk2 = measure("len2", d, tl["len2"][d], c)
            rel2 = sum(x["p_tokens"] for x in chk2) / sum(x["m_tokens"] for x in chk2) - 1
            rec.update(recal={"rho_P": rho_p2, "c_d": c, "T_length_rel": rel2, "blocks": rcal, "len": chk2},
                       pass_after_recal=abs(rel2) <= cfg["T"]["len_tolerance"])
        c_d[d] = c
        res["domains"][d] = rec
    ok = all(r["pass"] or r.get("pass_after_recal") for r in res["domains"].values())
    res.update(c_d=c_d, status="done" if ok else "failed", at=n1.now_iso())
    return res, ok


def p_checks(provs_p, idx, bfcl, c_d):
    """With the final c_d: header, |len - target| <= 12 and L4b for every P block of instances 0-3 (spec 6.3, L4b)."""
    lists = kl.read_json(STIM / "k1_l4_lists.json")
    fw = set(lists["function_words"])
    plans = kl.plan_turns(kl.read_json(STIM / "k1_plans_M.json"), idx)
    n, hdr, dev, jac, texts = 0, 0, 0, 0.0, {}
    for t, (_, d, part) in sorted(idx.items()):
        task = bfcl.tasks[t]
        for ti in sorted(plans[t]):
            req = task["question"][ti][0]["content"]
            mb = provs_p["_m_text"](part, d, t, ti, req)
            for inst in (0, 1, 2, 3):
                pb = provs_p["P"](inst)[part][d](t, ti, req)[0]
                if not mb:
                    if pb:
                        hdr += 1
                    continue
                n += 1
                texts[f"{t}:{ti}:{inst}"] = p0.sha(pb)
                hdr += pb.split("\n", 1)[0] != kl.HEADER
                dev = max(dev, abs(len(kl.content(pb)) - round(c_d[d] * len(kl.content(mb)))))
                jac = max(jac, kl.l4b(pb, req, fw))
    ok = n > 0 and hdr == 0 and dev <= 12 and jac <= cfg["l4b_max_jaccard"]
    return {"blocks": n, "header_failures": hdr, "max_len_dev": dev, "L4b_max": jac, "pass": ok,
            "p_blocks_sha256": kl.sha_obj(texts)}, ok


def m_measure(gw, bfcl):
    tl = kl.read_json(STIM / "k1_T_tasks.json")
    client = n1.LocalClient(gw, cfg["T"]["m_model"], "T")
    ctx_limit = p0.ctx_limit({"options": cfg["models"][cfg["T"]["m_model"]]["options"]})
    names = p0.Names(f"k1T_{os.getpid()}")
    calls = []
    for t in tl["m_tasks"]:
        rec = xv.run_episode_x(bfcl, bfcl.tasks[t], client, names, stage="T", arm="N", key=f"T:m:N:{t}", ctx_limit=ctx_limit,
                               block=None, tr_lessons=None, seed=cfg["T"]["m_seed"])
        calls.append(kl.episode_calls(rec))                         # only the call count is kept (spec sec. 10)
        heartbeat("T", {"m_episodes": len(calls), "local_calls": gw.total_local})
    return {"tasks": tl["m_tasks"], "calls": calls, "mean": sum(calls) / len(calls), "at": n1.now_iso()}


# ----------------------------------------------------------------------------- blocks A, S1-S3

def run_block(gw, bfcl, provs, idx, block, names):
    b = cfg["blocks"][block]
    client = n1.LocalClient(gw, b["model"], block)
    ctx_limit = p0.ctx_limit({"options": cfg["models"][b["model"]]["options"]})
    path = L["run"] / "sessions" / f"{block}.jsonl"
    n1.repair_tail(path)
    done = {(r["task"], r["arm"]) for r in n1.read_rows(path)}
    arms = ONLY.split(",") if ONLY else b["arms"]
    plan = kl.block_plan(block, sorted(idx), arms)
    fns = {a: provs[a](b["instance"]) for a in arms}
    for k, (t, a) in enumerate(plan):
        if (t, a) in done:
            continue
        _, d, part = idx[t]
        rec = xv.run_episode_x(bfcl, bfcl.tasks[t], client, names, stage=block, arm=a, key=f"{block}:{a}:{t}", ctx_limit=ctx_limit,
                               block=fns[a][part][d] if fns[a] else None, tr_lessons=None, seed=b["seed"])
        n1.fsync_append(path, {"block": block, "task": t, "arm": a, "instance": b["instance"], "calls": kl.episode_calls(rec),
                               "episode": rec})
        heartbeat(block, {"episodes": k + 1, "of": len(plan), "local_calls": gw.total_local})
        if (k + 1) % 50 == 0:
            n1.log(f"{block}: {k + 1}/{len(plan)} episodes, local calls {gw.total_local}")      # counts only, no outcomes (L7)
        if CRASH_AFTER and k + 1 >= CRASH_AFTER:                    # test seam (fake only): K1_TEST_CRASH_TIMES crashes per block
            mk = L["run"] / f"crashed_{block}"
            n_crash = int(mk.read_text(encoding="utf-8")) if mk.exists() else 0
            if n_crash < int(os.environ.get("K1_TEST_CRASH_TIMES", "1")):
                mk.write_text(str(n_crash + 1), encoding="utf-8")
                raise RuntimeError("K1_TEST_CRASH_AFTER: injected crash (test)")
    rows = n1.read_rows(path)
    n1.atomic_json(L["run"] / f"{block}_DONE.json", {"episodes": len(rows), "calls": sum(r["calls"] for r in rows), "at": n1.now_iso()})
    return rows


def sampled_m():
    """m before a sampled block: mean calls per episode over every temperature-0.7 episode so far (T measurement, then
    completed sampled blocks); call counts only, never outcomes (spec sec. 10)."""
    calls = list(kl.read_json(L["run"] / "T_m.json")["calls"])
    for b in kl.SAMPLED:
        if (L["run"] / f"{b}_DONE.json").exists():
            calls += [r["calls"] for r in n1.read_rows(L["run"] / "sessions" / f"{b}.jsonl")]
    return sum(calls) / len(calls)


def main():
    tr, sleep = transport()
    gw = n1.Gateway(cfg, run=L["run"], transport=tr, sleep=sleep)
    bfcl = kl.make_bfcl_k1(p0, xv, n1)(kl.BFCL)
    idx = kl.task_index(kl.read_json(STIM / "k1_tasks.json"))
    names = p0.Names(f"k1_{os.getpid()}")
    if PHASE == "T":
        provs0 = kl.make_providers(n2, p0, STIM)
        if TRANSPORT != "replay" and not (L["run"] / "T.json").exists():
            res = preflight(gw, bfcl)
            n1.atomic_json(L["run"] / "T.json", res)
            if res.get("status") != "done":
                n1.log_error("preflight failed: " + str(res.get("reason")))
                return kl.EXIT_PREFLIGHT
        if not (L["run"] / "c_d.json").exists():
            res, ok = t_stage(gw, bfcl, provs0, idx)
            n1.atomic_json(L["run"] / ("c_d.json" if ok else "c_d_FAILED.json"), res)
            if not ok:
                n1.log_error("T-length (b) failed after one recalibration: owner decision")
                return kl.EXIT_GATE
        c_d = kl.read_json(L["run"] / "c_d.json")["c_d"]
        if not (L["run"] / "P_check.json").exists():
            chk, ok = p_checks(kl.make_providers(n2, p0, STIM, c_d), idx, bfcl, c_d)
            n1.atomic_json(L["run"] / "P_check.json", chk)
            if not ok:
                n1.log_error(f"P check with c_d failed: {chk}")
                return kl.EXIT_FATAL
        if not (L["run"] / "STIM_T_FROZEN.json").exists():                # c_d and P blocks frozen before the first experimental call
            n1.atomic_json(L["run"] / "STIM_T_FROZEN.json", {"c_d.json": kl.sha_file(L["run"] / "c_d.json"),
                                                            "p_blocks_sha256": kl.read_json(L["run"] / "P_check.json")["p_blocks_sha256"],
                                                            "at": n1.now_iso()})
        if not (L["run"] / "T_m.json").exists():
            n1.atomic_json(L["run"] / "T_m.json", m_measure(gw, bfcl))
        n1.atomic_json(L["run"] / "T_DONE.json", {"local_calls": gw.total_local, "at": n1.now_iso()})
        return kl.EXIT_DONE
    frozen = kl.read_json(L["run"] / "STIM_T_FROZEN.json") if (L["run"] / "STIM_T_FROZEN.json").exists() else None
    if TRANSPORT == "replay":
        c_d = {d: 1.0 for d in kl.DOMAINS}
    else:
        if frozen is None or kl.sha_file(L["run"] / "c_d.json") != frozen["c_d.json"]:
            raise n1.ProtocolError("c_d missing or changed after stage T (L8)")
        c_d = kl.read_json(L["run"] / "c_d.json")["c_d"]
    provs = kl.make_providers(n2, p0, STIM, c_d)
    if PHASE == "A":
        if TRANSPORT != "replay" and not (L["run"] / "gate_A.json").exists():
            n1.atomic_json(L["run"] / "gate_A.json", kl.gate_before_a(gw.total_local, kl.read_json(L["run"] / "T_m.json")["mean"], cfg))
        if TRANSPORT != "replay" and not kl.read_json(L["run"] / "gate_A.json")["go"]:
            n1.log_error("budget gate before A: stop (owner decision)")
            return kl.EXIT_GATE
        if (L["run"] / "A_INCOMPLETE.json").exists():                 # C4: never resumed or retried
            return kl.EXIT_DONE
        try:
            run_block(gw, bfcl, provs, idx, "A", names)
        except n1.BudgetExhausted as exc:                            # C4: hard limit inside A -> NIEUKOŃCZONY, stop (code 4)
            n1.atomic_json(L["run"] / "A_INCOMPLETE.json", {"reason": f"hard limit: {exc}", "status": "NIEUKOŃCZONY",
                                                           "local_calls": gw.total_local, "at": n1.now_iso()})
            raise
        return kl.EXIT_DONE
    for b in kl.SAMPLED[:cfg.get("sampled_blocks", 3)]:
        if (L["run"] / f"{b}_DONE.json").exists() or (L["run"] / f"{b}_ABORTED.json").exists():
            continue
        if (L["run"] / "S_SKIPPED.json").exists():
            break
        gp = L["run"] / f"gate_{b}.json"
        if not gp.exists():
            n1.atomic_json(gp, kl.gate_before_s(gw.total_local, sampled_m(), cfg))
        if not kl.read_json(gp)["go"]:
            n1.log(f"budget gate before {b}: {b} and later blocks skipped")
            n1.atomic_json(L["run"] / "S_SKIPPED.json", {"from": b, "gate": kl.read_json(gp), "at": n1.now_iso()})
            break
        try:
            run_block(gw, bfcl, provs, idx, b, names)
        except n1.BudgetExhausted as exc:                           # hard limit inside a sampled block: block incomplete (7.2)
            n1.log_error(f"hard limit reached inside {b}: {exc}; block incomplete")
            n1.atomic_json(L["run"] / f"{b}_INCOMPLETE.json", {"reason": "hard limit", "local_calls": gw.total_local, "at": n1.now_iso()})
            n1.atomic_json(L["run"] / "S_SKIPPED.json", {"from": b, "reason": "hard limit", "at": n1.now_iso()})
            break
    n1.atomic_json(L["run"] / "S_DONE.json", {"local_calls": gw.total_local, "at": n1.now_iso()})
    return kl.EXIT_DONE


if __name__ == "__main__":
    try:
        rc = main()
    except n1.BudgetExhausted as exc:
        n1.log_error(f"hard limit reached: {exc}")
        rc = kl.EXIT_GATE
    except n1.TransientFailure as exc:
        n1.log_error(f"transient failure: {exc}")
        rc = kl.EXIT_TRANSIENT
    except (n1.ProtocolError, RuntimeError) as exc:
        if "K1_TEST_CRASH_AFTER" in str(exc):
            n1.log_error(f"crash: {exc!r}")
            rc = 1
        else:
            n1.log_error(f"fatal: {exc!r}")
            rc = kl.EXIT_FATAL
    sys.stdout.flush()
    os._exit(rc)
