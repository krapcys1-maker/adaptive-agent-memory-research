"""AAMR-K1 executor: shared paths and helpers (arms N, P, X, S, M; spec K1 v0.4).

Built on the N/M pilot code (D:/aamr-audit-2026-11-13/pilot-nm/code, read-only reference). Standard library only at import
time: the audit hook must be installed before any harness import, so this module imports no harness code until a function
asks for it. NIGHT-1/NIGHT-2 code and data are used read-only. TradingBot (ids 100-149) is rejected by id before parsing and
the harness guard (xv.guard_task) stays active.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]                 # D:/aamr-k1-executor
CODE = ROOT / "code"
CONFIG = CODE / "k1_config.json"
MATERIALS = ROOT / "materials"
CORPUS_SOURCE = MATERIALS / "corpus_P_source.txt"
GH = Path("D:/Pamiec LLM/GH_REVIVAL")
SCRIPTS = GH / "aamr-night2-worktree" / "scripts"
NRUN = GH / "aamr-night2-2026-11-13" / "run"
NRESP = NRUN / "responses.jsonl"
BFCL = GH / "experience-pilot-2026-11-12" / "bfcl" / "src" / "berkeley-function-call-leaderboard"
DATA = BFCL / "bfcl_eval" / "data"
TASKS_FILE = DATA / "BFCL_v4_multi_turn_base.json"
GOLD = DATA / "possible_answer" / "BFCL_v4_multi_turn_base.json"
DOCS = ["gorilla_file_system", "math_api", "message_api", "posting_api", "ticket_api", "vehicle_control", "travel_booking"]
DOC_FILES = [DATA / "multi_turn_func_doc" / f"{d}.json" for d in DOCS]
OLLAMA_APP = Path(os.environ.get("LOCALAPPDATA", "C:/Users/user/AppData/Local")) / "Programs" / "Ollama" / "ollama app.exe"
OLLAMA_ADDR = ("127.0.0.1", 11434)
DOMAINS = ("VC", "GFS", "TRAVEL")
ARMS5 = ("N", "P", "X", "S", "M")
SAMPLED = ("S1", "S2", "S3")
NIGHT2_M_ARM = {"E3": "E*", "E1": "R+"}                    # NIGHT-2 arm whose stimulus is K1's M
HEADER = "EXPERIENCE FROM EARLIER TASKS (it may or may not be relevant; use it only if it helps):"
TASK_RE = re.compile(r"multi_turn_base_(\d+)")
WORD = re.compile(r"[A-Za-z]+")
EXIT_DONE, EXIT_FATAL, EXIT_TRANSIENT, EXIT_GATE, EXIT_PREFLIGHT, EXIT_HOOK = 0, 2, 3, 4, 5, 97
EXIT_BLOCK_ABORT = 6                                         # second non-transient error inside a sampled block
# supervisor exit codes seen by the coordinator wrapper: 0 done, 3 stop (owner decision), 4 gate stop (owner decision)
SUP_STOP, SUP_GATE = 3, 4


def layout(base: Path) -> dict:
    base = Path(base)
    return {"base": base, "stim": base / "stim", "run": base / "run", "eval": base / "eval", "meta": base / "meta",
            "report": base / "report", "out": base / "out"}


def load_cfg(path: Path = CONFIG) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_obj(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def not_trading(line: str) -> bool:
    ids = [int(x) for x in TASK_RE.findall(line)]
    return bool(ids) and all(not (100 <= i < 150) for i in ids)


def rows(path: Path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not_trading(line):
                yield json.loads(line)


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, o, indent=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(o, sort_keys=True, indent=indent, ensure_ascii=False, default=float), encoding="utf-8")
    os.replace(tmp, p)


# ----------------------------------------------------------------------------- audit-hook policies (spec sec. 5, L6a)

def worker_policy(L: dict, extra_read=(), config=CONFIG) -> dict:
    stim = sorted(L["stim"].glob("*.json")) if L["stim"].exists() else []
    return {"read_files": [TASKS_FILE, Path(config)] + DOC_FILES + stim + list(extra_read),
            "code_roots": [sys.base_prefix, sys.prefix, SCRIPTS, BFCL, CODE],
            "run_dirs": [L["run"]], "spawn_allow": [OLLAMA_APP], "net_allow": [OLLAMA_ADDR]}


def import_harness():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    n2 = importlib.import_module("aamr_night2")
    return n2, n2.p0, n2.xv, n2.n1


def make_bfcl_k1(p0, xv, n1):
    """n1.BfclN without either ground-truth file (p0.Bfcl line 122, BfclX probe_gt) and without probe tasks (W2/D11).
    Identical to the pilot's BfclK1 (pilot_lib.make_bfcl_k1)."""

    class BfclK1(n1.BfclN):
        def __init__(self, root: Path):                      # deliberately does not call super().__init__
            self.root = Path(root)
            if str(self.root) not in sys.path:
                sys.path.insert(0, str(self.root))
            self.utils = importlib.import_module("bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils")
            self.checker = importlib.import_module("bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker")
            self.backend = importlib.import_module("bfcl_eval.constants.executable_backend_config")
            data = self.root / "bfcl_eval/data"
            self.tasks = {r["id"]: r for r in p0.read_jsonl(data / "BFCL_v4_multi_turn_base.json")}
            self.docs = {c: p0.read_jsonl(data / "multi_turn_func_doc" / f) for c, f in p0.FUNC_DOC_FILES.items()}
            self.signatures = {}
            for cls in p0.FUNC_DOC_FILES:
                module = importlib.import_module(self.backend.CLASS_FILE_PATH_MAPPING[cls])
                for name, fn in inspect.getmembers(getattr(module, cls), predicate=inspect.isfunction):
                    if not name.startswith("_"):
                        self.signatures[name] = [p for p in inspect.signature(fn).parameters if p != "self"]
            self.docs["TravelAPI"] = p0.read_jsonl(data / "multi_turn_func_doc" / "travel_booking.json")
            klass = getattr(importlib.import_module(self.backend.CLASS_FILE_PATH_MAPPING["TravelAPI"]), "TravelAPI")
            for name, f in inspect.getmembers(klass, predicate=inspect.isfunction):
                if not name.startswith("_"):
                    self.signatures[name] = [p for p in inspect.signature(f).parameters if p != "self"]
            for t in self.tasks.values():
                if "TradingBot" in t["involved_classes"] and not 100 <= xv.task_number(t["id"]) <= 149:
                    raise RuntimeError("TradingBot outside the reserve block")

        @property
        def gt(self):
            raise RuntimeError("episode process has no ground truth")

        @property
        def probe_gt(self):
            raise RuntimeError("episode process has no ground truth")

    return BfclK1


