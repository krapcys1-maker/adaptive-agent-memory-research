"""AAMR-NIGHT-2: autonomous program E1-E5 (specification data/lab/aamr-night2/SPEC_AAMR_NIGHT2.md, protocol PROTOCOL.md).

Imports the frozen code of the pilot, S1 and NIGHT-1 and changes none of it. NIGHT-1 module paths are redirected to this
program's folders right after import, so its gateway, session runner and logs write only here.

Resume, budgets, supervisor: as in NIGHT-1. Every attempt is appended to attempts.jsonl before it is sent; every response is
stored under its call key with the sha256 of the full request; completed episodes and forks are never rerun.

Subcommands: compat | smoke | work | supervise | status | analyze | report | freeze
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import random
import re
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT2 = HERE.parent
NDATA2 = ROOT2 / "data/lab/aamr-night2"
NWORK2 = ROOT2.parent / "aamr-night2-2026-11-13"
RUN = Path(os.environ.get("AAMR_NIGHT2_RUN", str(NWORK2 / "run")))
OUT = Path(os.environ.get("AAMR_NIGHT2_OUT", str(NDATA2)))
FAKE = os.environ.get("AAMR_NIGHT2_FAKE") == "1"
SMOKE = False
CONFIG_PATH = NDATA2 / "config.json"
PROTOCOL_PATH = NDATA2 / "PROTOCOL.md"
N1RUN = ROOT2.parent / "aamr-night1-2026-11-12" / "run"            # read-only input

sys.path.insert(0, str(HERE))
import experience_pilot_v0 as p0  # noqa: E402
import experience_xfer_v1 as xv  # noqa: E402
import aamr_night1 as n1  # noqa: E402
import reasoningbank_prompts as rbp  # noqa: E402


def redirect_n1():
    """NIGHT-1's gateway, session runner and logs must write only into NIGHT-2's folders (called by activate)."""
    n1.RUN, n1.NWORK, n1.NDATA, n1.OUT = RUN, NWORK2, NDATA2, OUT
    n1.CONFIG_PATH, n1.PROTOCOL_PATH = CONFIG_PATH, PROTOCOL_PATH


ACTIVE = False


def activate():
    """Called by every entry point before anything can write; importing this module changes nothing in NIGHT-1's module."""
    global ACTIVE
    redirect_n1()
    ACTIVE = True

fsync_append, atomic_json, repair_tail, read_rows, now_iso = n1.fsync_append, n1.atomic_json, n1.repair_tail, n1.read_rows, n1.now_iso
BudgetExhausted, TransientFailure, ProtocolError = n1.BudgetExhausted, n1.TransientFailure, n1.ProtocolError
EXIT_DONE, EXIT_NEXT, EXIT_FATAL, EXIT_TRANSIENT = 0, 10, 2, 3
FUEL_SIG = n1.FUEL_SIG
DOMAINS = ("VC", "GFS", "TRAVEL")
NOTE_CAP = 600
BLOCK_CAP = 2800
STATE_MAX = 8
TEXT_MODE = "text"                                                   # Ollama call without a JSON format (C-RB extraction)
CUT_FACTOR = 1.05
HEADER_SENTENCE = ("Values written as <...> belonged to that earlier task; take the real values from the current request and from your "
                   "own tool results.")
G0_TEMPLATE = ("{function}: this error was also returned in earlier tasks, and repeating the call with guessed arguments did not "
               "resolve it. Before calling {function} again, use a tool that reads the current state this call depends on, and base the "
               "new arguments on what it returns.")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
E1_RETRIEVAL = "e1_retrieval_plan.json"          # amendment 4: the old name e1_plan.json collided with E1_plan.json on Windows
SESSION_SEEDS = {"E1": 20261121, "E3": 20261123, "E4": 20261124, "E5": 20261125}
STAGES = ["preflight_q14", "E1", "E2", "build_c", "E3", "E4", "preflight_q9", "E5", "final"]
DEPENDS = {"E1": ["preflight_q14"], "E2": ["preflight_q14"], "build_c": ["preflight_q14"], "E3": ["E1", "E2"],
           "E4": ["E3", "build_c"], "E5": ["E3", "preflight_q9"]}
SMOKE_STAGES = ["preflight_q14", "smoke_e1", "smoke_e2", "smoke_rb", "preflight_q9", "smoke_q9"]


def log(msg):
    n1.log(msg)


def log_error(msg):
    n1.log_error(msg)


def load_config():
    return p0.read_json(CONFIG_PATH)


