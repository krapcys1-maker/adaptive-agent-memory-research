"""EXP-XFER-1, stage S1 (data/lab/experience-xfer-v1/PLAN.md, SPEC v0.1): tool-keyed lessons on BFCL Vehicle Control.

Arms: N (no memory), R+ (the pilot's success traces), Tp (lessons shown up front), Tr (lesson shown after a matching error),
G (LLM-written tool guidance), T* (conditional ceiling). Base tasks reuse the pilot's frozen split and pools; the probe is
`multi_turn_miss_param`, cut after the turn whose ground truth is empty.

The pilot (scripts/experience_pilot_v0.py, commit 52487db) is imported unchanged. Raw runs live outside Git under
../experience-transfer-2026-11-12/raw. TradingBot tasks (ids 100-149) are a reserve and must never be used.

Usage: python scripts/experience_xfer_v1.py {s0|s1a|s1b|s1c|s1d|s1e|freeze|analyze|ledger}
"""
from __future__ import annotations

import argparse
import ast
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experience_pilot_v0 as p0  # noqa: E402  (frozen pilot code)

ROOT = p0.ROOT
PDATA = p0.DATA                                                   # pilot data, read-only
XDATA = ROOT / "data/lab/experience-xfer-v1"
XWORK = ROOT.parent / "experience-transfer-2026-11-12"            # outside Git: raw runs
SEED = p0.SEED
PILOT_E2 = p0.WORK / "raw" / "e2" / "20261112T110823Z"            # frozen pilot test run (N, R+ reference)

SYSTEM_V2 = (
    "You operate tools for a user. In each step return JSON {\"calls\":[...]} with the function calls to execute now.\n"
    "You may return several calls in one step; they run in order and you will see their results.\n"
    "If a result contains an error, correct the problem and continue.\n"
    "When the user's current request is completely done, return {\"calls\":[]}.\n"
    "If the current request cannot be carried out because required information is missing or no listed function fits, "
    "return {\"calls\":[]} and do not guess.\n"
    "Never ask the user a question. Use only the functions listed below.\n"
    "\n"
    "FUNCTIONS\n"
)
LESSON_HEADER = ("NOTES FROM EARLIER TASKS ABOUT TOOLS (each note is about one tool; "
                 "it applies only when you call that tool):")
NOTE_PREFIX = "NOTE FROM EARLIER TASKS: "
MIN_TASKS = 2
SHARE = 0.6
MSG_CHARS = 110
MAX_NOTES = 12
BLOCK_CHARS = 2800
G_CHARS = 700
G_HISTORY = 30
G_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["guidance"], "properties": {"guidance": {"type": "string"}}}
BASE_ARMS = ["Tp", "Tr", "G"]
PROBE_ARMS = ["N", "R+", "Tp", "G"]
DETERMINISM_TASKS = 5


# ----------------------------------------------------------------------------- guards and small helpers

def task_number(task_id: str) -> int:
    return int(task_id.rsplit("_", 1)[1])


def guard_task(task_id: str) -> None:
    """TradingBot (100-149) is an untouched reserve: it must never reach a prompt, the executor or the checker."""
    if 100 <= task_number(task_id) <= 149:
        raise RuntimeError("reserved TradingBot task must not be used: " + task_id)


def base_id(probe_id: str) -> str:
    return f"multi_turn_base_{task_number(probe_id)}"


# ----------------------------------------------------------------------------- lesson compiler (SPEC 5.2)
# Normative source: ../experience-transfer-2026-11-12/reanalysis/03_lesson_compiler_prototype.py. Logic carried over unchanged.

def canon_value(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (list, tuple)):
        return [canon_value(x) for x in v]
    if isinstance(v, dict):
        return {k: canon_value(x) for k, x in sorted(v.items())}
    return v


def parse_call(s):
    node = ast.parse(s.strip(), mode="eval").body
    name = node.func.id
    kw = {k.arg: canon_value(ast.literal_eval(k.value)) for k in node.keywords}
    return name, kw


def canon_call(s):
    name, kw = parse_call(s)
    return "%s(%s)" % (name, ", ".join(f"{k}={v!r}" for k, v in kw.items()))


def fn(call):
    return call.split("(", 1)[0]


def error_text(result_text):
    prefix = "Error during execution: "
    if result_text.startswith(prefix):
        return result_text[len(prefix):]
    try:
        value = json.loads(result_text)
        if isinstance(value, dict) and "error" in value:
            return str(value["error"])
    except (ValueError, TypeError):
        pass
    return result_text


def arg_strings(kw):
    out = []
    for v in kw.values():
        for x in (v if isinstance(v, list) else [v]):
            if isinstance(x, str) and len(x) >= 2:
                out.append(x)
    return sorted(set(out), key=len, reverse=True)


def error_key(result_text, kw):
    s = error_text(result_text)
    for a in arg_strings(kw):
        s = re.sub(r"(?<![A-Za-z0-9_])" + re.escape(a) + r"(?![A-Za-z0-9_])", "<arg>", s)
    s = re.sub(r"'[^']*'|\"[^\"]*\"", "<v>", s)
    s = re.sub(r"\d+(?:\.\d+)?", "<n>", s)
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|(?<=[.!?])(?=[A-Z])", s) if p.strip()]
    chosen = next((p for p in parts if len(re.findall(r"[A-Za-z]{2,}", p)) >= 3), parts[0] if parts else s)
    return re.sub(r"\s+", " ", chosen).strip().rstrip(".").lower()[:100]


def collect_observations(pool):
    obs = defaultdict(list)
    for rec in pool:
        open_f = {}
        for st in rec["steps"]:
            try:
                name, kw = parse_call(st["call"])
            except Exception:
                continue
            if st["error"]:
                key = error_key(st["result"], kw)
                cur = open_f.get(name)
                if cur is not None and cur["key"] != key:
                    obs[(name, cur["key"])].append({"task": rec["source_task"], "turn": rec["turn"], "resolved": True,
                                                   "between": list(cur["between"]), "args_failed": cur["args"],
                                                   "args_ok": None, "msg": cur["msg"]})
                    cur = None
                if cur is None:
                    open_f[name] = {"key": key, "args": kw, "between": [], "msg": error_text(st["result"])}
                else:
                    cur["args"] = kw
            else:
                call_c = canon_call(st["call"])
                for f, cur in open_f.items():
                    if f != name:
                        cur["between"].append(call_c)
                cur = open_f.pop(name, None)
                if cur is not None:
                    obs[(name, cur["key"])].append({"task": rec["source_task"], "turn": rec["turn"], "resolved": True,
                                                   "between": list(cur["between"]), "args_failed": cur["args"],
                                                   "args_ok": kw, "msg": cur["msg"]})
        for f, cur in open_f.items():
            obs[(f, cur["key"])].append({"task": rec["source_task"], "turn": rec["turn"], "resolved": False,
                                         "msg": cur["msg"]})
    return obs