# ----------------------------------------------------------------------------- tasks, plans, blocks

def task_index(tasks: dict) -> dict:
    """task -> (set, domain, part) with set E3 (test) / E1 (train) as in NIGHT-2."""
    out = {}
    for d in DOMAINS:
        for t in tasks[d]["test"]:
            out[t] = ("E3", d, "test")
        for t in tasks[d]["train"]:
            out[t] = ("E1", d, "train")
    return out


def plan_turns(plans: dict, idx: dict) -> dict:
    """task -> {turn index: [trace ids]} of the M plan (all turns of the task, empty lists included)."""
    out = {}
    for t, (_, d, part) in idx.items():
        out[t] = {}
    for part in ("test", "train"):
        for d in DOMAINS:
            for k, ids in plans[part][d].items():
                t, ti = k.rsplit(":", 1)
                if t in out:
                    out[t][int(ti)] = list(ids)
    return out


def content(block: str) -> str:
    if not block:
        return ""
    if not block.startswith(HEADER + "\n"):
        raise ValueError("block without the memory header")
    return block[len(HEADER) + 1:]


def build_p(m_block: str, corpus: list, c: float, seed) -> str:
    """P block (spec sec. 2, P), identical to the W8 prototype (k1/v0.4/testy/t_w8_p_length.py: build_p)."""
    if not m_block:
        return ""
    target = round(c * len(content(m_block)))
    rng = random.Random(repr(seed))
    order = list(range(len(corpus)))
    rng.shuffle(order)
    out, k = "", 0
    while True:
        s = corpus[order[k % len(order)]]
        k += 1
        cand = (out + " " + s) if out else s
        if len(cand) <= target:
            out = cand
            if len(out) == target:
                break
            continue
        best = cand
        words = s.rstrip(".").split(" ")
        for j in range(1, len(words)):
            piece = " ".join(words[:j]) + "."
            alt = (out + " " + piece) if out else piece
            if abs(len(alt) - target) < abs(len(best) - target):
                best = alt
        if out and abs(len(out) - target) <= abs(len(best) - target):
            best = out
        out = best
        break
    return HEADER + "\n" + out