def config_id(cfg) -> str:
    return p0.sha({"config": cfg, "protocol_sha256": p0.file_sha(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else None,
                   "spec_sha256": p0.file_sha(NDATA2 / "SPEC_AAMR_NIGHT2.md")})[:16]


# ----------------------------------------------------------------------------- gateway, fake transport, context

class Gateway2(n1.Gateway):
    def payload(self, model_id, messages, schema, seed, keep_alive="10m"):
        p = super().payload(model_id, messages, None if schema == TEXT_MODE else schema, seed, keep_alive)
        if schema == TEXT_MODE:
            p.pop("format")
        return p


class FakeOllama2(n1.FakeOllama):
    def __call__(self, path, body=None, timeout=None):
        if path == "/api/chat" and body is not None:
            fmt = body.get("format")
            if fmt is None:
                self.loaded = body["model"]
                text = ("# Memory Item 1\n## Title Read the state first\n## Description Check the current state before acting.\n"
                        "## Content Call the tool that reports the state, then act on what it returns.")
                return {"model": body["model"], "done": True, "done_reason": "stop", "message": {"content": text},
                        "prompt_eval_count": 100, "eval_count": 30}
            if isinstance(fmt, dict) and "guidance" in fmt.get("properties", {}):
                self.loaded = body["model"]
                return {"model": body["model"], "done": True, "done_reason": "stop",
                        "message": {"content": json.dumps({"guidance": "Core function: does its job. Best practices: read state first."})},
                        "prompt_eval_count": 100, "eval_count": 30}
        return super().__call__(path, body, timeout)


class NoFlash:
    """NIGHT-2 makes no paid call; the NIGHT-1 heartbeat expects this interface."""

    def spent(self):
        return {"paid_calls": 0}


class Ctx:
    def __init__(self, cfg, gw=None, bfcl=None):
        if not ACTIVE:
            raise ProtocolError("aamr_night2.activate() must run before a context is created")
        self.cfg = cfg
        self.gw = gw or Gateway2(cfg, run=RUN, transport=FakeOllama2(cfg) if FAKE else None, sleep=(lambda s: None) if FAKE else time.sleep)
        self.flash = NoFlash()
        self.bfcl = bfcl or n1.bfcl_from(cfg)
        self.names = p0.Names(f"n2_{os.getpid()}_{int(time.time())}")
        self.state = p0.read_json(RUN / "state.json") if (RUN / "state.json").exists() else {"stages": {}}


def heartbeat(ctx, stage, extra=None):
    hb = {"at": now_iso(), "pid": os.getpid(), "stage": stage, "local_calls_total": ctx.gw.total_local, "by_bucket": dict(ctx.gw.by_bucket),
          "paid_calls": 0, "config_id": config_id(ctx.cfg)}
    hb.update(extra or {})
    atomic_json(RUN / "heartbeat.json", hb)


# ----------------------------------------------------------------------------- tasks, training records, pools (read-only inputs)

def domain_of(task_id):
    return n1.domain_of(task_id)


def train_tasks():
    return {"VC": p0.read_json(p0.DATA / "split.json")["train"], "GFS": n1.split("GFS")["train"], "TRAVEL": n1.split("TRAVEL")["train"]}


def test_tasks(bfcl):
    return {"VC": p0.read_json(p0.DATA / "split.json")["test"], "GFS": n1.split("GFS", bfcl)["test"], "TRAVEL": n1.split("TRAVEL", bfcl)["test"]}


def all_train():
    t = train_tasks()
    return t["VC"] + t["GFS"] + t["TRAVEL"]


def all_test(bfcl):
    t = test_tasks(bfcl)
    return t["VC"] + t["GFS"] + t["TRAVEL"]


_RECS = None


def training_records():
    """{task: (record, evaluation)} of the no-memory training runs: VC from the pilot (e1a, e1b), GFS and TRAVEL from NIGHT-1 census."""
    global _RECS
    if _RECS is None:
        recs, evs = n1.pilot_training_records()
        out = {t: (recs[t], evs[t]) for t in recs}
        for r in read_rows(N1RUN / "sessions" / "census.jsonl"):
            out[r["task"]] = (r["episode"], r["evaluation"])
        if set(out) != set(all_train()):
            raise ProtocolError("training records do not match the 60 training tasks")
        _RECS = out
    return _RECS


def n1_memory(domain):
    return p0.read_json(N1RUN / "artifacts" / f"memory_{domain}.json")


def success_pool(domain):
    if domain == "VC":
        return p0.read_jsonl(p0.DATA / "pools" / "A_plus.jsonl")
    return n1_memory(domain)["a_plus"]


def error_pool(domain):
    """All training pool rows (successes and failures), the input of signatures and of the C-G writer."""
    if domain == "VC":
        return n1.vc_pool()
    rows = []
    order = {t: i for i, t in enumerate(train_tasks()[domain])}
    for r in read_rows(N1RUN / "sessions" / "census.jsonl"):
        if domain_of(r["task"]) == domain:
            rows += p0.pool_rows_from_episode(r["episode"], r["evaluation"], order[r["task"]])
    return rows


def test_plan(domain):
    """The traces NIGHT-1 and the pilot chose for R+ on the development-test tasks: {task:turn: [row ids]}."""
    if domain == "VC":
        ret = p0.read_json(p0.DATA / "exposure.json")["retrieval"]
        return {k: v["R+"] for k, v in ret.items()}
    return n1_memory(domain)["rplus_plan"]


# ----------------------------------------------------------------------------- value masking (SPEC 3)

def literal_call(call):
    """(name, {param: python value}) without canonicalising numbers, so kept values print as in the original call."""
    node = ast.parse(call.strip(), mode="eval").body
    return node.func.id, {k.arg: ast.literal_eval(k.value) for k in node.keywords}


def forms(v):
    if isinstance(v, bool) or v is None:
        return set()
    if isinstance(v, (int, float)):
        out = {repr(v), str(v)}
        if float(v).is_integer():
            out |= {str(int(v)), f"{int(v)}.0"}
        return {f for f in out if f}
    s = str(v)
    return {s} if len(s) >= 2 else set()


def num_rx(f):
    return r"(?<![\d.])" + re.escape(f) + r"(?![\d])(?!\.\d)"


def present(v, text):
    """Reference rule (tier_e/n1_04): strings as case-insensitive substrings, numbers only as whole numeric tokens."""
    if isinstance(v, bool) or v is None:
        return False
    if isinstance(v, (int, float)):
        return any(re.search(num_rx(f), text) for f in forms(v))
    low = text.lower()
    return any(f.lower() in low for f in forms(v))


def visible(v, text):
    """Is a value visible as a token (strings word-bounded, case-insensitive; numbers as whole numeric tokens)?"""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return any(re.search(num_rx(f), text) for f in forms(v))
    return any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(f) + r"(?![A-Za-z0-9_])", text, flags=re.IGNORECASE) for f in forms(v))


def _vkey(v):
    return ("n", float(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) else ("s", str(v).lower())


def _scalars(value):
    if isinstance(value, (list, tuple)):
        for v in value:
            yield from _scalars(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _scalars(v)
    elif not (isinstance(value, bool) or value is None):
        yield value


def classify(value, param, req_ctx, prior):
    """SPEC 3 rule 2 for one scalar: (marker, from_request) or None (kept)."""
    if isinstance(value, str) and len(value) < 2:
        return None
    if present(value, req_ctx):
        return f"<{param}>", True
    if present(value, prior):
        return "<from an earlier result>", False
    if isinstance(value, str) and ISO_DATE.match(value):
        return "<YYYY-MM-DD>", False
    return None


def render_value(value, marker_of, inner=None):
    """Masked rendering of one argument value; a kept free-text string has masked values inside it replaced too (inner)."""
    if isinstance(value, bool) or value is None:
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(render_value(v, marker_of, inner) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k!r}: {render_value(v, marker_of, inner)}" for k, v in value.items()) + "}"
    m = marker_of(value)
    if m:
        return m
    if isinstance(value, str) and inner is not None:
        return repr(inner(value))
    return repr(value)


def mask_error(result, kw):
    """Error message masked the way error_key masks it (argument strings, quoted values, numbers), case kept."""
    s = xv.error_text(str(result))
    for a in xv.arg_strings(kw):
        s = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(a) + r"(?![A-Za-z0-9_])", "<arg>", s)
    s = re.sub(r"'[^']*'|\"[^\"]*\"", "<v>", s)
    s = re.sub(r"\d+(?:\.\d+)?", "<n>", s)
    return "error: " + re.sub(r"\s+", " ", s).strip()


def mask_ok(result):
    try:
        obj = json.loads(str(result))
    except (ValueError, TypeError):
        return "ok"
    if isinstance(obj, dict) and obj:
        return "ok {" + ", ".join(obj.keys()) + "}"
    return "ok"


def source_context(row):
    """Requests of the source task before this turn and every tool result of its earlier turns (whole source episode)."""
    rec, _ = training_records()[row["source_task"]]
    turns = rec["turns"][:row["turn"]]
    reqs = " ".join(t["request"] for t in turns)
    results = " ".join(str(c.get("result")) for t in turns for s in t["steps"] for c in s.get("calls", []))
    return reqs, results


def replace_in_request(text, value, mark):
    for f in sorted(forms(value), key=len, reverse=True):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            text = re.sub(num_rx(f), mark, text)
        else:
            text = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(f) + r"(?![A-Za-z0-9_])", mark, text, flags=re.IGNORECASE)
    return text


