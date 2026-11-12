"""AAMR-NIGHT-1: autonomous overnight research program (protocol: data/lab/aamr-night1/PROTOCOL.md, frozen before any model call).

One program, fixed stages, fixed arms, fixed decision rules. It runs without Claude Code: the Windows Task Scheduler starts
`supervise`, the supervisor runs `work` once per stage in a child process and restarts it after a technical failure.

Resume: every model response is stored under its call key with the sha256 of the full request. A restarted episode replays
stored responses (no new call, no second charge) and continues live where it stopped. Completed episodes are never rerun.
Budgets: every attempt (including failed ones) is appended to attempts.jsonl before it is sent; caps are checked before each one.

Subcommands: check | smoke | work | supervise | status | analyze | report
"""
from __future__ import annotations

import argparse
import copy
import ctypes
import importlib
import inspect
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experience_pilot_v0 as p0  # noqa: E402  frozen pilot code (loop, checker access, statistics)
import experience_xfer_v1 as xv  # noqa: E402  frozen S1 code (Tr delivery, lesson compiler)

ROOT = p0.ROOT
NDATA = ROOT / "data/lab/aamr-night1"
NWORK = ROOT.parent / "aamr-night1-2026-11-12"
RUN = Path(os.environ.get("AAMR_NIGHT1_RUN", str(NWORK / "run")))
CONFIG_PATH = NDATA / "config.json"
OUT = Path(os.environ.get("AAMR_NIGHT1_OUT", str(NDATA)))       # results, report and freeze manifest (a scratch folder in dry runs)
FAKE = os.environ.get("AAMR_NIGHT1_FAKE") == "1"
SMOKE = False
PROTOCOL_PATH = NDATA / "PROTOCOL.md"

FUEL_SIG = ("fillFuelTank", "cannot fill gas above the tank capacity")
ORACLE = ('fillFuelTank: error "Cannot fill gas above the tank capacity." means that the current fuel level plus fuelAmount would '
          'exceed 50 gallons. fuelAmount is the amount to add, not the target level. It was resolved by first calling '
          "displayCarStatus(option='fuel') and then calling fillFuelTank with at most 50 minus the reported fuelLevel.")
PLACEBO = ('fillFuelTank: error "Cannot fill gas above the tank capacity." was also returned in earlier tasks. Nothing else was '
           'recorded about this error at the time, so this note carries no further information about the tool. Continue with the '
           "user's current request and use the functions listed above as you normally would, one step after another.")
STALE = ORACLE.replace("50", "40")          # the same lesson written for an older tank of 40 gallons (harm probe, arm TrS)
NOTE_CAP = 600
WRITER_WORDS = 60
WRITER_OCCURRENCES = 6
WRITER_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["note"], "properties": {"note": {"type": "string"}}}
SPLIT_SEED = 20261112
DOMAINS = {"VC": (50, "VehicleControlAPI"), "GFS": (0, "GorillaFileSystem"), "TRAVEL": (150, "TravelAPI")}
REPLAY_MAX = {"default": 4, FUEL_SIG: 6}
EXIT_DONE, EXIT_NEXT, EXIT_FATAL, EXIT_TRANSIENT = 0, 10, 2, 3
STAGES = ["preflight_q14", "a0_writer", "b0_writers", "b1_quality", "sA", "census", "d0_build", "sD", "sC", "preflight_q9", "sE", "final"]
DEPENDS = {"a0_writer": ["preflight_q14"], "b0_writers": ["preflight_q14"], "b1_quality": ["b0_writers"],
           "sA": ["preflight_q14"], "census": ["preflight_q14"], "d0_build": ["census"], "sD": ["d0_build"], "sC": ["preflight_q14"],
           "sE": ["preflight_q9"]}


class BudgetExhausted(RuntimeError):
    pass


class TransientFailure(RuntimeError):
    pass


class ProtocolError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- durable files

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fsync_append(path: Path, row) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def repair_tail(path: Path) -> bool:
    """A crash can leave a torn last line; cut the file back to its last newline so later appends stay parseable."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    data = path.read_bytes()
    if data.endswith(b"\n"):
        return False
    cut = data.rfind(b"\n") + 1
    with open(path, "r+b") as f:
        f.truncate(cut)
    return True


def read_rows(path: Path):
    if not path.exists():
        return []
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").split("\n")):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def log(msg: str) -> None:
    line = f"{now_iso()} {msg}"
    print(line, flush=True)
    try:
        with open(RUN / "progress.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def log_error(msg: str) -> None:
    log("ERROR " + msg)
    try:
        with open(RUN / "errors.log", "a", encoding="utf-8") as f:
            f.write(f"{now_iso()} {msg}\n")
    except OSError:
        pass


def load_config():
    return p0.read_json(CONFIG_PATH)


def config_id(cfg) -> str:
    return p0.sha({"config": cfg, "protocol_sha256": p0.file_sha(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else None})[:16]


# ----------------------------------------------------------------------------- Ollama gateway with cache, caps and bounded retry

def ledger_dirs(cfg, run):
    out = [run]
    for x in cfg.get("extra_ledger_dirs", []):
        d = NWORK / x
        if d.resolve() != Path(run).resolve():
            out.append(d)
    return out


class Gateway:
    def __init__(self, cfg, run: Path = None, transport=None, sleep=time.sleep):
        self.cfg, self.run = cfg, run or RUN
        self.attempts_path, self.responses_path = self.run / "attempts.jsonl", self.run / "responses.jsonl"
        for p in (self.attempts_path, self.responses_path):
            repair_tail(p)
        self.cache = {r["key"]: r for r in read_rows(self.responses_path)}
        self.by_bucket = Counter()
        for d in ledger_dirs(cfg, self.run):
            if d != self.run:
                repair_tail(d / "attempts.jsonl")
            for a in read_rows(d / "attempts.jsonl"):
                if a.get("provider") == "ollama":
                    self.by_bucket[a["bucket"] if d == self.run else "T"] += 1
        self.transport = transport or self._http
        self.sleep = sleep
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def total_local(self):
        return sum(self.by_bucket.values())

    def _http(self, path, body=None, timeout=None):
        req = urllib.request.Request(self.cfg["base_url"] + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=timeout or self.cfg["http_timeout_seconds"]) as r:
            return json.load(r)

    def check_budget(self, bucket):
        b = self.cfg["budgets"]
        if self.total_local >= b["total_local"]:
            raise BudgetExhausted("total_local")
        if self.by_bucket[bucket] >= b[bucket]:
            raise BudgetExhausted(bucket)

    def payload(self, model_id, messages, schema, seed, keep_alive="10m"):
        m = self.cfg["models"][model_id]
        return {"model": m["name"], "messages": messages, "stream": False, "format": schema if schema is not None else "json",
                "keep_alive": keep_alive, "options": dict(m["options"], seed=seed), **m.get("extra", {})}

    def ask(self, key, model_id, messages, schema, bucket, seed):
        payload = self.payload(model_id, messages, schema, seed)
        rs = p0.sha(payload)
        hit = self.cache.get(key)
        if hit is not None:
            if hit["request_sha256"] != rs:
                raise ProtocolError("stored response belongs to a different request: " + key)
            return hit
        waits = self.cfg["retry"]["backoff_seconds"]
        last = None
        for attempt in range(self.cfg["retry"]["max_attempts_per_call"]):
            self.check_budget(bucket)
            fsync_append(self.attempts_path, {"key": key, "attempt": attempt, "provider": "ollama", "model": payload["model"], "bucket": bucket,
                                              "request_sha256": rs, "at": now_iso(), "request": payload if attempt == 0 else None})
            self.by_bucket[bucket] += 1
            t0 = time.monotonic()
            try:
                resp = self.transport("/api/chat", payload)
                if resp.get("error") or resp.get("done") is not True:
                    raise TransientFailure("incomplete response: %s" % str(resp.get("error"))[:200])
                if resp.get("model") != payload["model"]:
                    raise ProtocolError("unexpected model in response: %r" % resp.get("model"))
                text = (resp.get("message") or {}).get("content")
                if not isinstance(text, str):
                    raise TransientFailure("response without content")
            except ProtocolError:
                raise
            except urllib.error.HTTPError as exc:
                if exc.code == 400:
                    raise ProtocolError(f"Ollama rejected the request for {key}: HTTP 400")
                last = repr(exc)[:300]
                log_error(f"local call {key} attempt {attempt} failed: {last}")
                if attempt < len(waits):
                    ensure_ollama(self)
                    self.sleep(waits[attempt])
                continue
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, TransientFailure, ValueError) as exc:
                last = repr(exc)[:300]
                log_error(f"local call {key} attempt {attempt} failed: {last}")
                if attempt < len(waits):
                    ensure_ollama(self)
                    self.sleep(waits[attempt])
                continue
            row = {"key": key, "request_sha256": rs, "model": payload["model"], "bucket": bucket, "text": text,
                   "done_reason": resp.get("done_reason"), "wall_seconds": time.monotonic() - t0,
                   "thinking_present": bool((resp.get("message") or {}).get("thinking")),
                   "usage": {k: resp.get(k) for k in ("prompt_eval_count", "eval_count", "total_duration", "load_duration",
                                                      "prompt_eval_duration", "eval_duration")}}
            fsync_append(self.responses_path, row)
            self.cache[key] = row
            return row
        raise TransientFailure(f"local call failed after retries: {key}: {last}")

    def release(self, model_id):
        try:
            self.transport("/api/generate", {"model": self.cfg["models"][model_id]["name"], "keep_alive": 0})
        except Exception as exc:  # release must never hide a result
            log_error("release failed: " + repr(exc))


class LocalClient:
    """The interface run_episode_x expects: ask(key, messages, seed, output_schema=...)."""

    def __init__(self, gw: Gateway, model_id: str, bucket: str):
        self.gw, self.model_id, self.bucket = gw, model_id, bucket

    def ask(self, key, messages, seed, output_schema=None):
        return self.gw.ask(key, self.model_id, messages, output_schema, self.bucket, seed)


def ensure_ollama(gw: Gateway):
    """If the local server does not answer, start the user's own Ollama app once and wait for it (bounded)."""
    try:
        gw.transport("/api/version", None)
        return True
    except Exception:
        pass
    exe = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama app.exe"
    if exe.exists() and gw.transport == gw._http:
        log_error("Ollama not answering; starting " + str(exe))
        try:
            subprocess.Popen([str(exe)], creationflags=getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)
        except OSError as exc:
            log_error("could not start Ollama: " + repr(exc))
            return False
        for _ in range(24):
            time.sleep(5)
            try:
                gw.transport("/api/version", None)
                return True
            except Exception:
                continue
    return False