def compile_lessons(pool, min_tasks=MIN_TASKS):
    obs = collect_observations(pool)
    lessons, rejected = [], []
    for (f, key), lst in sorted(obs.items()):
        res = [o for o in lst if o["resolved"]]
        info = {"function": f, "error_key": key, "tasks_seen": len({o["task"] for o in lst}),
                "tasks_resolved": len({o["task"] for o in res}), "observations": len(lst)}
        if info["tasks_resolved"] < min_tasks:
            info["reason"] = "support"
            rejected.append(info)
            continue
        n = len(res)
        names_per_obs = [list(dict.fromkeys(fn(c) for c in o["between"])) for o in res]
        byname = Counter(nm for names in names_per_obs for nm in names)
        exact = Counter(c for o in res for c in dict.fromkeys(o["between"]))

        def mean_position(nm):
            pos = [names.index(nm) for names in names_per_obs if nm in names]
            return sum(pos) / len(pos)

        fix = []
        for nm in sorted((x for x, cnt in byname.items() if cnt / n >= SHARE), key=lambda x: (mean_position(x), x)):
            best, bc = max(((c, k) for c, k in exact.items() if fn(c) == nm), key=lambda t: (t[1], t[0]))
            fix.append(best if bc / n >= SHARE else f"{nm}(...)")
        values = Counter()
        for o in res:
            if o["args_ok"] is None:
                continue
            for p in sorted(o["args_ok"]):
                if o["args_failed"].get(p) != o["args_ok"][p]:
                    values[(p, repr(o["args_ok"][p]))] += 1
        arg_fix = [f"{p}={v}" for (p, v), c in sorted(values.items()) if c / n >= SHARE]
        if not fix and not arg_fix:
            info["reason"] = "no consistent fix"
            rejected.append(info)
            continue
        info.update({"fix_calls": fix, "arg_fix": arg_fix, "example_message": res[0]["msg"][:MSG_CHARS],
                     "source_turns": sorted({f'{o["task"]}:t{o["turn"]}' for o in res})})
        lessons.append(info)
    lessons.sort(key=lambda d: (-d["tasks_resolved"], d["function"], d["error_key"]))
    return lessons, rejected


def open_problems(rejected):
    return [r for r in rejected if r["tasks_seen"] >= 2]


def note_text(les):
    parts = []
    if les["fix_calls"]:
        parts.append("first calling " + "; ".join(les["fix_calls"]))
    if les["arg_fix"]:
        parts.append("using " + ", ".join(les["arg_fix"]))
    return (f'{les["function"]}: error "{les["example_message"]}" was resolved by ' + " and ".join(parts) +
            f'. Seen in {les["tasks_resolved"]} tasks.')


def render_lesson_block(lessons, available_functions=None):
    rows = [l for l in lessons if available_functions is None or l["function"] in available_functions][:MAX_NOTES]
    lines = [LESSON_HEADER]
    for les in rows:
        line = "- " + note_text(les)
        if len("\n".join(lines + [line])) > BLOCK_CHARS:
            break
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def lesson_id(les) -> str:
    return f'{les["function"]}|{les["error_key"]}'


def render_guidance_block(guidance, available_functions):
    """guidance: {function: text}. Same header and place as the lesson block (SPEC 5.5)."""
    lines = [f"- {f}: {text}" for f, text in guidance.items() if f in available_functions]
    return "\n".join([LESSON_HEADER] + lines) if lines else ""


# ----------------------------------------------------------------------------- BFCL access with the probe files

class BfclX(p0.Bfcl):
    def __init__(self, root: Path):
        super().__init__(root)
        data = self.root / "bfcl_eval/data"
        self.probe_tasks = {r["id"]: r for r in p0.read_jsonl(data / "BFCL_v4_multi_turn_miss_param.json")}
        self.probe_gt = {r["id"]: r["ground_truth"] for r in p0.read_jsonl(data / "possible_answer/BFCL_v4_multi_turn_miss_param.json")}

    def doc(self, name):
        for docs in self.docs.values():
            for d in docs:
                if d["name"] == name:
                    return d
        raise KeyError(name)

    def function_names(self, task):
        return {d["name"] for d in self.functions(task)}

    def execute(self, calls, task, model_name):
        guard_task(task["id"])
        return super().execute(calls, task, model_name)

    def check(self, model_turns, gt_turns, task, model_name):
        guard_task(task["id"])
        return super().check(model_turns, gt_turns, task, model_name)


def load_config():
    return p0.read_json(XDATA / "config.json")


def bfcl_from_config(cfg):
    return BfclX((ROOT / cfg["bfcl_root"]).resolve())


# ----------------------------------------------------------------------------- ledger and stage folder (own raw root, own caps)

def raw_dir(stage: str, run_id: str) -> Path:
    return XWORK / "raw" / stage / run_id


def ledger():
    """Model calls (attempts) and seconds over all raw runs of this experiment. Source of truth for the caps."""
    calls, seconds, runs = 0, 0.0, []
    base = XWORK / "raw"
    if base.exists():
        for manifest in sorted(base.glob("*/*/manifest.json")):
            m = p0.read_json(manifest)
            n = len(p0.read_jsonl(manifest.parent / "attempts.jsonl"))
            calls += n
            seconds += m.get("elapsed_seconds") or 0.0
            runs.append({"stage": m["stage"], "run_id": m["run_id"], "calls": n, "elapsed_seconds": m.get("elapsed_seconds"),
                         "status": m.get("status")})
    return {"calls": calls, "seconds": seconds, "runs": runs}