def replace_visible(text, value, mark):
    return replace_in_request(text, value, mark)


def mask_rows(rows):
    """Masked copies of the traces of one block and, per trace, the values masked in it.

    Pass 1 applies SPEC 3 rule 2 to every argument scalar with the context of the whole source episode. Pass 2 renders: a value
    masked anywhere in the block keeps its first marker wherever it occurs as an argument or in an error message, so that no masked
    value stays visible in the block (an earlier call or an error message would otherwise still show it); own-request occurrences of
    request values are replaced as in rule 2. Successful results show only their top-level keys (rule 3)."""
    infos, block_markers = [], {}
    for row in rows:
        earlier_reqs, prior = source_context(row)
        req_ctx = row["request"] + " " + earlier_reqs
        markers, req_vals, parsed = {}, [], []
        for st in row["steps"]:
            name, kw = literal_call(st["call"])
            for k, v in kw.items():
                for sv in _scalars(v):
                    c = classify(sv, k, req_ctx, prior)
                    if c:
                        markers.setdefault(_vkey(sv), (sv, c[0]))
                        if c[1]:
                            req_vals.append((sv, c[0]))
            parsed.append((name, kw, st))
            prior += " " + str(st["result"])
        infos.append((row, markers, req_vals, parsed))
        for vk, m in markers.items():
            block_markers.setdefault(vk, m)
    out = []
    for row, markers, req_vals, parsed in infos:
        def marker_of(v, markers=markers):
            m = markers.get(_vkey(v)) or block_markers.get(_vkey(v))
            return m[1] if m else None
        def inner(text):
            for sv, mk in sorted(block_markers.values(), key=lambda x: -len(str(x[0]))):
                text = replace_visible(text, sv, mk)
            return text
        steps = []
        for name, kw, st in parsed:
            args = ", ".join(f"{k}={render_value(v, marker_of, inner)}" for k, v in kw.items())
            if st.get("error"):
                _, ckw = xv.parse_call(st["call"])
                res = inner(mask_error(st["result"], ckw))
            else:
                res = mask_ok(st["result"])
            steps.append({"call": f"{name}({args})", "result": res, "error": st.get("error")})
        shown = row["request"]
        for value, mark in sorted(req_vals, key=lambda x: -max([len(f) for f in forms(x[0])] or [0])):
            shown = replace_in_request(shown, value, mark)
        m = dict(row)
        m["request"], m["steps"] = shown, steps
        out.append((m, [sv for sv, _ in markers.values()]))
    return out, [sv for sv, _ in block_markers.values()]


def mask_row(row):
    out, _ = mask_rows([row])
    return out[0]


def masked_block(rows):
    if not rows:
        return ""
    masked, _ = mask_rows(rows)
    text = p0.render_block([m for m, _ in masked])
    first, _, rest = text.partition("\n")
    return p0.truncate(first + " " + HEADER_SENTENCE + "\n" + rest, BLOCK_CAP, "…")


def trace_block(rows, presentation):
    if presentation == "R+":
        return p0.render_block(rows), rows
    if presentation == "M2":
        return masked_block(rows), rows
    if presentation == "M1":
        return masked_block(rows[:1]), rows[:1]
    raise ValueError(presentation)


def plan_provider(plan, rows_by_id, presentation, pool_meta):
    meta = dict(pool_meta, presentation=presentation)

    def block(task_id, ti, request):
        ids = plan.get(f"{task_id}:{ti}", [])
        text, shown = trace_block([rows_by_id[i] for i in ids], presentation)
        return text, [p0.pool_row_id(r) for r in shown], meta
    return block


def leave_one_out_plan(domain, bfcl):
    """E1: for a training task, the pool is the success traces of the other 19 training tasks of its domain (R+ retrieval)."""
    mk = p0.load_kernel()
    pool = success_pool(domain)
    plan = {}
    for t in train_tasks()[domain]:
        rows = [r for r in pool if r["source_task"] != t]
        idx = p0.build_index(mk, rows) if rows else None
        for ti, q in enumerate(bfcl.tasks[t]["question"]):
            if idx is None:
                plan[f"{t}:{ti}"] = []
                continue
            got, _ = p0.retrieve(mk, *idx, q[0]["content"], *p0.UNGATED)
            plan[f"{t}:{ti}"] = [p0.pool_row_id(r) for r in got]
    return plan


def providers(plans, presentation):
    out = {}
    for d in DOMAINS:
        pool = success_pool(d)
        out[d] = plan_provider(plans[d], {p0.pool_row_id(r): r for r in pool}, presentation, {"pool": f"{d} A+", "pool_sha256": p0.sha(pool)})
    return out


# ----------------------------------------------------------------------------- notes: sources, states, forks, X, tournament (SPEC 4)

def det_lessons(domain):
    if domain == "VC":
        return n1.det_lessons_vc()[0]
    return n1_memory(domain)["deterministic_lessons"]


def writer_lessons(domain, source):
    if domain == "VC":
        return n1.valid_lessons(N1RUN / "artifacts" / f"lessons_VC_{source}.json")
    m = n1_memory(domain)
    return [n1.given(r["function"], r["error_key"], r["text"], source) for r in m[source].get("rows", []) if r.get("check", {}).get("ok")]


def g0_text(function):
    return G0_TEMPLATE.format(function=function)


def states(domain):
    """First occurrence of each signature (seen in at least 2 training tasks) in successive training tasks, at most 8 states."""
    recs = {t: training_records()[t][0] for t in train_tasks()[domain]}
    sigs = n1.signatures(error_pool(domain))
    pts = []
    for sig in sigs:
        n = 0
        for t in train_tasks()[domain]:
            found = None
            for turn in recs[t]["turns"]:
                for si, step in enumerate(turn["steps"]):
                    for c in step.get("calls", []):
                        if c["valid"] and c.get("error") and xv.fn(c["call"]) == sig["function"]:
                            _, kw = xv.parse_call(c["call"])
                            if xv.error_key(c["result"], kw) == sig["error_key"]:
                                found = (turn["index"], si)
                                break
                    if found:
                        break
                if found:
                    break
            if found:
                pts.append({"domain": domain, "task": t, "turn": found[0], "step": found[1], "function": sig["function"],
                            "error_key": sig["error_key"], "message": sig["example_message"]})
                n += 1
            if n >= STATE_MAX:
                break
    return sigs, pts


def candidate_texts(domain, sig_key):
    out = {}
    det = {(l["function"], l["error_key"]): xv.note_text(l) for l in det_lessons(domain)}
    if sig_key in det:
        out["D"] = det[sig_key]
    for s in ("Q", "F"):
        m = {(l["function"], l["error_key"]): l["text"] for l in writer_lessons(domain, s)}
        if sig_key in m:
            out[s] = m[sig_key]
    out["G0"] = g0_text(sig_key[0])
    if domain == "VC" and sig_key == FUEL_SIG:
        out.update({"O": n1.ORACLE, "S": n1.STALE, "P": n1.PLACEBO})
    return out