# ----------------------------------------------------------------------------- DeepSeek Flash with reservation ledger

PRIVACY_PATTERNS = [r"[A-Za-z]:\\\\", r"[A-Za-z]:/(?:Users|Pamiec)", r"(?i)krapcys", r"(?i)pamiec llm", r"\bsk-[A-Za-z0-9]{16,}",
                    r"(?i)@gmail\.com", r"(?i)api[_-]?key"]


def privacy_violations(text: str):
    return [p for p in PRIVACY_PATTERNS if re.search(p, text)]


class Flash:
    def __init__(self, cfg, run: Path = None, key_loader=None, transport=None):
        self.cfg, self.f = cfg, cfg["flash"]
        self.run = run or RUN
        self.ledger_path, self.responses_path = self.run / "flash_ledger.jsonl", self.run / "flash_responses.jsonl"
        for p in (self.ledger_path, self.responses_path):
            repair_tail(p)
        self.cache = {r["key"]: r for r in read_rows(self.responses_path)}
        self.key_loader, self.transport = key_loader, transport
        self._key = None
        self.unavailable = None

    def ledger_rows(self):
        rows = []
        for d in ledger_dirs(self.cfg, self.run):
            rows += read_rows(d / "flash_ledger.jsonl")
        return rows

    def spent(self):
        rows = self.ledger_rows()
        res = [r for r in rows if r["event"] == "reserve"]
        use = [r for r in rows if r["event"] == "usage"]
        return {"reserved_calls": len(res), "reserved_usd": round(sum(r["usd"] for r in res), 6),
                "usage_upper_usd": round(sum(r["usd_upper"] for r in use), 6),
                "prompt_tokens": sum(r["prompt_tokens"] for r in use), "completion_tokens": sum(r["completion_tokens"] for r in use)}

    def _http(self, path, body=None):
        if path not in ("/models", "/chat/completions"):
            raise ValueError("unsupported operation")
        req = urllib.request.Request(self.f["url"] + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + self._key})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=120) as r:
            return json.load(r)

    def open(self):
        """Load the key (never printed) and check the advertised model. Any failure: Flash unavailable, no paid call."""
        if self.unavailable or self._key:
            return self.unavailable is None
        try:
            if self.key_loader is None:
                import metered_proxy
                self.key_loader = metered_proxy.load_key
            self._key = self.key_loader()
            if self.transport is None:
                self.transport = self._http
            models = self.transport("/models", None).get("data", [])
            match = [m for m in models if m.get("id") == self.f["model"]]
            if len(match) != 1:
                raise ProtocolError("provider does not list deepseek-flash")
            name = match[0].get("name")
            if name is not None and not re.fullmatch(r"DeepSeek-V4\.1-Flash(?:-\d+)?", name):
                raise ProtocolError("advertised name is not V4.1 Flash: %r" % name)
            self.identity = match[0]
            return True
        except BaseException as exc:
            if isinstance(exc, KeyboardInterrupt):
                raise
            self.unavailable = repr(exc)[:300]
            self._key = None
            log_error("Flash unavailable: " + self.unavailable)
            return False

    def ask(self, key, messages, max_tokens=None):
        max_tokens = max_tokens or self.f["max_tokens"]
        payload = {"model": self.f["model"], "messages": messages, "stream": False, "temperature": 0, "max_tokens": max_tokens,
                   "thinking": {"type": "disabled"}, "response_format": {"type": "json_object"}}
        rs = p0.sha(payload)
        hit = self.cache.get(key)
        if hit is not None:
            if hit["request_sha256"] != rs:
                raise ProtocolError("stored Flash response belongs to a different request: " + key)
            return hit
        body = json.dumps(messages, ensure_ascii=False)
        bad = privacy_violations(body)
        if bad:
            raise ProtocolError("privacy guard refused the payload: %s" % bad)
        size = len(body.encode())
        if size > self.f["max_input_bytes"]:
            raise ProtocolError("Flash request larger than the reserved bound")
        upper = (size * self.f["input_usd_per_million_upper"] + max_tokens * self.f["output_usd_per_million_upper"]) / 1e6
        if upper > self.f["reservation_usd"]:
            raise ProtocolError("Flash request cannot fit its reservation")
        if not self.open():
            raise BudgetExhausted("flash_unavailable")
        last = None
        for attempt in range(2):
            s = self.spent()
            if s["reserved_calls"] >= self.f["max_calls"] or s["reserved_usd"] + self.f["reservation_usd"] > self.f["cap_usd"] + 1e-12:
                raise BudgetExhausted("flash")
            fsync_append(self.ledger_path, {"event": "reserve", "key": key, "attempt": attempt, "model": self.f["model"],
                                            "usd": self.f["reservation_usd"], "at": now_iso()})
            t0 = time.monotonic()
            try:
                resp = self.transport("/chat/completions", payload)
            except Exception as exc:
                last = repr(exc)[:300]
                log_error(f"Flash call {key} attempt {attempt} failed: {last}")
                time.sleep(20)
                continue
            usage = resp.get("usage") or {}
            pt, ct = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if not all(isinstance(v, int) and v >= 0 for v in (pt, ct)):
                self.unavailable = "usage missing"
                raise BudgetExhausted("flash_usage_unknown")
            usd = (pt * self.f["input_usd_per_million_upper"] + ct * self.f["output_usd_per_million_upper"]) / 1e6
            fsync_append(self.ledger_path, {"event": "usage", "key": key, "attempt": attempt, "prompt_tokens": pt,
                                            "completion_tokens": ct, "usd_upper": usd})
            if usd > self.f["reservation_usd"]:
                self.unavailable = "usage exceeded the per-call reservation"
                raise BudgetExhausted("flash_reservation_exceeded")
            model = str(resp.get("model", ""))
            if not (model == "deepseek-flash" or re.fullmatch(r"deepseek-v4\.1-flash(?:-\d+)?", model.lower())):
                self.unavailable = "unexpected model " + model
                raise BudgetExhausted("flash_model")
            msg = (resp.get("choices") or [{}])[0].get("message") or {}
            if msg.get("reasoning_content"):
                self.unavailable = "thinking content returned"
                raise BudgetExhausted("flash_thinking")
            row = {"key": key, "request_sha256": rs, "text": msg.get("content") or "", "finish_reason": (resp.get("choices") or [{}])[0].get("finish_reason"),
                   "usage": {"prompt_tokens": pt, "completion_tokens": ct}, "usd_upper": usd, "wall_seconds": time.monotonic() - t0,
                   "returned_model": model}
            fsync_append(self.responses_path, row)
            self.cache[key] = row
            return row
        raise TransientFailure(f"Flash call failed twice: {key}: {last}")