def remaining(cfg):
    led = ledger()
    lim = cfg["limits"]
    return {"calls": min(lim["s1_max_calls"], lim["max_calls_total"]) - led["calls"], "seconds": lim["max_seconds_total"] - led["seconds"]}


def make_client(cfg, out: Path, max_calls: int):
    from nie_reader_pilot import LocalReader
    rem = remaining(cfg)
    if rem["calls"] <= 0 or rem["seconds"] <= 0:
        raise RuntimeError("Hard cap exhausted.")
    rc = {"base_url": cfg["base_url"], "http_timeout_seconds": cfg["http_timeout_seconds"], "model": cfg["model"],
          "model_digest": cfg["model_digest"], "options": cfg["options"], "max_calls": min(max_calls, rem["calls"]),
          "max_seconds": rem["seconds"]}
    return LocalReader(rc, out)


class XStage:
    """Raw run folder with a manifest; never reused (no resume, no retry). Mirrors the pilot's Stage with this experiment's root."""

    def __init__(self, stage: str, cfg, max_calls: int, client_factory=None):
        self.stage, self.cfg = stage, cfg
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.out = raw_dir(stage, self.run_id)
        if self.out.exists():
            raise RuntimeError("run folder exists")
        self.out.mkdir(parents=True)
        self.client = (client_factory or make_client)(cfg, self.out, max_calls)
        self.started = time.monotonic()
        self.manifest = {"stage": stage, "run_id": self.run_id, "started_at": p0.now_iso(), "status": "running",
                         "config_sha256": p0.file_sha(XDATA / "config.json")}
        p0.write_json(self.out / "manifest.json", self.manifest)

    def preflight(self):
        if hasattr(self.client, "preflight"):
            self.manifest["preflight"] = self.client.preflight()
            p0.write_json(self.out / "manifest.json", self.manifest)

    def close(self, status: str, extra=None):
        self.manifest.update({"status": status, "finished_at": p0.now_iso(), "elapsed_seconds": time.monotonic() - self.started})
        if extra:
            self.manifest.update(extra)
        try:
            if status == "completed" and hasattr(self.client, "finish"):
                self.manifest["finish"] = self.client.finish()
        finally:
            if hasattr(self.client, "release"):
                try:
                    self.client.release()
                except Exception as exc:
                    self.manifest["release_error"] = repr(exc)
            p0.write_json(self.out / "manifest.json", self.manifest)


def latest_completed(stage: str) -> Path:
    runs = sorted(p.parent for p in (XWORK / "raw" / stage).glob("*/manifest.json") if p0.read_json(p)["status"] == "completed")
    if not runs:
        raise RuntimeError("no completed run for " + stage)
    return runs[-1]


# ----------------------------------------------------------------------------- the agent loop (pilot loop + three extensions)

def run_episode_x(bfcl, task, client, names, *, stage: str, arm: str, key: str, ctx_limit: int, system_template=None, block=None,
                  tr_lessons=None, stop_after_turn=None, seed: int = 7):
    """One episode. block(task_id, turn_index, request) -> (text, item_ids, meta) or None.
    tr_lessons: {(function, error_key): lesson} for arm Tr. stop_after_turn: last turn index to run (probe)."""
    guard_task(task["id"])
    docs_by_name = {d["name"]: d for d in bfcl.functions(task)}
    schema = p0.output_schema(bfcl, task)
    live = names.new(stage, arm, task["id"], "live")
    system = (p0.system_prompt(bfcl, task) if system_template is None
              else system_template + "\n\n".join(p0.render_function(d) for d in bfcl.functions(task)))
    history = [{"role": "system", "content": system}]
    record = {"task": task["id"], "arm": arm, "stage": stage, "key": key, "live_name": live, "turns": [], "status": "completed",
              "system_sha256": p0.sha(history[0]["content"]), "schema_sha256": p0.sha(schema), "started_at": p0.now_iso()}
    lesson_order = {lesson_id(l): i for i, l in enumerate(tr_lessons.values())} if tr_lessons else {}
    notes_shown = set()
    for ti, messages in enumerate(task["question"]):
        if len(messages) != 1 or messages[0]["role"] != "user":
            raise ValueError("unexpected turn shape")
        request = messages[0]["content"]
        text, items, meta = block(task["id"], ti, request) if block else ("", [], None)
        turn = {"index": ti, "request": request, "memory": {"items": items, "block_chars": len(text),
                                                            "block_sha256": p0.sha(text) if text else None, "meta": meta,
                                                            "block_text": text}, "steps": []}
        record["turns"].append(turn)
        start = len(history)
        history.append({"role": "user", "content": (text + "\n\n" + request) if text else request})
        ended = False
        for si in range(p0.MAX_STEPS):
            estimate = p0.chars_tokens(history)
            if estimate >= ctx_limit:
                record["status"] = "context_overflow"
                turn["steps"].append({"overflow_estimate": estimate})
                break
            response = client.ask(f"{key}:t{ti}:s{si}", history, seed, output_schema=schema)
            usage = response.get("usage") or {}
            step = {"key": f"{key}:t{ti}:s{si}", "text": response["text"], "done_reason": response.get("done_reason"),
                    "estimate_tokens": estimate, "prompt_eval_count": usage.get("prompt_eval_count"), "eval_count": usage.get("eval_count"),
                    "wall_seconds": response.get("wall_seconds"), "calls": []}
            turn["steps"].append(step)
            history.append({"role": "assistant", "content": response["text"]})
            raw = p0.parse_output(response["text"], response.get("done_reason"))
            if raw is None:
                step["invalid_output"] = True
                results = [{"error": "invalid output: response is not valid JSON for the required schema"}]
            elif not raw:
                ended = True
            else:
                results = []
                for call in raw:
                    call_str, error = p0.validate_call(call, docs_by_name)
                    entry = {"raw": call, "call": call_str, "valid": call_str is not None}
                    if call_str is None:
                        entry["result"] = json.dumps({"error": error})
                    else:
                        out, _ = bfcl.execute([call_str], task, live)
                        entry["result"] = out[0]
                        entry["error"] = p0.is_error_result(out[0])
                    step["calls"].append(entry)
                    results.append({"call": call_str or (call.get("name") if isinstance(call, dict) else None),
                                    "result": p0.truncate(entry["result"], p0.RESULT_CHARS)})
            pec = usage.get("prompt_eval_count")
            if pec is not None and pec >= ctx_limit:
                record["status"] = "context_overflow"
                break
            if ended:
                break
            content = "RESULTS: " + json.dumps(results, ensure_ascii=False)
            if tr_lessons:
                hits = []
                for entry in step["calls"]:
                    if entry["valid"] and entry.get("error"):
                        name, kw = parse_call(entry["call"])
                        les = tr_lessons.get((name, error_key(entry["result"], kw)))        # full, untruncated result
                        if les is not None and lesson_id(les) not in notes_shown:
                            notes_shown.add(lesson_id(les))
                            hits.append(les)
                if hits:
                    hits.sort(key=lambda l: lesson_order[lesson_id(l)])
                    content += "\n\n" + "\n".join(NOTE_PREFIX + note_text(l) for l in hits)
                    step["notes"] = [lesson_id(l) for l in hits]
            history.append({"role": "user", "content": content})
        else:
            record["status"] = "forced_termination"
        history[start] = {"role": "user", "content": request}             # the memory block of a finished turn leaves the history
        if record["status"] != "completed":
            break
        if not ended:
            record["status"] = "forced_termination"
            break
        if stop_after_turn is not None and ti >= stop_after_turn:
            break
    record["finished_at"] = p0.now_iso()
    return record