def fork_key(pt, text):
    return f"e2:{pt['task']}:t{pt['turn']}:s{pt['step']}:{p0.sha(text or '')[:12]}"


def first_success_index(fork_steps, function):
    calls = [c for st in fork_steps for c in st["calls"] if c["valid"]]
    for i, c in enumerate(calls):
        if not c.get("error") and xv.fn(c["call"]) == function:
            return calls, i
    return calls, None


def build_x(sig_states, g0_rows, function, message):
    """X from repairs found after G0 in states of at least 2 tasks with the same function sequence (no LLM)."""
    groups = defaultdict(list)
    for pt, r in g0_rows:
        if not (r["resolved"] and r["turn_passed"]):
            continue
        calls, i = first_success_index(r["fork_steps"], function)
        if i is None:
            continue
        seq = tuple(xv.fn(c["call"]) for c in calls[:i])
        ex = "; ".join([f"{c['call']} -> {p0.truncate(str(c['result']), 120, '...')}" for c in calls[:i]] + [f"{calls[i]['call']} -> ok"])
        groups[seq].append((pt["task"], ex))
    best, best_n = None, 1
    for seq, items in groups.items():
        n_tasks = len({t for t, _ in items})
        if n_tasks > best_n:
            best, best_n = seq, n_tasks
    if best is None:
        return None
    exs, seen = [], set()
    for t, ex in groups[best]:
        if t not in seen:
            seen.add(t)
            exs.append(ex)
        if len(exs) == 2:
            break
    how = (f"by calling {', '.join(best)} and then {function} again" if best else f"by calling {function} again")
    text = f'{function}: error "{message}" was resolved in earlier tasks {how}. Examples: {exs[0]} | {exs[1]}.'
    return p0.truncate(text, NOTE_CAP, "…")


def run_fork_row(ctx, pt, source, text, bucket):
    rec, _ = training_records()[pt["task"]]
    key = fork_key(pt, text)
    res = n1.run_fork(ctx.bfcl, ctx.bfcl.tasks[pt["task"]], rec, pt, text, n1.LocalClient(ctx.gw, "q14", bucket), ctx.names, key,
                      p0.ctx_limit({"options": ctx.cfg["models"]["q14"]["options"]}))
    return {"source": source, **pt, "note_sha256": p0.sha(text) if text else None, "note_text": text, **res}


# ----------------------------------------------------------------------------- competitor arms (SPEC 6)

def rb_trajectory(rec, ev):
    parts = []
    for t in rec["turns"]:
        parts.append(f"User request (turn {t['index'] + 1}): {t['request']}")
        for s in t["steps"]:
            if "key" not in s:
                continue
            calls = s.get("calls", [])
            if not calls:
                parts.append("<action>\n(no call: the agent ended the turn)\n</action>")
                continue
            for c in calls:
                call = c.get("call") or json.dumps(c.get("raw"), ensure_ascii=False)
                parts.append(f"<action>\n{call}\n</action>\n<result>\n{p0.truncate(str(c.get('result')), 160)}\n</result>")
    return p0.truncate("\n".join(parts), 16000, "\n...[trajectory truncated]")


def rb_messages(rec, ev):
    query = " | ".join(t["request"] for t in rec["turns"])
    ok = bool(ev["solved"])
    user = "\n\n".join(["## Query and Trajectory Generated Using Previous Memory",
                        f"Query: {query}\nTrajectory:\n{rb_trajectory(rec, ev)}",
                        "## Correctness Signal", "The result is CORRECT." if ok else "The result is INCORRECT.", "## Updated Memory"])
    si = (rbp.SUCCESSFUL_SI if ok else rbp.FAILED_SI).strip()
    return [{"role": "system", "content": si}, {"role": "user", "content": user}], query


RB_ITEM = re.compile(r"#\s*Memory Item[^\n]*\n(.*?)(?=\n\s*#\s*Memory Item|\Z)", re.S)


def parse_rb(text):
    items = []
    for body in RB_ITEM.findall(text.replace("```", "")):
        fields = [(k.lower(), re.sub(r"\s+", " ", v).strip())
                  for k, v in re.findall(r"##\s*(Title|Description|Content)\s*:?\s*(.*?)(?=\n\s*##\s|\Z)", body, re.S)]

        def first(name):
            return next((v for k, v in fields if k == name and v), "")
        descs = [v for k, v in fields if k == "description" and v]
        it = {"title": first("title"), "description": first("description"), "content": first("content")}
        if not it["content"] and len(descs) >= 2:          # the model sometimes labels the content as a second Description
            it["content"] = descs[1]
        if it["title"] or it["content"]:
            items.append(it)
    return items[:3]


def rb_block_text(entry):
    lines = [p0.MEMORY_HEADER]
    for i, it in enumerate(entry["items"], 1):
        lines.append(f"[{i}] Title: {it['title']}\n    Description: {it['description']}\n    Content: {it['content']}")
    return p0.truncate("\n".join(lines), BLOCK_CAP, "…")


def rb_provider(entries):
    """k = 1: the memory of the training episode whose requests are lexically closest to the current request (our kernel)."""
    mk = p0.load_kernel()
    by_dom = defaultdict(list)
    for e in entries:
        if e["items"]:
            by_dom[e["domain"]].append(e)
    idx = {}
    for d, es in by_dom.items():
        rows = [{"request": e["query"], "source_task": e["task"], "turn": 0, "order": i} for i, e in enumerate(es)]
        idx[d] = (p0.build_index(mk, rows), {e["task"]: e for e in es})
    meta = {"kind": "C-RB", "sha256": p0.sha(entries)}

    def block(task_id, ti, request):
        d = domain_of(task_id)
        if d not in idx:
            return "", [], meta
        (index, by_id), entries_by_task = idx[d]
        got, _ = p0.retrieve(mk, index, by_id, request, *p0.UNGATED)
        if not got:
            return "", [], meta
        e = entries_by_task[got[0]["source_task"]]
        return rb_block_text(e), [e["task"]], meta
    return block


def g_tools(domain):
    tasks = defaultdict(set)
    for t in train_tasks()[domain]:
        rec, _ = training_records()[t]
        for turn in rec["turns"]:
            for s in turn["steps"]:
                for c in s.get("calls", []):
                    if c["valid"]:
                        tasks[xv.fn(c["call"])].add(t)
    return [f for f, ts in sorted(tasks.items(), key=lambda kv: (-len(kv[1]), kv[0])) if len(ts) >= 2]


def g_block_provider(bfcl, guidance_by_domain):
    meta = {"kind": "C-G", "sha256": p0.sha(guidance_by_domain)}

    def block(task_id, ti, request):
        g = guidance_by_domain.get(domain_of(task_id), {})
        avail = bfcl.function_names(bfcl.tasks[task_id])
        lines, shown = [xv.LESSON_HEADER], []
        for f, text in g.items():
            if f not in avail:
                continue
            line = f"- {f}: {text}"
            if len("\n".join(lines + [line])) > BLOCK_CAP:
                break
            lines.append(line)
            shown.append(f)
        return ("\n".join(lines) if shown else ""), shown, meta
    return block