# ----------------------------------------------------------------------------- BFCL with the travel docs; splits

class BfclN(xv.BfclX):
    def __init__(self, root: Path):
        super().__init__(root)
        data = self.root / "bfcl_eval/data"
        self.docs["TravelAPI"] = p0.read_jsonl(data / "multi_turn_func_doc" / "travel_booking.json")
        klass = getattr(importlib.import_module(self.backend.CLASS_FILE_PATH_MAPPING["TravelAPI"]), "TravelAPI")
        for name, f in inspect.getmembers(klass, predicate=inspect.isfunction):
            if not name.startswith("_"):
                self.signatures[name] = [p for p in inspect.signature(f).parameters if p != "self"]
        for t in self.tasks.values():
            if "TradingBot" in t["involved_classes"] and not 100 <= xv.task_number(t["id"]) <= 149:
                raise ProtocolError("TradingBot outside the reserve block")


def bfcl_from(cfg):
    return BfclN((ROOT / cfg["bfcl_root"]).resolve())


def domain_of(task_id):
    n = xv.task_number(task_id)
    for d, (lo, _) in DOMAINS.items():
        if lo <= n < lo + 50:
            return d
    raise ProtocolError("task outside the program's domains: " + task_id)


def split(domain, bfcl=None):
    lo = DOMAINS[domain][0]
    ids = [f"multi_turn_base_{i}" for i in range(lo, lo + 50)]
    random.Random(SPLIT_SEED).shuffle(ids)
    train, test = ids[:20], ids[20:]
    excluded = []
    if bfcl is not None:
        excluded = [t for t in test if any(not g for g in bfcl.gt[t])]
        test = [t for t in test if t not in excluded]
    return {"train": train, "test": test, "excluded_empty_gt": excluded}


# ----------------------------------------------------------------------------- notes with given text in the frozen Tr loop

_orig_note_text = xv.note_text


def _note_text(les):
    return les["text"] if les.get("text") is not None else _orig_note_text(les)


xv.note_text = _note_text            # run_episode_x looks the function up at call time; deterministic lessons keep their S1 text


def det_lessons_vc():
    path = ROOT / "data/lab/experience-xfer-v1/lessons.jsonl"
    rows = p0.read_jsonl(path)
    return rows, p0.file_sha(path)


def given(function, error_key, text, source):
    return {"function": function, "error_key": error_key, "text": text, "source": source}


def lesson_map(lessons):
    return {(l["function"], l["error_key"]): l for l in lessons}


# ----------------------------------------------------------------------------- writers (local Qwen and DeepSeek Flash; identical input)