def p_seed(task: str, ti: int, inst) -> tuple:
    return (task, ti, inst)


def matched_draw(rng_key: str, cand_pool: list, k: int, target_tok: float, rho: float, cchars, used=None,
                 attempts: int = 200, tol: float = 0.2):
    """D12 (length-matched draw), identical to the prototype in k1/v0.4/testy/t_d9_length.py (matched): up to `attempts`
    seeded draws of k traces; the first whose predicted tokens are within +-tol (log scale) of the M block of the turn is
    taken, else the closest. used: traces already shown to this task (S: no repeats while enough remain)."""
    TOL = math.log(1 + tol)
    best, bestv = None, None
    for att in range(attempts):
        r = random.Random(f"{rng_key}|{att}")
        cand = [i for i in cand_pool if not used or i not in used]
        pick = r.sample(cand if len(cand) >= k else cand_pool, k)
        v = abs(math.log(max(1, cchars(pick)) * rho / target_tok))
        if v <= TOL:
            return pick, att, v
        if bestv is None or v < bestv:
            best, bestv = pick, v
    return best, attempts, bestv


def unmatched_draw(rng, cand_pool, k, used=None):
    """v0.4 before D12: count only (used by the NOT-APPROVED variant switch d12.enabled=false and in tests)."""
    cand = [i for i in cand_pool if not used or i not in used]
    return rng.sample(cand if len(cand) >= k else cand_pool, k)


def make_providers(n2, p0, stim: Path, c_d: dict | None = None) -> dict:
    """Block providers per arm: arm -> callable(instance) -> {part: {domain: block(task, ti, request)}}.
    M: NIGHT-2 plan_provider (presentation R+) on the extracted, provenance-checked plans and pools (as the pilot).
    X, S: frozen draws (stim/k1_draws_SX.json), rendered with p0.render_block like M.
    P: neutral prose built from the frozen corpus with c_d of the task's domain (needs c_d from stage T)."""
    plans = read_json(stim / "k1_plans_M.json")
    pools = {d: read_json(stim / f"k1_pool_{d}.json") for d in DOMAINS}
    by_id = {p0.pool_row_id(r): r for d in DOMAINS for r in pools[d]}
    mprov = {part: {d: n2.plan_provider(plans[part][d], {p0.pool_row_id(r): r for r in pools[d]}, "R+",
                                        {"pool": f"{d} A+", "pool_sha256": p0.sha(pools[d])}) for d in DOMAINS}
             for part in ("test", "train")}
    draws = read_json(stim / "k1_draws_SX.json") if (stim / "k1_draws_SX.json").exists() else None
    corpus = read_json(stim / "k1_corpus_P.json")["sentences"] if (stim / "k1_corpus_P.json").exists() else None

    def m_text(part, d, task, ti, request):
        return mprov[part][d](task, ti, request)[0]

    def trace_arm(arm, inst):
        def mk(part, d):
            def block(task, ti, request):
                ids = draws[arm][str(inst)].get(f"{task}:{ti}", [])
                return p0.render_block([by_id[i] for i in ids]), list(ids), {"arm": arm, "instance": inst,
                                                                            "draws_sha256": draws["sha256"][arm]}
            return block
        return {part: {d: mk(part, d) for d in DOMAINS} for part in ("test", "train")}

    def p_arm(inst):
        if c_d is None:
            raise RuntimeError("P needs c_d from stage T")

        def mk(part, d):
            def block(task, ti, request):
                text = build_p(m_text(part, d, task, ti, request), corpus, c_d[d], p_seed(task, ti, inst))
                return text, [], {"arm": "P", "instance": inst, "c_d": c_d[d]}
            return block
        return {part: {d: mk(part, d) for d in DOMAINS} for part in ("test", "train")}

    return {"M": lambda inst: mprov, "X": lambda inst: trace_arm("X", inst), "S": lambda inst: trace_arm("S", inst),
            "P": p_arm, "N": lambda inst: None, "_m_text": m_text, "_by_id": by_id}