# ----------------------------------------------------------------------------- arm definitions

def tr_by_domain(lessons_by_domain):
    return {d: n1.lesson_map(ls) for d, ls in lessons_by_domain.items()}


def notes_t():
    d = p0.read_json(RUN / "artifacts" / "notes_T.json")
    return {dom: d["sets"][dom] for dom in DOMAINS}


def q_sets():
    return {d: writer_lessons(d, "Q") for d in DOMAINS}


def e_star():
    return p0.read_json(RUN / "artifacts" / "e_star.json")["E_star"]


def test_providers(presentation):
    return providers({d: test_plan(d) for d in DOMAINS}, presentation)


def e3_candidates():
    es = e_star()
    blk = test_providers(es)
    T, Q = tr_by_domain(notes_t()), tr_by_domain(q_sets())
    cand = [("N", {}), ("V0", {"block_by_domain": blk, "tr_by_domain": T}), ("N'", {}), ("E*", {"block_by_domain": blk}),
            ("TrT", {"tr_by_domain": T}), ("V0q", {"block_by_domain": blk, "tr_by_domain": Q}), ("TrQ", {"tr_by_domain": Q})]
    if es != "R+":
        cand.append(("R+", {"block_by_domain": test_providers("R+")}))
    return cand


def k_spec():
    k = p0.read_json(RUN / "artifacts" / "k.json")["K"]
    return k, dict(dict(e3_candidates())[k])


def calls_per_episode(model_id, tasks):
    """Projection basis: NIGHT-1 no-memory calls per episode on the same tasks (14B: sA, sD, census, pilot; 9B: sE and the spec)."""
    if model_id == "q9":
        return 12.8
    rows = read_rows(N1RUN / "sessions" / "sA.jsonl") + read_rows(N1RUN / "sessions" / "sD.jsonl") + read_rows(N1RUN / "sessions" / "census.jsonl")
    calls = {r["task"]: r["evaluation"]["model_calls"] for r in rows if r["arm"] == "N"}
    for t, (_, ev) in training_records().items():
        calls.setdefault(t, ev["model_calls"])
    known = [calls[t] for t in tasks if t in calls]
    return sum(known) / len(known) if known else 9.7


def cut_arms(ctx, name, model_id, tasks, candidates, bucket):
    """Drop arms from the end of the priority list when the projection exceeds the stage budget (SPEC 8)."""
    per_ep = calls_per_episode(model_id, tasks)
    remaining = ctx.cfg["budgets"][bucket] - ctx.gw.by_bucket[bucket]
    already = {r["arm"] for r in read_rows(RUN / "sessions" / f"{name}.jsonl")}
    done_calls = sum(r["evaluation"]["model_calls"] for r in read_rows(RUN / "sessions" / f"{name}.jsonl"))
    arms, projected, dropped = {}, 0.0, []
    budget_left = remaining + done_calls                    # the projection covers the whole session, finished episodes included
    for a, spec in candidates:
        cost = per_ep * len(tasks) * CUT_FACTOR
        if a in already or projected + cost <= budget_left:
            arms[a] = dict(spec, bucket=bucket)
            projected += cost
        else:
            dropped.append(a)
    plan = {"arms": list(arms), "dropped_for_budget": dropped, "per_episode": per_ep, "budget_left": budget_left, "projected": projected}
    atomic_json(RUN / "artifacts" / f"{name}_arms.json", plan)          # not *_plan.json: Windows names ignore case
    return arms, plan


# ----------------------------------------------------------------------------- stages

def stage_preflight_q14(ctx):
    for m in ctx.gw.transport("/api/ps", None).get("models", []):
        if m.get("name") not in [x["name"] for x in ctx.cfg["models"].values()]:
            raise TransientFailure("a foreign model is loaded on the GPU: " + str(m.get("name")))
        if m.get("name") != ctx.cfg["models"]["q14"]["name"]:
            ctx.gw.transport("/api/generate", {"model": m["name"], "keep_alive": 0})
    return n1.transport_check(ctx, "q14", "T")


def stage_preflight_q9(ctx):
    ctx.gw.release("q14")
    time.sleep(0 if FAKE else 5)
    return n1.transport_check(ctx, "q9", "T")


def e1_arms():
    plans = {d: p0.read_json(RUN / "artifacts" / E1_RETRIEVAL)[d] for d in DOMAINS}
    return [("N", {}), ("R+", {"block_by_domain": providers(plans, "R+")}), ("M2", {"block_by_domain": providers(plans, "M2")}),
            ("M1", {"block_by_domain": providers(plans, "M1")}), ("N'", {})]


def stage_e1(ctx):
    path = RUN / "artifacts" / E1_RETRIEVAL
    if not path.exists():
        atomic_json(path, {d: leave_one_out_plan(d, ctx.bfcl) for d in DOMAINS})
    tasks = all_train()
    arms, plan = cut_arms(ctx, "E1", "q14", tasks, e1_arms(), "E1")
    out = n1.run_session(ctx, "E1", "q14", tasks, arms, SESSION_SEEDS["E1"])
    import aamr_night2_analysis as an
    sel = an.select_e_star(read_rows(RUN / "sessions" / "E1.jsonl"))
    atomic_json(RUN / "artifacts" / "e_star.json", sel)
    out.update({"arms": list(arms), "dropped_for_budget": plan["dropped_for_budget"], "E_star": sel["E_star"]})
    return out


def stage_e2(ctx):
    path = RUN / "sessions" / "E2.jsonl"
    repair_tail(path)
    done = {(r["source"], r["task"], r["function"], r["error_key"]) for r in read_rows(path)}
    plan = {}
    for d in DOMAINS:
        sigs, pts = states(d)
        plan[d] = {"signatures": len(sigs), "states": len(pts)}
        by_sig = defaultdict(list)
        for pt in pts:
            by_sig[(pt["function"], pt["error_key"])].append(pt)
        for sk, sps in by_sig.items():
            texts = candidate_texts(d, sk)
            jobs = [("none", None)] + [(s, texts[s]) for s in ("D", "Q", "G0", "F", "O", "S", "P") if s in texts]
            for pt in sps:
                for src, text in jobs:
                    if (src, pt["task"], pt["function"], pt["error_key"]) in done:
                        continue
                    row = run_fork_row(ctx, pt, src, text, "E2")
                    fsync_append(path, row)
                    done.add((src, pt["task"], pt["function"], pt["error_key"]))
                    log(f"[E2] {d} {src} {pt['task']} {pt['function']} resolved={row['resolved']} turn_passed={row['turn_passed']}")
                    heartbeat(ctx, "E2")
            rows = [r for r in read_rows(path) if r["domain"] == d and (r["function"], r["error_key"]) == sk]
            g0 = [(next(p for p in sps if p["task"] == r["task"]), r) for r in rows if r["source"] == "G0"]
            x = build_x(sps, g0, sk[0], sps[0]["message"])
            if x is not None:
                for pt in sps:
                    if ("X", pt["task"], pt["function"], pt["error_key"]) in done:
                        continue
                    row = run_fork_row(ctx, pt, "X", x, "E2")
                    row["x_text"] = x
                    fsync_append(path, row)
                    done.add(("X", pt["task"], pt["function"], pt["error_key"]))
                    log(f"[E2] {d} X {pt['task']} {pt['function']} resolved={row['resolved']} turn_passed={row['turn_passed']}")
                    heartbeat(ctx, "E2")
    import aamr_night2_analysis as an
    sel = an.e2_selection(read_rows(path), {d: det_lessons(d) for d in DOMAINS}, q_sets())
    atomic_json(RUN / "artifacts" / "notes_T.json", sel)
    return {"status": "done", "plan": plan, "tool_valid": sel["tool_control"]["valid"], "set_used": sel["set_used"],
            "selected": {d: len(sel["sets"][d]) for d in DOMAINS}}