MASKS = [(re.compile(r"\b\d{12,}\b"), "<long-number>"), (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<email>")]


def mask(text: str) -> str:
    for rx, rep in MASKS:
        text = rx.sub(rep, text)
    return text


def signatures(pool):
    """Every (function, error_key) seen in at least two training tasks, with its first message."""
    obs = xv.collect_observations(pool)
    out = []
    for (f, key), lst in sorted(obs.items()):
        tasks = {o["task"] for o in lst}
        if len(tasks) >= xv.MIN_TASKS:
            out.append({"function": f, "error_key": key, "tasks_seen": len(tasks),
                        "tasks_resolved": len({o["task"] for o in lst if o["resolved"]}), "example_message": lst[0]["msg"][:xv.MSG_CHARS]})
    return out


def occurrences(pool, sig, limit=WRITER_OCCURRENCES):
    rows, seen = [], set()
    for row in sorted(pool, key=lambda r: (r["order"], r["turn"])):
        if row["source_task"] in seen:
            continue
        for s in row["steps"]:
            if s["error"] and xv.fn(s["call"]) == sig["function"]:
                try:
                    _, kw = xv.parse_call(s["call"])
                except Exception:
                    continue
                if xv.error_key(s["result"], kw) == sig["error_key"]:
                    rows.append(row)
                    seen.add(row["source_task"])
                    break
        if len(rows) >= limit:
            break
    return rows


def class_of(bfcl, function):
    for cls, docs in bfcl.docs.items():
        if any(d["name"] == function for d in docs):
            return cls
    raise KeyError(function)


def writer_messages(bfcl, sig, occ):
    cls = class_of(bfcl, sig["function"])
    lines = ["You write one short note for an AI agent that operates the tools listed below.",
             "The note will be shown to the agent in a later task, right after a tool call returns the error below.",
             "Use only the information given here: the tool descriptions and the agent's earlier attempts.", "",
             "TOOLS", "\n\n".join(p0.render_function(d) for d in bfcl.docs[cls]), "",
             "ERROR", f"Tool: {sig['function']}", f"Error message: {sig['example_message']}", "",
             "EARLIER ATTEMPTS IN WHICH THIS ERROR OCCURRED (outcome = whether that request was completed correctly, checked afterwards)"]
    for i, row in enumerate(occ, 1):
        lines.append(f"Attempt {i}. Request: {p0.truncate(row['request'], 300)}")
        for s in row["steps"][:12]:
            lines.append(f"  {s['call']} -> {p0.truncate(s['result'], 160)}")
        lines.append(f"  Outcome: {row['label']}")
    lines += ["", f"Write a note of at most {WRITER_WORDS} words: what the error means and what the agent should do when it appears.",
              "Mention only tools from the list above. Do not invent values that the information above does not support.",
              'Return JSON {"note": "<text>"}.']
    return [{"role": "user", "content": mask("\n".join(lines))}]


def writer_key(source, domain, sig):
    return f"w:{source}:{domain}:{sig['function']}|{sig['error_key']}"


def parse_note(text, done_reason, function):
    if done_reason == "length":
        return None, "length"
    text = re.sub(r"<\|[a-z_]{2,30}\|>", "", text or "")        # provider special tokens (seen once from Flash in the smoke test)
    try:
        note = json.loads(text)["note"]
    except (ValueError, TypeError, KeyError):
        return None, "not json"
    if not isinstance(note, str) or not note.strip():
        return None, "empty"
    note = re.sub(r"\s+", " ", note).strip()
    if not note.startswith(function):
        note = f"{function}: {note}"
    return p0.truncate(note, NOTE_CAP, "…"), None


IDENT = re.compile(r"\b[a-z][a-z0-9]*(?:[A-Z][A-Za-z0-9]*)+\b|\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
CALLNAME = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def allowed_identifiers(bfcl, cls, extra_text=""):
    text = json.dumps(bfcl.docs[cls]) + "\n" + extra_text
    return set(IDENT.findall(text)) | {d["name"] for d in bfcl.docs[cls]}


def test_only_tokens(bfcl, domain, extra_known=""):
    sp = split(domain, bfcl)

    def toks(task_ids):
        nums, strs = set(), set()
        for t in task_ids:
            task = bfcl.tasks[t]
            blob = json.dumps(task["question"]) + json.dumps(task["initial_config"]) + json.dumps(bfcl.gt[t])
            nums |= set(n for n in re.findall(r"\d+(?:\.\d+)?", blob) if len(n) >= 2)
            for pair in re.findall(r"'([^']{3,60})'|\"([^\"]{3,60})\"", blob):
                strs |= {x for x in pair if x}
            strs |= set(re.findall(r"\b[A-Z][a-z]{3,}\b", json.dumps(task["question"])))
        return nums, strs
    tn, ts = toks(sp["test"])
    kn, ks = toks(sp["train"])
    known = json.dumps(bfcl.docs) + extra_known
    nums = {n for n in tn - kn if not re.search(r"(?<![0-9.])" + re.escape(n) + r"(?![0-9])", known)}
    strs = {s for s in ts - ks if s not in known}
    return nums, strs


def check_note(text, allowed, fnames, leak):
    nums, strs = leak
    unknown = sorted({w for w in IDENT.findall(text) if w not in allowed})
    bad_calls = sorted({c for c in CALLNAME.findall(text) if c not in fnames})
    leaks = sorted([n for n in nums if re.search(r"(?<![0-9.])" + re.escape(n) + r"(?![0-9])", text)] +
                   [s for s in strs if s in text])
    return {"chars": len(text), "unknown_identifiers": unknown, "unknown_calls": bad_calls, "leaked_tokens": leaks[:10],
            "ok": not unknown and not bad_calls and not leaks and len(text) <= NOTE_CAP}


def write_lessons(ctx, source, domain, pool, sigs, bucket):
    """One writer call per signature. Returns rows with text or failure reason."""
    bfcl = ctx.bfcl
    train = set(split(domain)["train"])
    out = []
    for sig in sigs:
        occ = occurrences(pool, sig)
        if {r["source_task"] for r in occ} - train:
            raise ProtocolError("a writer input would contain a non-training task")
        msgs = writer_messages(bfcl, sig, occ)
        key = writer_key(source, domain, sig)
        row = {"function": sig["function"], "error_key": sig["error_key"], "source": source, "domain": domain,
               "occurrences": [f"{r['source_task']}:t{r['turn']}" for r in occ], "request_sha256": p0.sha(msgs),
               "input_chars": len(msgs[0]["content"])}
        if source == "Q":
            b = "A" if (domain == "VC" and (sig["function"], sig["error_key"]) == FUEL_SIG) else bucket
            r = ctx.gw.ask(key, "q14", msgs, WRITER_SCHEMA, b, 7)
            text, err = parse_note(r["text"], r.get("done_reason"), sig["function"])
            row.update({"raw": r["text"], "usage": r.get("usage")})
        else:
            try:
                r = ctx.flash.ask(key, msgs)
            except (ProtocolError, TransientFailure) as exc:          # a Flash problem never stops the local program
                ctx.flash.unavailable = ctx.flash.unavailable or repr(exc)[:300]
                log_error(f"Flash writer {key}: {exc!r}")
                row.update({"text": None, "parse_error": "flash refused or failed: " + repr(exc)[:200]})
                out.append(row)
                continue
            text, err = parse_note(r["text"], "length" if r.get("finish_reason") == "length" else None, sig["function"])
            row.update({"raw": r["text"], "usage": r.get("usage"), "usd_upper": r.get("usd_upper")})
        row.update({"text": text, "parse_error": err})
        out.append(row)
    return out


def checked(bfcl, domain, rows, writer_inputs=""):
    cls_cache = {}
    leak = test_only_tokens(bfcl, domain, writer_inputs)
    for row in rows:
        cls = cls_cache.setdefault(row["function"], class_of(bfcl, row["function"]))
        if row.get("text") is None:
            row["check"] = {"ok": False, "reason": row.get("parse_error")}
            continue
        allowed = allowed_identifiers(bfcl, cls, writer_inputs)
        row["check"] = check_note(row["text"], allowed, {d["name"] for d in bfcl.docs[cls]}, leak)
    return rows


# ----------------------------------------------------------------------------- B1: lesson unit test at real training error states

def pilot_training_records():
    recs, evs = {}, {}
    for stage in ("e1a", "e1b"):
        run = p0.latest_completed(stage)
        for r in p0.read_jsonl(run / "episodes.jsonl"):
            recs[r["task"]] = r
        for e in p0.read_jsonl(run / "evaluations.jsonl"):
            evs[e["task"]] = e
    return recs, evs


def step_results(step):
    if step.get("invalid_output"):
        return [{"error": "invalid output: response is not valid JSON for the required schema"}]
    if not step.get("calls"):
        return None
    return [{"call": c["call"] or (c["raw"].get("name") if isinstance(c["raw"], dict) else None),
             "result": p0.truncate(c["result"], p0.RESULT_CHARS)} for c in step["calls"]]


def rebuild_history(bfcl, task, rec, t_star, s_star):
    """Messages of the pilot loop (arm N) just after the assistant message of step (t_star, s_star)."""
    history = [{"role": "system", "content": p0.system_prompt(bfcl, task)}]
    for turn in rec["turns"][:t_star + 1]:
        history.append({"role": "user", "content": turn["request"]})
        for si, step in enumerate(turn["steps"]):
            if "key" not in step:
                break
            history.append({"role": "assistant", "content": step["text"]})
            res = step_results(step)
            if turn["index"] == t_star and si == s_star:
                return history, res
            if res is None:
                break
            history.append({"role": "user", "content": "RESULTS: " + json.dumps(res, ensure_ascii=False)})
    raise ProtocolError("fork point not found")


def replay_points(recs, train, sigs):
    pts = []
    for sig in sigs:
        sk = (sig["function"], sig["error_key"])
        limit = REPLAY_MAX.get(sk, REPLAY_MAX["default"])
        n = 0
        for t in train:
            rec = recs[t]
            found = None
            for turn in rec["turns"]:
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
                pts.append({"task": t, "turn": found[0], "step": found[1], "function": sig["function"], "error_key": sig["error_key"]})
                n += 1
            if n >= limit:
                break
    return pts


def run_fork(bfcl, task, rec, pt, note, client, names, key, ctx_limit):
    t, s = pt["turn"], pt["step"]
    history, results = rebuild_history(bfcl, task, rec, t, s)
    docs_by_name = {d["name"]: d for d in bfcl.functions(task)}
    schema = p0.output_schema(bfcl, task)
    live = names.new("fork", key)
    prefix_steps = []
    for turn in rec["turns"][:t + 1]:
        for si, st in enumerate(turn["steps"]):
            if turn["index"] == t and si > s:
                break
            prefix_steps.append((turn["index"], [c["call"] for c in st.get("calls", []) if c["valid"]]))
    flat = [c for _, cs in prefix_steps for c in cs]
    if flat:
        bfcl.execute(flat, task, live)
    content = "RESULTS: " + json.dumps(results, ensure_ascii=False)
    if note:
        content += "\n\n" + xv.NOTE_PREFIX + note
    history.append({"role": "user", "content": content})
    fork_steps, ended = [], False
    for si in range(s + 1, p0.MAX_STEPS):
        if p0.chars_tokens(history) >= ctx_limit:
            break
        r = client.ask(f"{key}:s{si}", history, 7, output_schema=schema)
        history.append({"role": "assistant", "content": r["text"]})
        raw = p0.parse_output(r["text"], r.get("done_reason"))
        step = {"text": r["text"], "calls": []}
        fork_steps.append(step)
        if raw is None:
            res = [{"error": "invalid output: response is not valid JSON for the required schema"}]
        elif not raw:
            ended = True
            break
        else:
            res = []
            for call in raw:
                cs, err = p0.validate_call(call, docs_by_name)
                e = {"raw": call, "call": cs, "valid": cs is not None}
                if cs is None:
                    e["result"] = json.dumps({"error": err})
                else:
                    o, _ = bfcl.execute([cs], task, live)
                    e["result"], e["error"] = o[0], p0.is_error_result(o[0])
                step["calls"].append(e)
                res.append({"call": cs or (call.get("name") if isinstance(call, dict) else None), "result": p0.truncate(e["result"], p0.RESULT_CHARS)})
        history.append({"role": "user", "content": "RESULTS: " + json.dumps(res, ensure_ascii=False)})
    resolved = any(c["valid"] and not c.get("error") and xv.fn(c["call"]) == pt["function"] for st in fork_steps for c in st["calls"])
    model_turns = [[] for _ in range(t + 1)]
    for ti, cs in prefix_steps:
        if cs:
            model_turns[ti].append(cs)
    for st in fork_steps:
        cs = [c["call"] for c in st["calls"] if c["valid"]]
        if cs:
            model_turns[t].append(cs)
    chk = bfcl.check(model_turns, bfcl.gt[task["id"]][:t + 1], task, names.new("forkchk", key))
    return {"resolved": resolved, "turn_passed": bool(chk["valid"]) and ended, "ended": ended, "live_steps": len(fork_steps),
            "fork_steps": fork_steps}


# ----------------------------------------------------------------------------- sessions

class FakeOllama:
    """Dry-run stand-in for Ollama (AAMR_NIGHT1_FAKE=1): exercises every stage with the real BFCL environment and no model."""

    def __init__(self, cfg):
        self.cfg, self.loaded = cfg, None

    def __call__(self, path, body=None, timeout=None):
        if path == "/api/version":
            return {"version": "fake"}
        if path == "/api/tags":
            return {"models": [{"name": m["name"], "digest": m["digest"]} for m in self.cfg["models"].values()]}
        if path == "/api/ps":
            return {"models": [{"name": self.loaded, "size": 1, "size_vram": 1}] if self.loaded else []}
        if path == "/api/generate":
            self.loaded = None
            return {"done": True}
        self.loaded = body["model"]
        last = body["messages"][-1]["content"]
        props = (body.get("format") or {}).get("properties", {}) if isinstance(body.get("format"), dict) else {}
        if "note" in props:
            text = json.dumps({"note": "first call displayCarStatus with option fuel, then retry with a smaller amount."})
        elif 'mode equal to \"on\"' in last:
            text = '{"calls": [{"name": "setHeadlights", "arguments": {"mode": "on"}}]}'
        elif 'mode equal to \"off\"' in last:
            text = '{"calls": [{"name": "setHeadlights", "arguments": {"mode": "off"}}]}'
        elif last.startswith("RESULTS") or "empty list" in last:
            text = '{"calls": []}'
        else:
            names = props["calls"]["items"]["properties"]["name"]["enum"]
            pick = "fillFuelTank" if "fillFuelTank" in names else names[len(last) % len(names)]
            args = {"fuelAmount": 60.0} if pick == "fillFuelTank" else {}
            text = json.dumps({"calls": [{"name": pick, "arguments": args}]})
        return {"model": body["model"], "done": True, "done_reason": "stop", "message": {"content": text},
                "prompt_eval_count": len(json.dumps(body["messages"])) // 3, "eval_count": 20}


class FakeFlashTransport:
    def __call__(self, path, body=None):
        if path == "/models":
            return {"data": [{"id": "deepseek-flash"}]}
        return {"model": "deepseek-flash", "choices": [{"message": {"content": json.dumps({"note": "read the state first, then retry."})},
                                                        "finish_reason": "stop"}], "usage": {"prompt_tokens": 3000, "completion_tokens": 40}}


class Ctx:
    def __init__(self, cfg, gw=None, flash=None, bfcl=None):
        self.cfg = cfg
        fake = os.environ.get("AAMR_NIGHT1_FAKE") == "1"
        self.gw = gw or Gateway(cfg, transport=FakeOllama(cfg) if fake else None, sleep=(lambda s: None) if fake else time.sleep)
        self.flash = flash or (Flash(cfg, key_loader=lambda: "fake", transport=FakeFlashTransport()) if fake else Flash(cfg))
        self.bfcl = bfcl or bfcl_from(cfg)
        self.names = p0.Names(f"n1_{os.getpid()}_{int(time.time())}")
        self.state = p0.read_json(RUN / "state.json") if (RUN / "state.json").exists() else {"stages": {}}


def heartbeat(ctx, stage, extra=None):
    hb = {"at": now_iso(), "pid": os.getpid(), "stage": stage, "local_calls_total": ctx.gw.total_local,
          "by_bucket": dict(ctx.gw.by_bucket), "flash": ctx.flash.spent(), "config_id": config_id(ctx.cfg)}
    if extra:
        hb.update(extra)
    atomic_json(RUN / "heartbeat.json", hb)


def session_plan(tasks, arms, seed_base):
    plan = []
    for i, t in enumerate(tasks):
        order = list(arms)
        random.Random(seed_base + i).shuffle(order)
        plan.extend((t, a) for a in order)
    return plan


def run_session(ctx, name, model_id, tasks, arms, seed_base):
    """arms: {arm: {"bucket": b, "tr": map or None, "block": provider or None, "lessons_by_domain": {...} or None}}."""
    path = RUN / "sessions" / f"{name}.jsonl"
    repair_tail(path)
    done = {(r["task"], r["arm"]) for r in read_rows(path)}
    plan = session_plan(tasks, list(arms), seed_base)
    exhausted, n_new = set(), 0
    cfg_m = {"options": ctx.cfg["models"][model_id]["options"]}
    for i, (t, a) in enumerate(plan):
        if (t, a) in done or arms[a]["bucket"] in exhausted:
            continue
        spec = arms[a]
        tr = spec.get("tr")
        if spec.get("tr_by_domain") is not None:
            tr = spec["tr_by_domain"].get(domain_of(t))
        block = spec.get("block")
        if spec.get("block_by_domain") is not None:
            block = spec["block_by_domain"].get(domain_of(t))
        client = LocalClient(ctx.gw, model_id, spec["bucket"])
        try:
            rec = xv.run_episode_x(ctx.bfcl, ctx.bfcl.tasks[t], client, ctx.names, stage=name, arm=a, key=f"{name}:{a}:{t}",
                                   ctx_limit=p0.ctx_limit(cfg_m), block=block, tr_lessons=tr or None)
        except BudgetExhausted as exc:
            if str(exc) == "total_local":
                raise
            exhausted.add(spec["bucket"])
            log_error(f"{name}: budget {exc} exhausted at episode {t} {a}; this bucket stops in this session")
            continue
        ev = p0.evaluate_episode(ctx.bfcl, rec, ctx.names)
        fsync_append(path, {"task": t, "arm": a, "bucket": spec["bucket"], "model": model_id, "episode": rec, "evaluation": ev})
        n_new += 1
        log(f"[{name}] {i + 1}/{len(plan)} {t} {a} solved={ev['solved']} calls={ev['model_calls']} total_local={ctx.gw.total_local}")
        heartbeat(ctx, name, {"session_progress": f"{i + 1}/{len(plan)}"})
    rows = read_rows(path)
    complete = {(r["task"], r["arm"]) for r in rows}
    missing = [(t, a) for t, a in plan if (t, a) not in complete]
    return {"episodes": len(rows), "new": n_new, "missing": len(missing), "exhausted_buckets": sorted(exhausted),
            "status": "done" if not missing else "partial"}


def session_rows(name):
    return read_rows(RUN / "sessions" / f"{name}.jsonl")


# ----------------------------------------------------------------------------- stages

def transport_check(ctx, model_id, bucket):
    bfcl = ctx.bfcl
    task = bfcl.tasks["multi_turn_base_50"]
    schema, long_system = p0.output_schema(bfcl, task), p0.system_prompt(bfcl, task)
    short = "Return JSON that matches the schema."
    probes = [("short-1", [{"role": "system", "content": short}, {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"on\"."}],
               [{"name": "setHeadlights", "arguments": {"mode": "on"}}]),
              ("long-1", [{"role": "system", "content": long_system}, {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"off\". Do nothing else."}],
               [{"name": "setHeadlights", "arguments": {"mode": "off"}}]),
              ("short-2", [{"role": "system", "content": short}, {"role": "user", "content": "Return an empty list of calls."}], [])]
    rows = []
    for k, msgs, expected in probes:
        r = ctx.gw.ask(f"pre:{model_id}:{k}", model_id, msgs, schema, bucket, 7)
        rows.append({"probe": k, "ok": p0.parse_output(r["text"], r.get("done_reason")) == expected, "text": r["text"][:300],
                     "thinking_present": r.get("thinking_present")})
    try:
        ps = ctx.gw.transport("/api/ps", None).get("models", [])
    except Exception as exc:
        ps = [{"error": repr(exc)}]
    me = [m for m in ps if m.get("name") == ctx.cfg["models"][model_id]["name"]]
    gpu_full = bool(me) and me[0].get("size_vram") == me[0].get("size")
    tags = ctx.gw.transport("/api/tags", None).get("models", [])
    digest_ok = any(m.get("name") == ctx.cfg["models"][model_id]["name"] and m.get("digest") == ctx.cfg["models"][model_id]["digest"] for m in tags)
    version = ctx.gw.transport("/api/version", None)
    ok = all(r["ok"] for r in rows) and gpu_full and digest_ok and not any(r["thinking_present"] for r in rows)
    return {"status": "done" if ok else "failed", "probes": rows, "gpu_full": gpu_full, "digest_ok": digest_ok, "ollama": version,
            "api_ps": me[:1], "reason": None if ok else "transport check failed"}


def preflight_bucket(default):
    return "T" if SMOKE else default


def stage_preflight_q14(ctx):
    for m in ctx.gw.transport("/api/ps", None).get("models", []):
        if m.get("name") not in [x["name"] for x in ctx.cfg["models"].values()]:
            raise TransientFailure("a foreign model is loaded on the GPU: " + str(m.get("name")))
        if m.get("name") != ctx.cfg["models"]["q14"]["name"]:
            ctx.gw.transport("/api/generate", {"model": m["name"], "keep_alive": 0})
    return transport_check(ctx, "q14", preflight_bucket("A"))


def stage_preflight_q9(ctx):
    ctx.gw.release("q14")
    time.sleep(0 if os.environ.get("AAMR_NIGHT1_FAKE") == "1" else 5)
    return transport_check(ctx, "q9", preflight_bucket("E"))


def vc_pool():
    return p0.read_jsonl(p0.DATA / "pools" / "A.jsonl")


def stage_a0_writer(ctx):
    pool = vc_pool()
    sig = next(s for s in signatures(pool) if (s["function"], s["error_key"]) == FUEL_SIG)
    rows = checked(ctx.bfcl, "VC", write_lessons(ctx, "Q", "VC", pool, [sig], "A"), writer_inputs=writer_messages(ctx.bfcl, sig, occurrences(pool, sig))[0]["content"])
    row = rows[0]
    valid = row["text"] is not None and row["check"]["ok"]
    atomic_json(RUN / "artifacts" / "trw_lesson.json", row)
    return {"status": "done", "trw_valid": valid, "chars": len(row["text"] or ""), "check": row["check"]}


def stage_b0_writers(ctx):
    pool = vc_pool()
    sigs = signatures(pool)
    out = {"signatures": [f"{s['function']}|{s['error_key']}" for s in sigs]}
    for source in ("Q", "F"):
        if source == "F" and not ctx.flash.open():
            out["F"] = {"available": False, "reason": ctx.flash.unavailable}
            atomic_json(RUN / "artifacts" / "lessons_VC_F.json", {"available": False, "reason": ctx.flash.unavailable, "rows": []})
            continue
        try:
            rows = write_lessons(ctx, source, "VC", pool, sigs, "B")
        except BudgetExhausted as exc:
            out[source] = {"available": False, "reason": "budget " + str(exc)}
            atomic_json(RUN / "artifacts" / f"lessons_VC_{source}.json", {"available": False, "reason": str(exc), "rows": []})
            continue
        inputs = "\n".join(writer_messages(ctx.bfcl, s, occurrences(pool, s))[0]["content"] for s in sigs)
        rows = checked(ctx.bfcl, "VC", rows, inputs)
        atomic_json(RUN / "artifacts" / f"lessons_VC_{source}.json", {"available": True, "rows": rows})
        out[source] = {"available": True, "valid": sum(r["check"]["ok"] for r in rows), "of": len(rows)}
    return {"status": "done", **out}


def valid_lessons(path):
    if not path.exists():
        return []
    d = p0.read_json(path)
    return [given(r["function"], r["error_key"], r["text"], r["source"]) for r in d.get("rows", []) if r.get("check", {}).get("ok")]


def stage_b1_quality(ctx):
    """Unit test of each lesson source at real training error states (pilot arm N, training tasks only)."""
    recs, _ = pilot_training_records()
    pool = vc_pool()
    sigs = signatures(pool)
    train = p0.read_json(p0.DATA / "split.json")["train"]
    pts = replay_points(recs, train, sigs)
    det = {(l["function"], l["error_key"]): xv.note_text(l) for l in det_lessons_vc()[0]}
    srcmaps = {"none": {}, "D": det, "O": {FUEL_SIG: ORACLE}}
    for s in ("Q", "F"):
        srcmaps[s] = {(l["function"], l["error_key"]): l["text"] for l in valid_lessons(RUN / "artifacts" / f"lessons_VC_{s}.json")}
    path = RUN / "sessions" / "b1.jsonl"
    repair_tail(path)
    done = {(r["source"], r["task"], r["function"], r["error_key"]) for r in read_rows(path)}
    for pt in pts:
        sk = (pt["function"], pt["error_key"])
        for source, m in srcmaps.items():
            if source != "none" and sk not in m:
                continue
            ident = (source, pt["task"], pt["function"], pt["error_key"])
            if ident in done:
                continue
            key = f"b1:{source}:{pt['task']}:{pt['function']}:{pt['turn']}:{pt['step']}"
            res = run_fork(ctx.bfcl, ctx.bfcl.tasks[pt["task"]], recs[pt["task"]], pt, m.get(sk), LocalClient(ctx.gw, "q14", "B"),
                           ctx.names, key, p0.ctx_limit({"options": ctx.cfg["models"]["q14"]["options"]}))
            fsync_append(path, {"source": source, **pt, **res})
            log(f"[b1] {source} {pt['task']} {pt['function']} resolved={res['resolved']} turn_passed={res['turn_passed']}")
            heartbeat(ctx, "b1_quality")
    rows = read_rows(path)
    summary, admitted = {}, {}
    for source in srcmaps:
        mine = [r for r in rows if r["source"] == source]
        summary[source] = {"forks": len(mine), "resolved": sum(r["resolved"] for r in mine), "turn_passed": sum(r["turn_passed"] for r in mine)}
    for s in ("Q", "F"):
        d = p0.read_json(RUN / "artifacts" / f"lessons_VC_{s}.json") if (RUN / "artifacts" / f"lessons_VC_{s}.json").exists() else {"rows": []}
        rows_s = d.get("rows", [])
        n_ok = sum(1 for r in rows_s if r.get("check", {}).get("ok"))
        leaks = sum(1 for r in rows_s if r.get("check", {}).get("leaked_tokens"))
        mine = {(r["task"], r["function"], r["error_key"]): r for r in rows if r["source"] == s}
        base = {(r["task"], r["function"], r["error_key"]): r for r in rows if r["source"] == "none"}
        common = [k for k in mine if k in base]
        res_s, res_n = sum(mine[k]["resolved"] for k in common), sum(base[k]["resolved"] for k in common)
        g = {"available": bool(d.get("available")), "valid": n_ok, "of": len(sigs), "leaks": leaks,
             "coverage_ok": n_ok >= math.ceil(0.6 * len(sigs)), "leak_ok": leaks == 0,
             "replay_resolved": res_s, "replay_resolved_none": res_n, "replay_ok": res_s >= res_n - 2}
        g["admitted"] = bool(g["available"] and g["coverage_ok"] and g["leak_ok"] and g["replay_ok"])
        admitted[s] = g
    atomic_json(RUN / "artifacts" / "b1_gate.json", {"summary": summary, "gate": admitted})
    return {"status": "done", "summary": summary, "gate": admitted}


def vc_arms_14(ctx):
    det, _ = det_lessons_vc()
    base = list(det)
    arms = {"N": {"bucket": "A"}, "N'": {"bucket": "A"}, "Tr": {"bucket": "A", "tr": lesson_map(base)},
            "TrO": {"bucket": "A", "tr": lesson_map(base + [given(*FUEL_SIG, ORACLE, "oracle")])},
            "TrP": {"bucket": "A", "tr": lesson_map(base + [given(*FUEL_SIG, PLACEBO, "placebo")])},
            "TrS": {"bucket": "H", "tr": lesson_map(base + [given(*FUEL_SIG, STALE, "stale")])}}
    trw = RUN / "artifacts" / "trw_lesson.json"
    if trw.exists():
        row = p0.read_json(trw)
        if row.get("text") and row.get("check", {}).get("ok"):
            arms["TrW"] = {"bucket": "A", "tr": lesson_map(base + [given(*FUEL_SIG, row["text"], "Q")])}
    gate = p0.read_json(RUN / "artifacts" / "b1_gate.json")["gate"] if (RUN / "artifacts" / "b1_gate.json").exists() else {}
    for s in ("Q", "F"):
        if gate.get(s, {}).get("admitted"):
            arms["Tr" + s] = {"bucket": "B", "tr": lesson_map(valid_lessons(RUN / "artifacts" / f"lessons_VC_{s}.json"))}
    return arms


def stage_sA(ctx):
    arms = vc_arms_14(ctx)
    test = p0.read_json(p0.DATA / "split.json")["test"]
    out = run_session(ctx, "sA", "q14", test, arms, 20261113)
    out["arms"] = sorted(arms)
    return out


def stage_sC(ctx):
    arms = {k: v for k, v in vc_arms_14(ctx).items() if k in ("N", "TrP", "TrO")}
    for v in arms.values():
        v["bucket"] = "C"
    train = p0.read_json(p0.DATA / "split.json")["train"]
    out = run_session(ctx, "sC", "q14", train, arms, 20261114)
    out["arms"] = sorted(arms)
    return out


def stage_census(ctx):
    tasks = split("GFS")["train"] + split("TRAVEL")["train"]
    return run_session(ctx, "census", "q14", tasks, {"N": {"bucket": "D"}}, 20261115)


def census_pool(domain):
    rows = []
    sp = split(domain)
    order = {t: i for i, t in enumerate(sp["train"])}
    for r in session_rows("census"):
        if domain_of(r["task"]) == domain:
            rows += p0.pool_rows_from_episode(r["episode"], r["evaluation"], order[r["task"]])
    return rows


def stage_d0_build(ctx):
    out = {}
    mk = p0.load_kernel()
    for domain in ("GFS", "TRAVEL"):
        pool = census_pool(domain)
        lessons, rejected = xv.compile_lessons(pool)
        sigs = signatures(pool)
        d = {"pool_rows": len(pool), "deterministic_lessons": lessons, "open_problems": xv.open_problems(rejected), "signatures": sigs}
        inputs = "\n".join(writer_messages(ctx.bfcl, s, occurrences(pool, s))[0]["content"] for s in sigs)
        for source in ("Q", "F"):
            if source == "F" and not ctx.flash.open():
                d[source] = {"available": False, "reason": ctx.flash.unavailable, "rows": []}
                continue
            try:
                rows = checked(ctx.bfcl, domain, write_lessons(ctx, source, domain, pool, sigs, "D"), inputs)
                d[source] = {"available": True, "rows": rows}
            except BudgetExhausted as exc:
                d[source] = {"available": False, "reason": "budget " + str(exc), "rows": []}
        a_plus = [r for r in pool if r["label"] == "PASSED"]
        plan = {}
        if a_plus:
            idx = p0.build_index(mk, a_plus)
            for t in split(domain, ctx.bfcl)["test"]:
                for ti, q in enumerate(ctx.bfcl.tasks[t]["question"]):
                    rows_r, _ = p0.retrieve(mk, *idx, q[0]["content"], *p0.UNGATED)
                    plan[f"{t}:{ti}"] = [p0.pool_row_id(r) for r in rows_r]
        d["a_plus"] = a_plus
        d["rplus_plan"] = plan
        atomic_json(RUN / "artifacts" / f"memory_{domain}.json", d)
        out[domain] = {"pool_rows": len(pool), "lessons": len(lessons), "signatures": len(sigs), "a_plus": len(a_plus),
                       "Q_valid": sum(r["check"]["ok"] for r in d["Q"]["rows"]) if d["Q"].get("rows") else 0,
                       "F_valid": sum(r["check"]["ok"] for r in d["F"]["rows"]) if d["F"].get("rows") else 0}
    return {"status": "done", **out}


def rplus_provider(mem):
    rows = {p0.pool_row_id(r): r for r in mem["a_plus"]}
    meta = {"pool": "census A+", "pool_sha256": p0.sha(mem["a_plus"])}

    def block(task_id, ti, request):
        ids = mem["rplus_plan"].get(f"{task_id}:{ti}", [])
        return p0.render_block([rows[i] for i in ids]), list(ids), meta
    return block


def calls_per_episode(rows):
    return sum(r["evaluation"]["model_calls"] for r in rows) / max(1, len(rows))


def stage_sD(ctx):
    mem = {d: p0.read_json(RUN / "artifacts" / f"memory_{d}.json") for d in ("GFS", "TRAVEL")}
    gate = p0.read_json(RUN / "artifacts" / "b1_gate.json")["gate"] if (RUN / "artifacts" / "b1_gate.json").exists() else {}
    tasks = split("GFS", ctx.bfcl)["test"] + split("TRAVEL", ctx.bfcl)["test"]
    det = {d: lesson_map(mem[d]["deterministic_lessons"]) for d in mem}
    writer = {s: {d: lesson_map([given(r["function"], r["error_key"], r["text"], s) for r in mem[d][s].get("rows", []) if r.get("check", {}).get("ok")])
                  for d in mem} for s in ("Q", "F")}
    candidates = [("N", {"bucket": "D"}), ("TrD", {"bucket": "D", "tr_by_domain": det}), ("N'", {"bucket": "D"})]
    for s in ("F", "Q"):
        ok_domains = sum(1 for d in mem if len(writer[s][d]) >= math.ceil(0.6 * max(1, len(mem[d]["signatures"]))))
        if gate.get(s, {}).get("admitted") and ok_domains == 2:
            candidates.append(("Tr" + s, {"bucket": "D", "tr_by_domain": writer[s]}))
    if all(mem[d]["a_plus"] for d in mem):
        candidates.append(("R+", {"bucket": "D", "block_by_domain": {d: rplus_provider(mem[d]) for d in mem}}))
    cens = session_rows("census")
    per_dom = {d: calls_per_episode([r for r in cens if domain_of(r["task"]) == d]) for d in mem}
    per_ep = sum(per_dom[domain_of(t)] for t in tasks) / len(tasks)
    remaining = ctx.cfg["budgets"]["D"] - ctx.gw.by_bucket["D"]
    already = {r["arm"] for r in session_rows("sD")}
    arms, projected, dropped = {}, 0.0, []
    for a, spec in candidates:
        cost = per_ep * len(tasks) * 1.15
        if a in already or projected + cost <= remaining:
            arms[a] = spec
            projected += cost
        else:
            dropped.append(a)
    atomic_json(RUN / "artifacts" / "sD_plan.json", {"arms": list(arms), "dropped_for_budget": dropped, "per_episode": per_ep,
                                                      "remaining": remaining, "projected": projected, "tasks": tasks})
    out = run_session(ctx, "sD", "q14", tasks, arms, 20261116)
    out.update({"arms": list(arms), "dropped_for_budget": dropped})
    return out


def stage_sE(ctx):
    det, _ = det_lessons_vc()
    arms = {"N": {"bucket": "E"}, "TrO": {"bucket": "E", "tr": lesson_map(det + [given(*FUEL_SIG, ORACLE, "oracle")])},
            "TrP": {"bucket": "E", "tr": lesson_map(det + [given(*FUEL_SIG, PLACEBO, "placebo")])},
            "Tr": {"bucket": "E", "tr": lesson_map(det)}, "N'": {"bucket": "E"}}
    test = p0.read_json(p0.DATA / "split.json")["test"]
    out = run_session(ctx, "sE", "q9", test, arms, 20261117)
    ctx.gw.release("q9")
    out["arms"] = sorted(arms)
    return out


def stage_final(ctx):
    ctx.gw.release("q14")
    ctx.gw.release("q9")
    import aamr_night1_analysis as an
    freeze = freeze_raw()
    OUT.mkdir(parents=True, exist_ok=True)
    results = an.analyze(RUN, OUT)
    an.write_report(results, OUT, RUN)
    if not FAKE and OUT == NDATA:
        git_commit("AAMR-NIGHT-1: frozen raw manifest, results and generated report (autonomous run)")
    return {"status": "done", "frozen_files": freeze["files"], "results": str(OUT / "results.json")}


def freeze_raw():
    files = {p.relative_to(RUN).as_posix(): p0.file_sha(p) for p in sorted(RUN.rglob("*"))
             if p.is_file() and p.name not in ("heartbeat.json", "supervisor.lock", "progress.log", "supervisor.log", "worker.log", "state.json", "restarts.json")
             and not p.suffix == ".tmp"}
    out = {"frozen_at": now_iso(), "raw_root": str(RUN), "files": files}
    atomic_json(OUT / "raw-freeze.json", out)
    return {"files": len(files)}


def git_commit(message):
    try:
        subprocess.run(["git", "add", "data/lab/aamr-night1"], cwd=ROOT, check=True, capture_output=True, timeout=120)
        r = subprocess.run(["git", "commit", "-m", message + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
        log("git commit: " + (r.stdout or r.stderr).strip()[:200])
    except Exception as exc:
        log_error("git commit failed: " + repr(exc))


def stage_smoke_q14(ctx):
    det, _ = det_lessons_vc()
    arms = {"N": {"bucket": "T"}, "TrO": {"bucket": "T", "tr": lesson_map(det + [given(*FUEL_SIG, ORACLE, "oracle")])}}
    tasks = p0.read_json(p0.DATA / "split.json")["test"][:3]
    return run_session(ctx, "smoke", "q14", tasks, arms, 99)


def stage_smoke_flash(ctx):
    if not ctx.flash.open():
        return {"status": "done", "flash_available": False, "reason": ctx.flash.unavailable}
    r = ctx.flash.ask("smoke:flash:1", [{"role": "user", "content": 'Return JSON {"note": "ok"} and nothing else.'}], max_tokens=20)
    return {"status": "done", "flash_available": True, "text": r["text"][:100], "usage": r["usage"], "usd_upper": r["usd_upper"],
            "returned_model": r.get("returned_model")}


def stage_smoke_q9(ctx):
    arms = {"N": {"bucket": "T"}}
    tasks = p0.read_json(p0.DATA / "split.json")["test"][:1]
    out = run_session(ctx, "smoke9", "q9", tasks, arms, 98)
    ctx.gw.release("q9")
    return out


SMOKE_STAGES = ["preflight_q14", "smoke_q14", "smoke_flash", "preflight_q9", "smoke_q9"]

STAGE_FN = {"smoke_q14": stage_smoke_q14, "smoke_flash": stage_smoke_flash, "smoke_q9": stage_smoke_q9,
"preflight_q14": stage_preflight_q14, "a0_writer": stage_a0_writer, "b0_writers": stage_b0_writers, "b1_quality": stage_b1_quality,
            "sA": stage_sA, "census": stage_census, "d0_build": stage_d0_build, "sD": stage_sD, "sC": stage_sC,
            "preflight_q9": stage_preflight_q9, "sE": stage_sE, "final": stage_final}


# ----------------------------------------------------------------------------- worker and supervisor

def prevent_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED, this process only
    except Exception:
        pass


def write_state(ctx):
    atomic_json(RUN / "state.json", ctx.state)


def next_stage(state):
    for s in STAGES:
        st = state["stages"].get(s, {})
        if st.get("status") not in ("done", "partial", "skipped", "failed"):
            return s
    return None


def work(stages=None) -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    prevent_sleep()
    cfg = load_config()
    ctx = Ctx(cfg)
    if ctx.state.get("config_id") not in (None, config_id(cfg)):
        log_error("config or protocol changed during the run; refusing to continue")
        return EXIT_FATAL
    ctx.state["config_id"] = config_id(cfg)
    order = stages or (SMOKE_STAGES if SMOKE else STAGES)
    stage = next((s for s in order if ctx.state["stages"].get(s, {}).get("status") not in ("done", "partial", "skipped", "failed")), None)
    if stage is None:
        if not SMOKE:
            pass
        (RUN / "DONE.json").write_text(json.dumps({"at": now_iso(), "stages": ctx.state["stages"]}, indent=2, default=str), encoding="utf-8")
        return EXIT_DONE
    deps = DEPENDS.get(stage, [])
    bad = [d for d in deps if ctx.state["stages"].get(d, {}).get("status") not in ("done", "partial")]
    if bad and stage != "final":
        ctx.state["stages"][stage] = {"status": "skipped", "reason": "dependency not done: " + ", ".join(bad), "at": now_iso()}
        write_state(ctx)
        log(f"stage {stage} skipped: dependency {bad}")
        return EXIT_NEXT
    log(f"stage {stage} starting (local calls so far {ctx.gw.total_local}, flash {ctx.flash.spent()})")
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
    except Exception as exc:
        st["errors"] = st.get("errors", 0) + 1
        log_error(f"stage {stage} error {st['errors']}: {exc!r}\n{traceback.format_exc()}")
        if st["errors"] >= 2:
            st.update({"status": "failed", "reason": repr(exc)[:500], "at": now_iso()})
        write_state(ctx)
        return EXIT_NEXT if st["errors"] >= 2 else EXIT_TRANSIENT
    st.update(result if isinstance(result, dict) else {"status": "done"})
    st.setdefault("status", "done")
    st["finished_at"] = now_iso()
    write_state(ctx)
    log(f"stage {stage} -> {st['status']}")
    heartbeat(ctx, stage, {"stage_status": st["status"]})
    return EXIT_NEXT


def pid_alive(pid: int) -> bool:
    try:
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259
    except Exception:
        return False


def supervise() -> int:
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / "DONE.json").exists() or (RUN / "STOPPED.json").exists():
        return 0
    lock = RUN / "supervisor.lock"
    if lock.exists():
        try:
            if pid_alive(int(lock.read_text().strip())):
                return 0
        except ValueError:
            pass
    lock.write_text(str(os.getpid()))
    prevent_sleep()
    cfg = load_config()
    sup = cfg["supervisor"]
    restarts_path = RUN / "restarts.json"
    restarts = p0.read_json(restarts_path)["count"] if restarts_path.exists() else 0
    py = sys.executable
    try:
        while True:
            with open(RUN / "worker.log", "a", encoding="utf-8") as wl:
                proc = subprocess.Popen([py, str(Path(__file__).resolve()), "work"] + (["--smoke"] if SMOKE else []), cwd=str(ROOT), stdout=wl, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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
                atomic_json(RUN / "STOPPED.json", {"at": now_iso(), "reason": "fatal: configuration or protocol changed (see errors.log)"})
                return 2
            restarts += 1
            atomic_json(restarts_path, {"count": restarts, "at": now_iso(), "last_rc": rc})
            if restarts > sup["max_restarts"]:
                atomic_json(RUN / "STOPPED.json", {"at": now_iso(), "reason": f"technical failures exceeded {sup['max_restarts']} restarts (last rc {rc}); all data kept, see errors.log"})
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["work", "supervise", "status", "analyze", "report", "freeze"])
    ap.add_argument("--stages", nargs="*")
    ap.add_argument("--smoke", action="store_true", help="technical test in a separate run folder (counted in the program's budget)")
    a = ap.parse_args(argv)
    if a.smoke:
        global RUN, SMOKE
        RUN, SMOKE = NWORK / "smoke-run", True
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
    import aamr_night1_analysis as an
    OUT.mkdir(parents=True, exist_ok=True)
    results = an.analyze(RUN, OUT)
    if a.cmd == "report":
        an.write_report(results, OUT, RUN)
    print(json.dumps({k: results[k] for k in list(results)[:6]}, indent=2, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