# ----------------------------------------------------------------------------- memory blocks per arm

def lessons_block_provider(bfcl, lessons, lessons_sha, kind="lessons"):
    def block(task_id, ti, request):
        task = bfcl.tasks.get(task_id) or bfcl.probe_tasks[task_id]
        avail = bfcl.function_names(task)
        text = render_lesson_block(lessons, avail)
        ids = [lesson_id(l) for l in lessons if l["function"] in avail][:MAX_NOTES] if text else []
        return text, ids, {"kind": kind, "sha256": lessons_sha}
    return block


def guidance_block_provider(bfcl, guidance, guidance_sha):
    def block(task_id, ti, request):
        task = bfcl.tasks.get(task_id) or bfcl.probe_tasks[task_id]
        avail = bfcl.function_names(task)
        text = render_guidance_block(guidance, avail)
        return text, [f for f in guidance if f in avail] if text else [], {"kind": "guidance", "sha256": guidance_sha}
    return block


def rplus_base_provider():
    """R+ on base tasks: exactly the pilot's frozen retrieval plan and pool."""
    memory = p0.memory_provider("R+")

    def block(task_id, ti, request):
        rows, meta = memory(task_id, ti, request)
        return p0.render_block(rows), [p0.pool_row_id(r) for r in rows], meta
    return block


def rplus_probe_provider(plan):
    """R+ in the probe: retrieval precomputed in probe-plan.json from the pilot's frozen A+ pool."""
    path = PDATA / "pools" / "A_plus.jsonl"
    rows = {p0.pool_row_id(r): r for r in p0.read_jsonl(path)}
    meta = {"pool": "A_plus", "pool_sha256": p0.file_sha(path)}
    by_entry = {e["id"]: e for e in plan["entries"]}

    def block(task_id, ti, request):
        ids = by_entry[task_id]["r_plus"][ti]
        return p0.render_block([rows[i] for i in ids]), list(ids), meta
    return block


def tr_map(lessons):
    return {(l["function"], l["error_key"]): l for l in lessons}


# ----------------------------------------------------------------------------- probe evaluation (SPEC 9.3)