def stage_build_c(ctx):
    art = RUN / "artifacts"
    rb_path, g_path = art / "c_rb.json", art / "c_g.json"
    entries = p0.read_json(rb_path)["entries"] if rb_path.exists() else []
    have = {e["task"] for e in entries}
    for t in all_train():
        if t in have:
            continue
        rec, ev = training_records()[t]
        msgs, query = rb_messages(rec, ev)
        r = ctx.gw.ask(f"crb:{t}", "q14", msgs, TEXT_MODE, "E4", 7)
        entries.append({"task": t, "domain": domain_of(t), "label": "success" if ev["solved"] else "failure", "query": query,
                        "items": parse_rb(r["text"]), "raw": r["text"], "done_reason": r.get("done_reason"), "request_sha256": r["request_sha256"],
                        "usage": r.get("usage")})
        atomic_json(rb_path, {"entries": entries, "source": "google-research/reasoning-bank instruction.py (Apache-2.0)",
                              "instruction_sha256": p0.file_sha(HERE / "reasoningbank_prompts.py")})
        heartbeat(ctx, "build_c")
    g = p0.read_json(g_path) if g_path.exists() else {"guidance": {}, "writer": []}
    vc = p0.read_json(p0.ROOT / "data/lab/experience-xfer-v1/g-guidance.json")
    g["guidance"]["VC"] = vc["guidance"]
    for d in ("GFS", "TRAVEL"):
        pool = error_pool(d)
        g["guidance"].setdefault(d, {})
        for tool in g_tools(d):
            if tool in g["guidance"][d] or any(w["domain"] == d and w["tool"] == tool for w in g["writer"]):
                continue
            messages, n_hist = xv.guidance_request(ctx.bfcl, tool, pool)
            r = ctx.gw.ask(f"cg:{d}:{tool}", "q14", messages, xv.G_SCHEMA, "E4", 7)
            try:
                text = json.loads(r["text"])["guidance"]
            except (ValueError, TypeError, KeyError):
                text = None
            clean = p0.truncate(re.sub(r"\s+", " ", text).strip(), xv.G_CHARS, "…") if isinstance(text, str) and text.strip() else None
            g["writer"].append({"domain": d, "tool": tool, "history_items": n_hist, "raw_text": r["text"], "guidance": clean,
                                "request_sha256": r["request_sha256"], "usage": r.get("usage")})
            if clean:
                g["guidance"][d][tool] = clean
            atomic_json(g_path, g)
            heartbeat(ctx, "build_c")
    atomic_json(g_path, g)
    return {"status": "done", "rb_entries": len(entries), "rb_with_items": sum(1 for e in entries if e["items"]),
            "g_tools": {d: len(v) for d, v in g["guidance"].items()}}


def stage_e3(ctx):
    tasks = all_test(ctx.bfcl)
    arms, plan = cut_arms(ctx, "E3", "q14", tasks, e3_candidates(), "E3")
    out = n1.run_session(ctx, "E3", "q14", tasks, arms, SESSION_SEEDS["E3"])
    import aamr_night2_analysis as an
    k = an.select_k(read_rows(RUN / "sessions" / "E3.jsonl"))
    atomic_json(RUN / "artifacts" / "k.json", k)
    out.update({"arms": list(arms), "dropped_for_budget": plan["dropped_for_budget"], "K": k["K"]})
    return out


def c_arms(ctx):
    rb = p0.read_json(RUN / "artifacts" / "c_rb.json")["entries"]
    g = p0.read_json(RUN / "artifacts" / "c_g.json")["guidance"]
    return {"C-RB": {"block": rb_provider(rb)}, "C-G": {"block": g_block_provider(ctx.bfcl, g)}}


def stage_e4(ctx):
    tasks = all_test(ctx.bfcl)
    k, spec = k_spec()
    c = c_arms(ctx)
    cand = [("N", {}), ("K", spec), ("C-RB", c["C-RB"]), ("C-G", c["C-G"])]
    arms, plan = cut_arms(ctx, "E4", "q14", tasks, cand, "E4")
    out = n1.run_session(ctx, "E4", "q14", tasks, arms, SESSION_SEEDS["E4"])
    out.update({"arms": list(arms), "K_is": k, "dropped_for_budget": plan["dropped_for_budget"]})
    return out


def stage_e5(ctx):
    tasks = all_test(ctx.bfcl)
    k, spec = k_spec()
    arms, plan = cut_arms(ctx, "E5", "q9", tasks, [("N", {}), ("K", spec), ("N'", {})], "E5")
    out = n1.run_session(ctx, "E5", "q9", tasks, arms, SESSION_SEEDS["E5"])
    ctx.gw.release("q9")
    out.update({"arms": list(arms), "K_is": k, "dropped_for_budget": plan["dropped_for_budget"]})
    return out


def freeze_raw():
    skip = ("heartbeat.json", "supervisor.lock", "progress.log", "supervisor.log", "worker.log", "state.json", "restarts.json")
    files = {p.relative_to(RUN).as_posix(): p0.file_sha(p) for p in sorted(RUN.rglob("*")) if p.is_file() and p.name not in skip and p.suffix != ".tmp"}
    out = {"frozen_at": now_iso(), "raw_root": str(RUN), "files": files}
    atomic_json(OUT / "raw-freeze.json", out)
    return {"files": len(files)}


def git_commit(message):
    try:
        subprocess.run(["git", "add", str(OUT.relative_to(ROOT2))], cwd=str(ROOT2), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", message + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], cwd=str(ROOT2),
                       check=True, capture_output=True)
    except Exception as exc:
        log_error("git commit failed: " + repr(exc))


def stage_final(ctx):
    ctx.gw.release("q14")
    ctx.gw.release("q9")
    import aamr_night2_analysis as an
    fr = freeze_raw()
    OUT.mkdir(parents=True, exist_ok=True)
    res = an.analyze(RUN, OUT)
    an.write_report(res, OUT)
    if not FAKE and OUT == NDATA2:
        git_commit("AAMR-NIGHT-2: frozen raw manifest, results and generated report (autonomous run)")
    return {"status": "done", "frozen_files": fr["files"]}