def block_plan(block: str, task_list: list, arms: list) -> list:
    """Every (task, arm) of a block; order of tasks and of arms within a task randomised with a fixed seed per block."""
    rng = random.Random(f"K1|{block}|order")
    ts = sorted(task_list)
    rng.shuffle(ts)
    out = []
    for t in ts:
        a = list(arms)
        random.Random(f"K1|{block}|{t}|arms").shuffle(a)
        out += [(t, x) for x in a]
    return out


def episode_calls(rec) -> int:
    return sum(1 for tu in rec["turns"] for s in tu["steps"] if "key" in s)


# ----------------------------------------------------------------------------- budget gates (spec sec. 10, D10)

def projections(m: float, cfg: dict) -> tuple:
    na = 148 * len(cfg["blocks"]["A"]["arms"])
    ns = 148 * len(cfg["blocks"]["S1"]["arms"])
    return math.ceil(cfg["margin"] * m * na), math.ceil(cfg["margin"] * m * ns)


def gate_before_a(used: int, m: float, cfg: dict) -> dict:
    pa, ps = projections(m, cfg)
    return {"m": m, "P_A": pa, "P_S": ps, "used": used, "need": pa + 2 * ps, "go": used + pa + 2 * ps <= cfg["hard_limit"]}


def gate_before_s(used: int, m: float, cfg: dict) -> dict:
    _, ps = projections(m, cfg)
    return {"m": m, "P_S": ps, "used": used, "need": ps, "go": used + ps <= cfg["hard_limit"]}


# ----------------------------------------------------------------------------- provenance L10 (spec sec. 2, 5)

def check_g1_rows(pools: dict, tasks: dict, pool_row_id) -> list:
    """G1 row conditions: origin 'A', label PASSED, source task in the training set of the pool's domain."""
    bad = [f"G1 {d} {pool_row_id(r)}" for d, rws in pools.items() for r in rws
           if r.get("origin") != "A" or r.get("label") != "PASSED" or r["source_task"] not in tasks[d]["train"]]
    if not any(pools.values()):
        bad.append("G1 empty comparison")
    return bad


def check_g2_plans(plans: dict, rebuilt: dict) -> tuple:
    """G2: extracted plans equal to the plans rebuilt under the hook from gold-free inputs; empty comparison fails."""
    bad, nkeys = [], 0
    for part in ("test", "train"):
        for d in DOMAINS:
            a_, b_ = plans.get(part, {}).get(d, {}), rebuilt.get(part, {}).get(d, {})
            nkeys += len(a_)
            if not a_ or a_ != b_:
                bad.append(f"G2 {part}/{d}: {sum(a_.get(k) != b_.get(k) for k in set(a_) | set(b_))} mismatching keys")
    return bad, nkeys


# ----------------------------------------------------------------------------- leak checks (spec sec. 5)

def check_l1(arm_ids: dict, idx: dict, src_of: dict, train_tasks: set) -> tuple:
    """L1 on one arm: arm_ids task -> {ti: ids}. Stops on: a trace from the current task; a trace whose source is not a
    training task (for test tasks this is the spec's condition; for training tasks the pools hold only training tasks);
    an unknown trace id; zero checked sources. Returns (violations, checked)."""
    bad, checked = [], 0
    for t, turns in arm_ids.items():
        for ti, ids in turns.items():
            for i in ids:
                s = src_of.get(i)
                checked += 1
                if s is None:
                    bad.append(f"{t}:{ti} unknown trace {i}")
                elif s == t:
                    bad.append(f"{t}:{ti} own-task trace {i}")
                elif s not in train_tasks:
                    bad.append(f"{t}:{ti} trace {i} from a non-training task")
    if checked == 0:
        bad.append("zero checked sources")
    return bad, checked