def _scalar_values(obj):
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(_scalar_values(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_scalar_values(v))
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        out.append(obj)
    elif isinstance(obj, str) and len(obj) >= 2:
        out.append(obj)
    return out


def _value_forms(v):
    if isinstance(v, str):
        return [v]
    forms = {repr(v), str(v)}
    if isinstance(v, float) and v.is_integer():
        forms.add(str(int(v)))
    if isinstance(v, int):
        forms.add(str(float(v)))
    return sorted(forms)


def _contains_number(text, form):
    return re.search(r"(?<![0-9.])" + re.escape(form) + r"(?![0-9])", text) is not None


def _in_text(v, text):
    if isinstance(v, str):
        return v in text
    return any(_contains_number(text, f) for f in _value_forms(v))


def evaluate_probe(bfcl, record, names, probe_turn: int):
    """Measures at the turn whose ground truth is empty. UAR counts any proposed call, valid or not."""
    task = bfcl.probe_tasks[record["task"]]
    turns = record["turns"]
    reached = len(turns) > probe_turn and bool(turns[probe_turn]["steps"]) and "key" in turns[probe_turn]["steps"][0]
    out = {"task": record["task"], "arm": record["arm"], "stage": record["stage"], "status": record["status"], "probe_turn": probe_turn,
           "reached": reached, "turns_started": len(turns),
           "model_calls": sum(1 for t in turns for s in t["steps"] if "key" in s),
           "prompt_eval_sum": sum(s.get("prompt_eval_count") or 0 for t in turns for s in t["steps"]),
           "eval_sum": sum(s.get("eval_count") or 0 for t in turns for s in t["steps"]),
           "wall_seconds": sum(s.get("wall_seconds") or 0 for t in turns for s in t["steps"])}
    if not reached:
        out.update({"proposed": None, "executed": None, "state_changed": None, "imported_argument": None, "invalid_outputs": None,
                    "proposed_calls": None, "block_chars": None})
        return out
    turn = turns[probe_turn]
    calls = [c for s in turn["steps"] for c in s.get("calls", [])]
    executed = [c["call"] for c in calls if c["valid"]]
    before = [c["call"] for t in turns[:probe_turn] for s in t["steps"] for c in s.get("calls", []) if c["valid"]]
    tag = (record["stage"], record["arm"], record["task"])
    _, inst_a = bfcl.execute(before, task, names.new(*tag, "probe_before"))
    _, inst_b = bfcl.execute(before + executed, task, names.new(*tag, "probe_after"))
    seen = "\n".join([t["request"] for t in turns[:probe_turn + 1]] +
                     [c["result"] for t in turns[:probe_turn] for s in t["steps"] for c in s.get("calls", [])])
    block_text = turn["memory"].get("block_text") or ""
    imported = []
    for c in calls:
        args = c["raw"].get("arguments") if isinstance(c["raw"], dict) else None
        for v in _scalar_values(args):
            if not _in_text(v, seen) and block_text and _in_text(v, block_text):
                imported.append(v)
    out.update({"proposed": bool(calls), "executed": bool(executed), "state_changed": not bfcl.state_ok(inst_b, inst_a),
                "imported_argument": bool(imported), "imported_values": imported[:8],
                "invalid_outputs": sum(1 for s in turn["steps"] if s.get("invalid_output")), "proposed_calls": len(calls),
                "proposed_functions": [c["raw"].get("name") if isinstance(c["raw"], dict) else None for c in calls],
                "block_chars": turn["memory"]["block_chars"]})
    return out


# ----------------------------------------------------------------------------- S0: static reads and the probe gate G1p

def probe_entries(bfcl, ids):
    """G1p (SPEC 2.2) for the miss_param entries of the given base ids."""
    names = p0.Names("g1p")
    report = {}
    for b in ids:
        pid = f"multi_turn_miss_param_{task_number(b)}"
        guard_task(pid)
        task, gt, base = bfcl.probe_tasks[pid], bfcl.probe_gt[pid], bfcl.tasks[b]
        empty = [i for i, t in enumerate(gt) if not t]
        k = empty[0] if empty else None
        same_request = (k is not None and k < len(base["question"]) and
                        task["question"][k][0]["content"] == base["question"][k][0]["content"])
        prefix_errors = []
        if k is not None:
            name = names.new("g1p", pid)
            for t in gt[:k]:
                out, _ = bfcl.execute(t, task, name)
                prefix_errors.extend(c for c, r in zip(t, out) if p0.is_error_result(r))
        row = {"base_id": b, "probe_turn": k, "empty_turns": len(empty), "request_identical_to_base": bool(same_request),
               "prefix_error_calls": prefix_errors, "config_differs": task["initial_config"] != base["initial_config"],
               "turn_shapes_ok": all(len(m) == 1 and m[0]["role"] == "user" for m in task["question"]),
               "classes_equal_base": task["involved_classes"] == base["involved_classes"]}
        row["ok"] = (len(empty) == 1 and not same_request and not prefix_errors and row["turn_shapes_ok"] and row["classes_equal_base"])
        report[pid] = row
    return report


def stage_s0(cfg):
    bfcl = bfcl_from_config(cfg)
    split = p0.read_json(PDATA / "split.json")
    build = p0.read_json(PDATA / "build.json")
    pools_ok = {n: p0.file_sha(PDATA / "pools" / f"{n}.jsonl") == build["pools"][n]["sha256"] for n in ("A", "A_plus")}
    checker_src = (bfcl.root / "bfcl_eval/eval_checker/multi_turn_eval/multi_turn_checker.py").read_text(encoding="utf-8")
    skip = re.search(r"if not single_turn_ground_truth_list:\s*\n\s*continue", checker_src) is not None
    body = checker_src.split("def multi_turn_checker", 1)[1].split("\ndef ", 1)[0]
    g1p = probe_entries(bfcl, p0.VC_IDS)
    ok = sorted((i for i, r in g1p.items() if r["ok"]), key=task_number)
    p0.write_json(XDATA / "g1p.json", {"domain": "VehicleControlAPI", "entries": g1p, "n_ok": len(ok), "ok": ok,
                                       "excluded": sorted((i for i, r in g1p.items() if not r["ok"]), key=task_number)})
    out = {"bfcl_commit": cfg["bfcl_commit"], "pilot_commit": cfg["pilot_commit"],
           "pilot_pools_sha_match_build_json": pools_ok,
           "checker_skips_empty_ground_truth_turn": skip,
           "irrelevance_checker_called_from_multi_turn_checker": "multi_turn_irrelevance_checker(" in body,
           "vc_probe_entries": len(g1p), "vc_probe_entries_ok": len(ok),
           "vc_probe_near": sum(1 for i in ok if base_id(i) in split["train"]),
           "vc_probe_far": sum(1 for i in ok if base_id(i) in split["test"]),
           "vc_probe_config_differs": sorted(i for i in ok if g1p[i]["config_differs"]),
           "vc_probe_turns_to_run": sum(g1p[i]["probe_turn"] + 1 for i in ok),
           "system_v2_extra_line": [l for l in SYSTEM_V2.splitlines() if l not in p0.SYSTEM_TEMPLATE.splitlines()]}
    p0.write_json(XDATA / "s0-static.json", out)
    if not all(pools_ok.values()):
        raise SystemExit("STOP: pilot pools differ from the pilot's build.json")
    if not skip:
        raise SystemExit("STOP: checker no longer skips empty ground-truth turns; SPEC 9.3 must be revisited")
    return out


# ----------------------------------------------------------------------------- S1a: transport and agreement with the pilot

def texts(record):
    return [s.get("text") for t in record["turns"] for s in t["steps"]]


def pilot_episodes():
    recs = {(r["task"], r["arm"]): r for r in p0.read_jsonl(PILOT_E2 / "episodes.jsonl")}
    evs = {(e["task"], e["arm"]): e for e in p0.read_jsonl(PILOT_E2 / "evaluations.jsonl")}
    return recs, evs


def transport_checks(st, bfcl):
    """The pilot's G2 probes (4 calls): schema obeyed, model fully on the GPU."""
    e0 = p0.read_json(PDATA / "e0-static.json")
    longest_id = max(e0["system_prompt_chars"]["by_task"], key=lambda k: e0["system_prompt_chars"]["by_task"][k])
    task = bfcl.tasks[longest_id]
    schema, long_system = p0.output_schema(bfcl, task), p0.system_prompt(bfcl, task)
    short = "Return JSON that matches the schema."
    probes = [("short-1", [{"role": "system", "content": short},
                           {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"on\"."}],
               [{"name": "setHeadlights", "arguments": {"mode": "on"}}]),
              ("long-1", [{"role": "system", "content": long_system},
                          {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"off\". Do nothing else."}],
               [{"name": "setHeadlights", "arguments": {"mode": "off"}}])]
    probes.append(("long-2", probes[1][1], probes[1][2]))
    probes.append(("short-2", [{"role": "system", "content": short}, {"role": "user", "content": "Return an empty list of calls."}], []))
    checks = []
    for key, messages, expected in probes:
        r = st.client.ask("g2:" + key, messages, 7, output_schema=schema)
        row = {"key": key, "text": r["text"], "ok": p0.parse_output(r["text"], r.get("done_reason")) == expected, "usage": r.get("usage")}
        if key == "long-1" and hasattr(st.client, "request"):
            row["api_ps"] = st.client.request("/api/ps")
        checks.append(row)
    ps = next((c.get("api_ps") for c in checks if c.get("api_ps")), None)
    model_ps = (ps or {}).get("models", [{}])[0] if ps else {}
    return {"checks": checks, "all_ok": all(c["ok"] for c in checks),
            "gpu_full": bool(model_ps) and model_ps.get("size_vram") == model_ps.get("size"), "api_ps_model": model_ps}


def stage_s1a(cfg, client_factory=None):
    bfcl = bfcl_from_config(cfg)
    split = p0.read_json(PDATA / "split.json")
    tasks = split["test"][:DETERMINISM_TASKS]
    pilot_recs, _ = pilot_episodes()
    st = XStage("s1a", cfg, 400, client_factory)
    names = p0.Names("s1a_" + st.run_id)
    rplus = rplus_base_provider()
    rows = []
    try:
        st.preflight()
        transport = transport_checks(st, bfcl)
        if not transport["all_ok"] or not transport["gpu_full"]:
            raise SystemExit("STOP: transport check failed: " + json.dumps({k: transport[k] for k in ("all_ok", "gpu_full")}))
        for t in tasks:
            for arm, block in (("N", None), ("R+", rplus)):
                key = f"s1a:{arm}:{t}"
                rec = run_episode_x(bfcl, bfcl.tasks[t], st.client, names, stage="s1a", arm=arm, key=key, ctx_limit=p0.ctx_limit(cfg), block=block)
                ev = p0.evaluate_episode(bfcl, rec, names)
                p0.append_jsonl(st.out / "episodes.jsonl", rec)
                p0.append_jsonl(st.out / "evaluations.jsonl", ev)
                same = texts(rec) == texts(pilot_recs[(t, arm)])
                rows.append({"task": t, "arm": arm, "identical_to_pilot": same, "solved": ev["solved"], "calls": ev["model_calls"]})
                print(f"[s1a] {t} {arm} identical={same} solved={ev['solved']}", flush=True)
        st.close("completed", {"episodes": len(rows)})
    except BaseException as exc:
        st.close("aborted", {"error": repr(exc), "episodes": len(rows)})
        raise
    identical = all(r["identical_to_pilot"] for r in rows)
    out = {"run_id": st.run_id, "transport": {k: transport[k] for k in ("all_ok", "gpu_full", "api_ps_model")}, "tasks": tasks, "episodes": rows,
           "identical_to_pilot": identical, "reuse_pilot_N_and_Rplus": identical,
           "base_arms_to_run": BASE_ARMS if identical else ["N", "R+"] + BASE_ARMS}
    p0.write_json(XDATA / "s1a.json", out)
    return out


# ----------------------------------------------------------------------------- S1b: lessons, guidance, strata, probe plan

def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def guidance_request(bfcl, tool, pool):
    doc = bfcl.doc(tool)
    history = []
    for row in sorted(pool, key=lambda r: (r["order"], r["turn"])):
        for s in row["steps"]:
            if fn(s["call"]) == tool:
                history.append((row["request"], s["call"], s["result"], not s["error"]))
    history = history[-G_HISTORY:]
    lines = ["You are summarising how a tool behaved in earlier tasks so that an agent can use it better next time.",
             "Tool: " + p0.render_function(doc).splitlines()[0],
             "Description: " + p0.doc_description(doc),
             "Invocation history (oldest first):"]
    for i, (req, call, result, ok) in enumerate(history, 1):
        lines.append(f"{i}. request: {p0.truncate(req, 200)} | call: {call} | result: {p0.truncate(result, 160)} | success: {'true' if ok else 'false'}")
    lines += ["Based on the tool invocation history, write concise and logical usage guidance for this tool in four short parts:",
              "Core function; Success patterns; Common issues; Best practices. Use at most 120 words. State only what the history supports.",
              "Return JSON {\"guidance\": \"<text>\"}."]
    return [{"role": "user", "content": "\n".join(lines)}], len(history)


def build_probe_plan(bfcl, split, g1p):
    mk = p0.load_kernel()
    a_plus = p0.read_jsonl(PDATA / "pools" / "A_plus.jsonl")
    idx = p0.build_index(mk, a_plus)
    in_pool = {p0.pool_row_id(r) for r in a_plus}
    entries = []
    for pid in g1p["ok"]:
        row, b = g1p["entries"][pid], base_id(pid)
        k = row["probe_turn"]
        task = bfcl.probe_tasks[pid]
        r_plus = []
        for ti in range(k + 1):
            rows, _ = p0.retrieve(mk, *idx, task["question"][ti][0]["content"], *p0.UNGATED)
            r_plus.append([p0.pool_row_id(r) for r in rows])
        same_turn = f"{b}:t{k}"
        stratum = "near" if b in split["train"] else "far"
        entries.append({"id": pid, "base_id": b, "probe_turn": k, "stratum": stratum, "config_differs": row["config_differs"],
                        "same_turn_in_pool": same_turn in in_pool, "same_turn_shown": same_turn in r_plus[k],
                        "near_exact": stratum == "near" and same_turn in r_plus[k] and not row["config_differs"],
                        "r_plus": r_plus, "r_plus_items": r_plus[k]})
    counts = {"entries": len(entries), "near": sum(e["stratum"] == "near" for e in entries), "far": sum(e["stratum"] == "far" for e in entries),
              "near_exact": sum(e["near_exact"] for e in entries), "turns_to_run": sum(e["probe_turn"] + 1 for e in entries)}
    return {"domain": "VehicleControlAPI", "system_prompt": "v2", "counts": counts, "entries": entries}


def stage_s1b(cfg, client_factory=None):
    bfcl = bfcl_from_config(cfg)
    split = p0.read_json(PDATA / "split.json")
    pool = p0.read_jsonl(PDATA / "pools" / "A.jsonl")
    if {r["source_task"] for r in pool} - set(split["train"]):
        raise RuntimeError("pool A contains a non-training task")
    lessons, rejected = compile_lessons(pool)
    write_jsonl(XDATA / "lessons.jsonl", lessons)
    p0.write_json(XDATA / "open-problems.json", open_problems(rejected))
    tools = list(dict.fromkeys(l["function"] for l in lessons))
    # strata for the lesson analyses: which test turns need a tool that has a lesson
    l_turns = {}
    for t in split["test"]:
        for ti, turn in enumerate(bfcl.gt[t]):
            l_turns[f"{t}:{ti}"] = any(fn(c) in tools for c in turn)
    p0.write_json(XDATA / "strata-s1.json", {"lesson_tools": tools, "l_turn": l_turns, "l_turns": sum(l_turns.values()),
                                             "l_tasks": sum(any(v for k, v in l_turns.items() if k.rsplit(":", 1)[0] == t) for t in split["test"]),
                                             "mem_layers_from": "data/lab/experience-pilot-v0/strata.json"})
    plan = build_probe_plan(bfcl, split, p0.read_json(XDATA / "g1p.json"))
    p0.write_json(XDATA / "probe-plan.json", plan)
    # arm G: one writer call per tool that has a lesson (SPEC 5.5)
    guidance, writer = {}, []
    if tools:
        st = XStage("s1b", cfg, len(tools), client_factory)
        try:
            st.preflight()
            for tool in tools:
                messages, n_hist = guidance_request(bfcl, tool, pool)
                r = st.client.ask(f"s1b:writer:{tool}", messages, 7, output_schema=G_SCHEMA)
                try:
                    text = json.loads(r["text"])["guidance"]
                except (ValueError, TypeError, KeyError):
                    text = None
                clean = p0.truncate(re.sub(r"\s+", " ", text).strip(), G_CHARS, "…") if isinstance(text, str) and text.strip() else None
                writer.append({"tool": tool, "history_items": n_hist, "raw_text": r["text"], "done_reason": r.get("done_reason"),
                               "guidance": clean, "request_sha256": p0.sha(messages)})
                if clean:
                    guidance[tool] = clean
            st.close("completed", {"writer_calls": len(writer)})
        except BaseException as exc:
            st.close("aborted", {"error": repr(exc)})
            raise
    g_ok = bool(tools) and len(guidance) == len(tools)
    p0.write_json(XDATA / "g-guidance.json", {"tools": tools, "guidance": guidance, "writer": writer, "arm_G_valid": g_ok,
                                              "sha256": p0.sha(guidance)})
    s1a = p0.read_json(XDATA / "s1a.json")
    arms = [a for a in s1a["base_arms_to_run"] if a != "G" or g_ok]
    pilot_calls_per_episode = p0.read_json(PDATA / "results.json")["per_arm"]["N"]["model_calls"] / len(split["test"])
    rem = remaining(cfg)
    proj_c = pilot_calls_per_episode * len(arms) * len(split["test"]) * 1.15
    out = {"lessons": len(lessons), "lesson_tools": tools, "open_problems": len(open_problems(rejected)),
           "lessons_sha256": p0.file_sha(XDATA / "lessons.jsonl"), "arm_G_valid": g_ok, "base_arms": arms,
           "probe_arms": [a for a in PROBE_ARMS if a != "G" or g_ok], "probe_counts": plan["counts"],
           "projection_s1c": {"calls_per_episode": pilot_calls_per_episode, "projected_calls": proj_c, "remaining_calls": rem["calls"],
                              "ok": proj_c <= rem["calls"]},
           "gate_lessons_exist": len(lessons) >= 1}
    p0.write_json(XDATA / "s1b.json", out)
    if not lessons:
        raise SystemExit("STOP: the compiler emitted no lesson")
    return out


# ----------------------------------------------------------------------------- S1c: base tasks, S1d: probe, S1e: ceiling

def load_lessons(name="lessons.jsonl"):
    path = XDATA / name
    return p0.read_jsonl(path), p0.file_sha(path)


def arm_setup(bfcl, arm, *, probe_plan=None):
    """(block provider, tr_lessons) for an arm on base tasks (probe_plan None) or in the probe."""
    if arm in ("N", "N'"):
        return None, None
    if arm == "R+":
        return (rplus_probe_provider(probe_plan) if probe_plan else rplus_base_provider()), None
    if arm == "Tp":
        lessons, sha = load_lessons()
        return lessons_block_provider(bfcl, lessons, sha), None
    if arm == "Tr":
        lessons, _ = load_lessons()
        return None, tr_map(lessons)
    if arm == "G":
        g = p0.read_json(XDATA / "g-guidance.json")
        return guidance_block_provider(bfcl, g["guidance"], g["sha256"]), None
    if arm == "T*":
        lessons, sha = load_lessons("lessons-tstar.jsonl")
        return lessons_block_provider(bfcl, lessons, sha, kind="lessons-tstar (not deployable)"), None
    raise ValueError(arm)


def run_base(cfg, stage, plan, client_factory=None):
    bfcl = bfcl_from_config(cfg)
    setups = {a: arm_setup(bfcl, a) for a in sorted({a for _, a in plan})}
    st = XStage(stage, cfg, remaining(cfg)["calls"], client_factory)
    names = p0.Names(stage + "_" + st.run_id)
    done = 0
    try:
        st.preflight()
        for n, (task_id, arm) in enumerate(plan):
            block, tr = setups[arm]
            rec = run_episode_x(bfcl, bfcl.tasks[task_id], st.client, names, stage=stage, arm=arm, key=f"{stage}:{arm}:{task_id}",
                                ctx_limit=p0.ctx_limit(cfg), block=block, tr_lessons=tr)
            ev = p0.evaluate_episode(bfcl, rec, names)
            p0.append_jsonl(st.out / "episodes.jsonl", rec)
            p0.append_jsonl(st.out / "evaluations.jsonl", ev)
            done += 1
            print(f"[{stage}] {n + 1}/{len(plan)} {task_id} {arm} solved={ev['solved']} status={ev['status']} calls={ev['model_calls']}", flush=True)
        st.close("completed", {"episodes": done})
    except BaseException as exc:
        st.close("aborted", {"error": repr(exc), "episodes": done})
        raise
    return {"run_id": st.run_id, "episodes": done}


def s1c_plan(test, arms):
    plan = []
    for i, t in enumerate(test):
        order = list(arms)
        random.Random(SEED + i).shuffle(order)
        plan.extend((t, a) for a in order)
    return plan


def stage_s1c(cfg, client_factory=None):
    s1b = p0.read_json(XDATA / "s1b.json")
    if not s1b["projection_s1c"]["ok"]:
        raise SystemExit("STOP: S1c projection exceeds the remaining S1 budget")
    split = p0.read_json(PDATA / "split.json")
    return run_base(cfg, "s1c", s1c_plan(split["test"], s1b["base_arms"]), client_factory)


def s1d_plan(entries, arms):
    plan = []
    for e in sorted(entries, key=lambda e: task_number(e["id"])):
        order = list(arms)
        random.Random(SEED + 1000 + task_number(e["id"])).shuffle(order)
        plan.extend((e, a) for a in order)
    return plan


def calls_per_turn_measured():
    evs = p0.read_jsonl(latest_completed("s1c") / "evaluations.jsonl")
    return sum(e["model_calls"] for e in evs) / max(1, sum(e["turns_started"] for e in evs))


def stage_s1d(cfg, client_factory=None):
    bfcl = bfcl_from_config(cfg)
    s1b = p0.read_json(XDATA / "s1b.json")
    plan_file = p0.read_json(XDATA / "probe-plan.json")
    arms = s1b["probe_arms"]
    rem = remaining(cfg)
    proj = calls_per_turn_measured() * plan_file["counts"]["turns_to_run"] * len(arms) * 1.15
    p0.write_json(XDATA / "s1d-projection.json", {"projected_calls": proj, "remaining_calls": rem["calls"], "ok": proj <= rem["calls"]})
    if proj > rem["calls"]:
        raise SystemExit("STOP: S1d projection exceeds the remaining S1 budget")
    setups = {a: arm_setup(bfcl, a, probe_plan=plan_file) for a in arms}
    plan = s1d_plan(plan_file["entries"], arms)
    st = XStage("s1d", cfg, rem["calls"], client_factory)
    names = p0.Names("s1d_" + st.run_id)
    done = 0
    try:
        st.preflight()
        for n, (entry, arm) in enumerate(plan):
            block, tr = setups[arm]
            task = bfcl.probe_tasks[entry["id"]]
            rec = run_episode_x(bfcl, task, st.client, names, stage="s1d", arm=arm, key=f"s1d:{arm}:{entry['id']}", ctx_limit=p0.ctx_limit(cfg),
                                system_template=SYSTEM_V2, block=block, tr_lessons=tr, stop_after_turn=entry["probe_turn"])
            ev = evaluate_probe(bfcl, rec, names, entry["probe_turn"])
            p0.append_jsonl(st.out / "episodes.jsonl", rec)
            p0.append_jsonl(st.out / "evaluations.jsonl", ev)
            done += 1
            print(f"[s1d] {n + 1}/{len(plan)} {entry['id']} {arm} reached={ev['reached']} proposed={ev['proposed']} calls={ev['model_calls']}", flush=True)
        st.close("completed", {"episodes": done})
    except BaseException as exc:
        st.close("aborted", {"error": repr(exc), "episodes": done})
        raise
    return {"run_id": st.run_id, "episodes": done}


def build_tstar(cfg):
    """Ceiling lessons (SPEC 5.6): pool A plus arm N's own traces on the test tasks, support of one task. Not deployable."""
    split = p0.read_json(PDATA / "split.json")
    pool = p0.read_jsonl(PDATA / "pools" / "A.jsonl")
    recs, evs = pilot_episodes()
    s1a = p0.read_json(XDATA / "s1a.json")
    if not s1a["reuse_pilot_N_and_Rplus"]:
        run = latest_completed("s1c")
        recs = {(r["task"], r["arm"]): r for r in p0.read_jsonl(run / "episodes.jsonl")}
        evs = {(e["task"], e["arm"]): e for e in p0.read_jsonl(run / "evaluations.jsonl")}
    extra = [row for i, t in enumerate(split["test"]) for row in p0.pool_rows_from_episode(recs[(t, "N")], evs[(t, "N")], 1000 + i)]
    lessons, rejected = compile_lessons(pool + extra, min_tasks=1)
    write_jsonl(XDATA / "lessons-tstar.jsonl", lessons)
    return {"lessons": len(lessons), "sha256": p0.file_sha(XDATA / "lessons-tstar.jsonl")}


def stage_s1e(cfg, client_factory=None):
    split = p0.read_json(PDATA / "split.json")
    info = build_tstar(cfg)
    rem = remaining(cfg)
    proj = p0.read_json(XDATA / "s1b.json")["projection_s1c"]["calls_per_episode"] * len(split["test"]) * 1.2
    if proj > rem["calls"]:
        raise SystemExit("STOP: no reserve for T*")
    out = run_base(cfg, "s1e", [(t, "T*") for t in split["test"]], client_factory)
    out["tstar"] = info
    return out


def stage_freeze(cfg):
    base = XWORK / "raw"
    files = {p.relative_to(base).as_posix(): p0.file_sha(p) for p in sorted(base.rglob("*")) if p.is_file()}
    out = {"frozen_at": p0.now_iso(), "raw_root": "experience-transfer-2026-11-12/raw (outside Git)", "files": files, "ledger": ledger()}
    p0.write_json(XDATA / "raw-freeze.json", out)
    return {"files": len(files), "calls": out["ledger"]["calls"]}


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["s0", "s1a", "s1b", "s1c", "s1d", "s1e", "freeze", "analyze", "ledger"])
    a = p.parse_args(argv)
    cfg = load_config()
    if a.stage == "ledger":
        print(json.dumps({**ledger(), "remaining": remaining(cfg)}, indent=2))
        return
    if a.stage == "analyze":
        import experience_xfer_v1_analysis as an
        an.main(cfg)
        return
    stage_fn = {"s0": stage_s0, "s1a": stage_s1a, "s1b": stage_s1b, "s1c": stage_s1c, "s1d": stage_s1d, "s1e": stage_s1e,
                "freeze": stage_freeze}[a.stage]
    out = stage_fn(cfg)
    print(json.dumps(out, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