# ----------------------------------------------------------------------------- technical test (separate folder, counted as T)

def stage_smoke_e1(ctx):
    t = train_tasks()["GFS"][0]
    plans = {d: leave_one_out_plan(d, ctx.bfcl) if d == "GFS" else {} for d in DOMAINS}
    arms = {"N": {"bucket": "T"}, "M2": {"bucket": "T", "block_by_domain": providers(plans, "M2")}}
    return n1.run_session(ctx, "smoke_e1", "q14", [t], arms, 1)


def stage_smoke_e2(ctx):
    _, pts = states("VC")
    pt = next(p for p in pts if (p["function"], p["error_key"]) == FUEL_SIG)
    row = run_fork_row(ctx, pt, "G0", g0_text(pt["function"]), "T")
    fsync_append(RUN / "sessions" / "smoke_e2.jsonl", row)
    return {"status": "done", "resolved": row["resolved"], "turn_passed": row["turn_passed"], "steps": row["live_steps"]}


def stage_smoke_rb(ctx):
    t = train_tasks()["TRAVEL"][0]
    rec, ev = training_records()[t]
    msgs, _ = rb_messages(rec, ev)
    r = ctx.gw.ask(f"crb:{t}", "q14", msgs, TEXT_MODE, "T", 7)
    items = parse_rb(r["text"])
    return {"status": "done" if items else "failed", "items": items, "raw": r["text"][:1500], "done_reason": r.get("done_reason")}


def stage_smoke_q9(ctx):
    t = test_tasks(ctx.bfcl)["VC"][0]
    return n1.run_session(ctx, "smoke_q9", "q9", [t], {"N": {"bucket": "T"}}, 2)


STAGE_FN = {"preflight_q14": stage_preflight_q14, "E1": stage_e1, "E2": stage_e2, "build_c": stage_build_c, "E3": stage_e3, "E4": stage_e4,
            "preflight_q9": stage_preflight_q9, "E5": stage_e5, "final": stage_final, "smoke_e1": stage_smoke_e1, "smoke_e2": stage_smoke_e2,
            "smoke_rb": stage_smoke_rb, "smoke_q9": stage_smoke_q9}


# ----------------------------------------------------------------------------- compatibility test with NIGHT-1 (SPEC 10)

class ReplayClient:
    """Answers with NIGHT-1's stored responses and records whether each request is byte-identical to NIGHT-1's."""

    def __init__(self, gw, cache):
        self.gw, self.cache, self.checked, self.mismatch, self.missing, self.payloads = gw, cache, 0, [], [], {}

    def ask(self, key, messages, seed, output_schema=None):
        hit = self.cache.get(key)
        if hit is None:
            self.missing.append(key)
            raise ProtocolError("no stored NIGHT-1 response for " + key)
        payload = self.gw.payload("q14", messages, output_schema, seed)
        self.checked += 1
        if p0.sha(payload) != hit["request_sha256"]:
            self.mismatch.append(key)
            self.payloads[key] = json.loads(json.dumps(payload, ensure_ascii=False))     # the history list keeps growing
        return hit


def compat(limit=None):
    cfg = load_config()
    bfcl = n1.bfcl_from(cfg)
    gw = Gateway2(cfg, run=NWORK2 / "compat-scratch", transport=lambda *a, **k: (_ for _ in ()).throw(ProtocolError("no calls in compat")))
    cache = {r["key"]: r for r in read_rows(N1RUN / "responses.jsonl")}
    client = ReplayClient(gw, cache)
    names = p0.Names(f"n2compat_{os.getpid()}")
    blocks = test_providers("R+")
    out = {"episodes": 0, "same_records": 0}
    jobs = []
    for sess, arms in (("sA", ("N",)), ("sD", ("N", "R+"))):
        for r in read_rows(N1RUN / "sessions" / f"{sess}.jsonl"):
            if r["arm"] in arms:
                jobs.append((sess, r))
    for sess, r in jobs[:limit]:
        t, a = r["task"], r["arm"]
        block = blocks[domain_of(t)] if a == "R+" else None
        rec = xv.run_episode_x(bfcl, bfcl.tasks[t], client, names, stage=sess, arm=a, key=f"{sess}:{a}:{t}",
                               ctx_limit=p0.ctx_limit({"options": cfg["models"]["q14"]["options"]}), block=block, tr_lessons=None)
        out["episodes"] += 1
        same = [tu["memory"]["block_text"] for tu in rec["turns"]] == [tu["memory"]["block_text"] for tu in r["episode"]["turns"]]
        same &= [[c.get("result") for s in tu["steps"] for c in s.get("calls", [])] for tu in rec["turns"]] == \
                [[c.get("result") for s in tu["steps"] for c in s.get("calls", [])] for tu in r["episode"]["turns"]]
        out["same_records"] += bool(same)
    explained = []
    if client.mismatch:
        want = set(client.mismatch)
        old_req = {}
        with open(N1RUN / "attempts.jsonl", encoding="utf-8") as f:
            for line in f:
                if '"attempt": 0' in line and any(k in line for k in want):
                    a = json.loads(line)
                    if a["key"] in want and a.get("request"):
                        old_req[a["key"]] = a["request"]
        for k in client.mismatch:
            if k in old_req and norm_instances(json.dumps(old_req[k], ensure_ascii=False)) == norm_instances(json.dumps(client.payloads[k], ensure_ascii=False)):
                explained.append(k)
    out.update({"requests_checked": client.checked, "request_mismatches": len(client.mismatch), "mismatch_keys": client.mismatch[:20],
                "mismatches_identical_after_instance_name_normalisation": len(explained), "missing": client.missing[:20]})
    out["ok"] = (len(explained) == len(client.mismatch) and not client.missing and out["episodes"] > 0
                 and out["episodes"] - out["same_records"] <= len({k.rsplit(":", 2)[0] for k in explained}))
    out["note"] = ("requests differ only where the BFCL executor echoes its per-process instance name (unique by design) in an error "
                   "message; identical after normalising that name") if explained else None
    return out


INSTANCE = re.compile(r"xp0_[A-Za-z0-9_]*?_(?:live|fork)_\d+_")


def norm_instances(text):
    return INSTANCE.sub("<instance>_", text)


# ----------------------------------------------------------------------------- worker, supervisor

def write_state(ctx):
    atomic_json(RUN / "state.json", ctx.state)


def guard_environment(cfg):
    if not re.match(r"^http://(127\.0\.0\.1|localhost):\d+$", cfg["base_url"]):
        raise ProtocolError("model calls must go only to the local Ollama")
    if cfg.get("paid_calls", 0) != 0:
        raise ProtocolError("paid calls are not allowed in NIGHT-2")


def stop_fatal(reason):
    atomic_json(RUN / "STOPPED.json", {"at": now_iso(), "reason": reason})