def check_l3(s_ids: dict, m_ids: dict, src_of: dict) -> list:
    """L3 on one S draw: shares a trace with M of the task (any turn); trace from the own task; other count than M."""
    bad = []
    for t, turns in m_ids.items():
        mine = {i for ids in turns.values() for i in ids}
        st = s_ids.get(t, {})
        for ti, ids in turns.items():
            got = st.get(ti, [])
            if len(got) != len(ids):
                bad.append(f"{t}:{ti} count {len(got)} != M {len(ids)}")
            for i in got:
                if i in mine:
                    bad.append(f"{t}:{ti} trace {i} shared with M")
                if src_of.get(i) == t:
                    bad.append(f"{t}:{ti} own-task trace {i}")
    if not m_ids:
        bad.append("empty scope")
    return bad


def content_words(text: str, function_words) -> set:
    return {w.lower() for w in WORD.findall(text) if len(w) >= 3 and w.lower() not in function_words}


def l4b(p_block: str, request: str, function_words) -> float:
    a, b = content_words(content(p_block), function_words), content_words(request, function_words)
    return len(a & b) / len(a | b) if (a | b) else 0.0


# ----------------------------------------------------------------------------- owner approvals (real-model gate)

def approval_problems(cfg: dict) -> list:
    """Every decision D1-D12 approved, technical choices approved, the executor's spec copy equal to spec_frozen_sha256 and the
    FREEZE.json copy next to it equal to spec_freeze_json_sha256 (when set), and that FREEZE.json naming the same spec sha."""
    missing = [f"{k} ({v.get('status')})" for k, v in cfg["decisions"].items() if not str(v.get("status", "")).startswith("approved")]
    if cfg.get("technical_choices_approved") is not True:
        missing.append("technical choices T1-T12 not approved (technical_choices_approved)")
    spec = Path(cfg["spec"])
    if not cfg.get("spec_frozen_sha256"):
        missing.append("spec not frozen (spec_frozen_sha256 is null)")
    elif not spec.exists() or sha_file(spec) != cfg["spec_frozen_sha256"]:
        missing.append("spec file differs from spec_frozen_sha256")
    if cfg.get("spec_freeze_json_sha256"):
        fz = spec.parent / "FREEZE.json"
        if not fz.exists() or sha_file(fz) != cfg["spec_freeze_json_sha256"]:
            missing.append("FREEZE.json copy differs from spec_freeze_json_sha256")
        elif read_json(fz).get("spec_sha256") != cfg.get("spec_frozen_sha256"):
            missing.append("FREEZE.json names another spec sha256")
    return missing


# ----------------------------------------------------------------------------- L8 manifest

def manifest_files(L: dict, config: Path = CONFIG) -> list:
    spec = Path(load_cfg(config)["spec"])
    return (sorted(L["stim"].glob("*.json")) + sorted(CODE.glob("*.py")) + [Path(config), CORPUS_SOURCE, spec])


def verify_manifest(L: dict) -> list:
    """L8: stimuli, code, config, corpus source and spec unchanged since preparation. Returns differences."""
    p = L["meta"] / "MANIFEST.json"
    if not p.exists():
        return ["MANIFEST.json missing"]
    man = read_json(p)
    res = lambda f: Path(f) if Path(f).is_absolute() else L["base"] / f
    diff = [f for f, h in man["files"].items() if not res(f).exists() or sha_file(res(f)) != h]
    now = {f"stim/{q.name}" for q in sorted(L["stim"].glob("*.json"))} | {str(f) for f in CODE.glob("*.py")}
    diff += sorted(now - set(man["files"]))
    diff += [f for f, h in man["startup_files_before_hook"].items() if not Path(f).exists() or sha_file(Path(f)) != h]
    return diff