def work(stages=None) -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    n1.prevent_sleep()
    cfg = load_config()
    guard_environment(cfg)
    ctx = Ctx(cfg)
    if ctx.state.get("config_id") not in (None, config_id(cfg)):
        log_error("config, protocol or specification changed during the run; refusing to continue")
        return EXIT_FATAL
    ctx.state["config_id"] = config_id(cfg)
    order = stages or (SMOKE_STAGES if SMOKE else STAGES)
    stage = next((s for s in order if ctx.state["stages"].get(s, {}).get("status") not in ("done", "partial", "skipped", "failed")), None)
    if stage is None:
        (RUN / "DONE.json").write_text(json.dumps({"at": now_iso(), "stages": ctx.state["stages"]}, indent=2, default=str), encoding="utf-8")
        return EXIT_DONE
    bad = [d for d in DEPENDS.get(stage, []) if ctx.state["stages"].get(d, {}).get("status") not in ("done", "partial")]
    if bad and stage != "final":
        ctx.state["stages"][stage] = {"status": "skipped", "reason": "dependency not done: " + ", ".join(bad), "at": now_iso()}
        write_state(ctx)
        log(f"stage {stage} skipped: dependency {bad}")
        return EXIT_NEXT
    log(f"stage {stage} starting (local calls so far {ctx.gw.total_local})")
    heartbeat(ctx, stage)
    st = ctx.state["stages"].setdefault(stage, {})
    st["started_at"] = st.get("started_at") or now_iso()
    write_state(ctx)
    try:
        result = STAGE_FN[stage](ctx)
    except TransientFailure as exc:
        log_error(f"stage {stage} transient failure: {exc}")
        return EXIT_TRANSIENT
    except BudgetExhausted as exc:
        st.update({"status": "partial", "reason": "budget " + str(exc), "at": now_iso()})
        write_state(ctx)
        log_error(f"stage {stage} stopped by budget {exc}")
        if str(exc) == "total_local":
            for s in STAGES:
                if s != "final" and ctx.state["stages"].get(s, {}).get("status") is None:
                    ctx.state["stages"][s] = {"status": "skipped", "reason": "total local budget exhausted"}
            write_state(ctx)
        return EXIT_NEXT
    except RuntimeError as exc:
        if "reserved TradingBot" in str(exc) or "TradingBot outside" in str(exc) or "only to the local Ollama" in str(exc):
            log_error(f"guard violation in {stage}: {exc}")
            stop_fatal(f"guard violation: {exc}")
            return EXIT_FATAL
        return _stage_error(ctx, st, stage, exc)
    except Exception as exc:
        return _stage_error(ctx, st, stage, exc)
    st.update(result if isinstance(result, dict) else {"status": "done"})
    st.setdefault("status", "done")
    st["finished_at"] = now_iso()
    write_state(ctx)
    log(f"stage {stage} -> {st['status']}")
    heartbeat(ctx, stage, {"stage_status": st["status"]})
    return EXIT_NEXT


def _stage_error(ctx, st, stage, exc):
    st["errors"] = st.get("errors", 0) + 1
    log_error(f"stage {stage} error {st['errors']}: {exc!r}\n{traceback.format_exc()}")
    if st["errors"] >= 2:
        st.update({"status": "failed", "reason": repr(exc)[:500], "at": now_iso()})
    write_state(ctx)
    return EXIT_NEXT if st["errors"] >= 2 else EXIT_TRANSIENT


def supervise() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / "DONE.json").exists() or (RUN / "STOPPED.json").exists():
        return 0
    lock = RUN / "supervisor.lock"
    if lock.exists():
        try:
            if n1.pid_alive(int(lock.read_text().strip())):
                return 0
        except ValueError:
            pass
    lock.write_text(str(os.getpid()))
    n1.prevent_sleep()
    sup = load_config()["supervisor"]
    restarts_path = RUN / "restarts.json"
    restarts = p0.read_json(restarts_path)["count"] if restarts_path.exists() else 0
    try:
        while True:
            with open(RUN / "worker.log", "a", encoding="utf-8") as wl:
                proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "work"] + (["--smoke"] if SMOKE else []), cwd=str(ROOT2),
                                        stdout=wl, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                started = time.time()
                while proc.poll() is None:
                    time.sleep(1 if FAKE else sup.get("poll_seconds", 30))
                    hb = RUN / "heartbeat.json"
                    last = max(started, hb.stat().st_mtime if hb.exists() else 0)
                    if time.time() - last > sup["stall_seconds"]:
                        log_error("worker heartbeat stalled; terminating worker")
                        proc.kill()
                        proc.wait()
                        break
                rc = proc.returncode
            if rc == EXIT_NEXT:
                continue
            if rc == EXIT_DONE:
                log("program finished")
                return 0
            if rc == EXIT_FATAL:
                if not (RUN / "STOPPED.json").exists():
                    stop_fatal("fatal: configuration changed or a guard reported a violation (see errors.log)")
                return 2
            restarts += 1
            atomic_json(restarts_path, {"count": restarts, "at": now_iso(), "last_rc": rc})
            if restarts > sup["max_restarts"]:
                stop_fatal(f"technical failures exceeded {sup['max_restarts']} restarts (last rc {rc}); all data kept, see errors.log")
                log_error("too many restarts; stopping safely")
                return 3
            log_error(f"worker exited with {rc}; restart {restarts} after {sup['restart_wait_seconds']} s")
            time.sleep(1 if FAKE else (15 if SMOKE else sup["restart_wait_seconds"]))
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def status() -> dict:
    out = {"run": str(RUN)}
    for name in ("state.json", "heartbeat.json", "DONE.json", "STOPPED.json", "restarts.json"):
        p = RUN / name
        if p.exists():
            out[name] = p0.read_json(p)
    return out


def set_run(path: Path):
    global RUN
    RUN = path
    activate()


def main(argv=None):
    global SMOKE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["work", "supervise", "status", "analyze", "report", "freeze", "compat"])
    ap.add_argument("--stages", nargs="*")
    ap.add_argument("--smoke", action="store_true", help="technical test in a separate run folder (counted as budget T)")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    activate()
    if a.smoke:
        SMOKE = True
        set_run(NWORK2 / "smoke-run")
    if a.cmd == "work":
        return work(a.stages)
    if a.cmd == "supervise":
        return supervise()
    if a.cmd == "status":
        print(json.dumps(status(), indent=2, default=str)[:20000])
        return 0
    if a.cmd == "freeze":
        print(freeze_raw())
        return 0
    if a.cmd == "compat":
        res = compat(a.limit)
        print(json.dumps(res, indent=2))
        return 0 if res["ok"] else 1
    import aamr_night2_analysis as an
    OUT.mkdir(parents=True, exist_ok=True)
    res = an.analyze(RUN, OUT)
    if a.cmd == "report":
        an.write_report(res, OUT)
    print(json.dumps({k: res[k] for k in list(res)[:8]}, indent=2, default=str)[:8000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
