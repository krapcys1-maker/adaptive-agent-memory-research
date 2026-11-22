"""Placebo check: one volunteer cell = one frozen block of 20 games × the arms none, placebo, retrieved_task.

Why: in the lab's V3 run (100 valid_seen games, min_tokens not set), a token-matched placebo block raised the solve
rate by 13 points over no memory, and in the same run it almost removed empty answers (the model ending its answer
at once). In V4 (300 train games, min_tokens = 8, no game shared with V3) there were no empty answers and placebo and
no memory were equivalent. How much of the V3 13 points came from the empty-answer artefact is a hypothesis. A cell
checks on other hardware and software whether these effects appear, and two cells on the same block with
`--min-tokens 0` and `--min-tokens 8` are the direct test of the decoding hypothesis on those games.

Steps (inside the environment with alfworld, textworld and a vLLM server for the model on port 8001):

    python placebo_check.py prepare --pool v4 --block B03 --replicate 1          # writes data/contrib/<cell-id>/
    python placebo_check.py run data/contrib/<cell-id>                           # archive check, then all episodes (GPU)
    python placebo_check.py finish data/contrib/<cell-id>                        # fills the card, checks the records

`run` first checks every scheduled game's game.tw-pddl against the pinned archive manifest and starts nothing if one
is missing, unknown or changed. It writes a receipt to the card. `finish` accepts only records written by such runs.
    python placebo_check.py summary data/contrib/<cell-id>                       # prints the comparison, writes per_unit.csv

`--min-tokens 0` re-creates the V3 decoding condition on train games (not the V3 games); run it as a second cell
on the same block to compare. `--format-reminder 0` (the default) keeps the V3/V4 prompts; `1` adds the V5
one-line format reminder to every arm and makes the cell a V5-prompt cell, not a V3/V4 replication.
The model is the one the agent will use (`LADDER_MODEL`, default Qwen/Qwen3-4B-Instruct-2507-FP8); the card records
it, the prompt hash and the format reminder, and `run` passes them to the agent.

The cell id is placebo-<pool>-<block>-r<replicate>-mt<min_tokens>-fr<format_reminder>. When the model or the prompt
text differs from V3/V4, `-x<8 hex>` (a digest of model and prompt) is appended, so such a cell can never be
mistaken for a replication. Claim the block on the cell board first.
Never add valid_unseen games: prepare refuses any game outside the frozen pools.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CONTRIB_ROOT = os.environ.get("AAMR_CONTRIB_ROOT", os.path.join(REPO, "data", "contrib"))
POOLS = os.path.join(HERE, "contrib", "pools.json")
ARMS = ["none", "placebo", "retrieved_task"]
PROMPT_TEMPLATE = os.path.join(HERE, "instrument", "prompt_template.txt")
FIXED_FILES = {"agent": os.path.join(HERE, "agent.py"), "placebo": os.path.join(HERE, "instrument", "placebo.txt"),
               "bank": os.path.join(HERE, "data", "bank.jsonl"), "prompt_template": PROMPT_TEMPLATE}

# The configuration the lab's V3 and V4 programs measured (their knowledge.jsonl pins).
V3V4_MODEL = "Qwen/Qwen3-4B-Instruct-2507-FP8"
V3V4_PROMPT_TEMPLATE_SHA256 = "e1d94a682d38c95d47e0341adb2c66048509dcfbfb1d5a7f07d4d2828b0424ff"
# The ALFWorld game archive a cell runs on. A profile is chosen at prepare, recorded on the card and verified before
# any episode starts: every scheduled game's game.tw-pddl (the only per-game file agent.py loads) must have the
# SHA-256 that the profile's trusted manifest lists, and the manifest itself must have the canonical digest pinned
# here. Unknown, missing or changed bytes block the run in every profile. Only `reference` (json_2.1.2_tw-pddl.zip,
# ALFWorld release 0.4.0, fetched by alfworld-download from ALFWorld 0.4.2, extracted into json_2.1.1/; see
# tools/alfworld_ladder/v5b/SETUP_SAME.md) has a pinned manifest. The older json_2.1.1 archive is a declared
# sensitivity profile without a pinned manifest, so it cannot be prepared or run yet
# (docs/research-map/VOLUNTEER_COMPUTE.md).
REFERENCE_PROFILE = "reference"
ARCHIVE_PROFILES = {
    "reference": {"class": "primary", "archive": "json_2.1.2_tw-pddl.zip",
                  "manifest": os.path.join(HERE, "contrib", "archive_manifest_reference.json"),
                  "games_canonical_sha256": "643701c5bb9683c6b3ccc7007d52dc423ee6793eb5eed1d95fc0399276bc240e"},
    "older-json_2.1.1": {"class": "sensitivity", "archive": "json_2.1.1_tw-pddl.zip", "manifest": None,
                         "games_canonical_sha256": None},
}
ARCHIVE_DIGEST_TYPE = "SHA-256 of game.tw-pddl, per scheduled game, against the profile's pinned manifest"
# The sentinel game of SETUP_SAME.md; the reference manifest lists the same digest for it.
ARCHIVE_CHECK_GAME = "train/pick_and_place_simple-CellPhone-None-Safe-302/trial_T20190908_122757_136508"
ARCHIVE_CHECK_SHA256 = "86059504faa14bd6a04b7443f3779c240e2eedbcf673e0282795cdee29497b53"
DEFAULT_DATA_ROOT_REL = "~/test-a-feasibility/alfworld_data/json_2.1.1"
# Cells published before the archive preflight existed: their cards carry no archive policy and no receipt. finish
# labels them as historical evidence; any other card without an archive policy is invalid.
HISTORICAL_CELLS = frozenset({"placebo-v4-B03-r1-mt0-fr0"})
# The prompt pieces agent.py sends, in the order instrument/prompt_template.txt documents them.
TEMPLATE_SECTIONS = ("TEMPLATE_NO_HIS", "TEMPLATE", "ACTION_INSTR", "MEMORY_WRAPPER")
# Settings every record must share with the card (agent.py writes them into metrics).
CHECKED_SETTINGS = ("model", "min_tokens", "format_reminder", "temperature", "max_tokens", "max_steps")


class CellError(ValueError):
    """The records do not match the card: the cell cannot be summarised."""


def sha_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_agent(format_reminder: bool | None = None):
    """Import agent.py as the runner will see it, so the card's settings come from the agent's own CFG.

    ``format_reminder`` sets LADDER_FORMAT_REMINDER for the import, as ``run`` does for the agent process.
    """
    saved = os.environ.get("LADDER_FORMAT_REMINDER")
    if format_reminder is not None:
        os.environ["LADDER_FORMAT_REMINDER"] = "1" if format_reminder else "0"
    try:
        spec = importlib.util.spec_from_file_location("placebo_check_agent", FIXED_FILES["agent"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if format_reminder is not None:
            if saved is None:
                os.environ.pop("LADDER_FORMAT_REMINDER", None)
            else:
                os.environ["LADDER_FORMAT_REMINDER"] = saved
    return module


def template_sections(text: str) -> dict:
    """The '## NAME' sections of instrument/prompt_template.txt, each stripped of surrounding blank lines."""
    out, name, lines = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if name:
                out[name] = "\n".join(lines).strip()
            name, lines = line[3:].strip(), []
        elif name:
            lines.append(line)
    if name:
        out[name] = "\n".join(lines).strip()
    return out


def prompt_config(agent, format_reminder: bool) -> dict:
    """What the agent's prompt text is, and whether it equals the V3/V4 template."""
    pieces = [getattr(agent, n) for n in TEMPLATE_SECTIONS] + [agent.FORMAT_REMINDER if format_reminder else ""]
    with open(PROMPT_TEMPLATE, encoding="utf-8") as f:
        sections = template_sections(f.read())
    same = all(sections.get(n) == getattr(agent, n).strip() for n in TEMPLATE_SECTIONS)
    template_sha = sha_file(PROMPT_TEMPLATE)
    return {"prompt_sha256": hashlib.sha256(json.dumps(pieces).encode()).hexdigest(),
            "prompt_template_sha256": template_sha,
            "agent_prompts_match_template": same,
            "prompts_match_v3_v4": same and not format_reminder and template_sha == V3V4_PROMPT_TEMPLATE_SHA256}


def cell_id(pool: str, block: str, rep: int, mt: int, fr: bool, model: str, prompt: dict) -> str:
    cid = f"placebo-{pool}-{block}-r{rep}-mt{mt}-fr{int(fr)}"
    reference = (model == V3V4_MODEL and prompt["agent_prompts_match_template"]
                 and prompt["prompt_template_sha256"] == V3V4_PROMPT_TEMPLATE_SHA256)
    if not reference:
        tag = hashlib.sha256(json.dumps({"model": model, "prompt_sha256": prompt["prompt_sha256"]}).encode())
        cid += "-x" + tag.hexdigest()[:8]
    return cid


def cmd_prepare(a) -> None:
    pools = json.load(open(POOLS, encoding="utf-8"))
    if a.pool not in pools or a.block not in pools[a.pool]["blocks"]:
        sys.exit(f"unknown pool/block {a.pool}/{a.block}; see {POOLS}")
    games = pools[a.pool]["blocks"][a.block]
    if any(not g.startswith("train/") for g in games):
        sys.exit("refusing: a block game is outside train")
    arms = ARMS + (["mismatched_type"] if a.with_mismatched else [])
    profile = ARCHIVE_PROFILES.get(a.archive_profile)
    if profile is None:
        sys.exit(f"unknown archive profile {a.archive_profile}; known: {sorted(ARCHIVE_PROFILES)}")
    if not profile["manifest"] or not profile["games_canonical_sha256"]:
        sys.exit(f"refusing: archive profile {a.archive_profile} has no pinned manifest in this repository, so its "
                 "bytes cannot be verified before a run; only the reference profile can be prepared")
    try:
        manifest = load_manifest(a.archive_profile)
    except CellError as e:
        sys.exit(str(e))
    if any(g not in manifest for g in games):
        sys.exit(f"refusing: a block game is not in the {a.archive_profile} archive manifest")
    fr = bool(a.format_reminder)
    agent = load_agent(fr)
    cfg = agent.CFG
    prompt = prompt_config(agent, fr)
    cid = cell_id(a.pool, a.block, a.replicate, a.min_tokens, fr, cfg["model"], prompt)
    if a.with_mismatched:
        cid += "-mis"
    if a.archive_profile != REFERENCE_PROFILE:
        cid += "-a" + a.archive_profile  # a non-reference archive is never pooled with reference cells
    d = os.path.join(CONTRIB_ROOT, cid)
    if os.path.exists(os.path.join(d, "records.jsonl")):
        sys.exit(f"{d} already has records; use a new replicate number")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "batch.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for g in games:
            for arm in arms:  # all arms of a game side by side: they share machine state and load
                f.write(json.dumps({"unit": f"{cid}~{g}", "task": g, "arm": arm, "seed": a.replicate}) + "\n")
    try:
        commit = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    replication = cfg["model"] == V3V4_MODEL and prompt["prompts_match_v3_v4"]
    card = {
        "cell_id": cid, "pool": a.pool, "block": a.block, "replicate": a.replicate, "games": games,
        "pool_games_sha256": pools[a.pool]["games_sha256"],
        "block_games_sha256": hashlib.sha256(json.dumps(sorted(games)).encode()).hexdigest(),
        "pools_file_sha256": sha_file(POOLS), "arms": arms,
        "fixed": {"model": cfg["model"], "temperature": cfg["temperature"], "max_tokens": cfg["max_tokens"],
                  "min_tokens": a.min_tokens, "format_reminder": fr, "max_steps": cfg["max_steps"],
                  "history_length": cfg["history_length"], "k": cfg["k"], "prompt": prompt,
                  "sha256": {k: sha_file(p) for k, p in FIXED_FILES.items()}, "harness_commit": commit},
        "replication": ("V3/V4 setup (model and prompts); min_tokens as chosen" if replication else
                        "conceptual: model or prompts differ from V3/V4; analysed separately"),
        "agent_note": ("agent.py is the current public runner, not the V4 agent pin (68f48c2f, unpublished). "
                       "With format_reminder off its prompt text equals instrument/prompt_template.txt as pinned "
                       "by V3 and V4 (prompts_match_v3_v4)."),
        "batch_sha256": sha_file(os.path.join(d, "batch.jsonl")),
        "archive": {"profile": a.archive_profile, "class": profile["class"], "archive": profile["archive"],
                    "games_canonical_sha256": profile["games_canonical_sha256"], "digest_type": ARCHIVE_DIGEST_TYPE,
                    "receipt_required": True, "receipts": []},
        "machine": {"gpu": None, "driver": None, "vllm_version": None, "served_models": None,
                    "quantisation_kernel": a.kernel, "os": platform.platform()},
        "started_at": None, "finished_at": None, "status": "prepared", "notes": a.notes or "",
    }
    save_card(d, card)
    print(f"prepared {cid}: {len(games)} games x {len(arms)} arms -> {d}")
    if not replication:
        print("note: this cell is not a V3/V4 replication (" + card["replication"] + ")")


def load_card(d: str) -> dict:
    return json.load(open(os.path.join(d, "card.json"), encoding="utf-8"))


def save_card(d: str, card: dict) -> None:
    json.dump(card, open(os.path.join(d, "card.json"), "w", encoding="utf-8", newline="\n"), indent=1)


def agent_env(card: dict) -> dict:
    """The environment that makes agent.py run with the card's settings."""
    fixed = card["fixed"]
    env = dict(os.environ)
    env.update({"LADDER_MODEL": fixed["model"], "LADDER_MIN_TOKENS": str(fixed["min_tokens"]),
                "LADDER_FORMAT_REMINDER": "1" if fixed["format_reminder"] else "0"})
    return env


def resolve_data_root(data_root: str | None = None) -> str:
    """Where the ALFWorld game archive lives (matches agent.py --data-root resolution)."""
    if data_root:
        return os.path.expanduser(data_root)
    if os.environ.get("ALFWORLD_DATA"):
        return os.path.join(os.path.expanduser(os.environ["ALFWORLD_DATA"]), "json_2.1.1")
    return os.path.expanduser(DEFAULT_DATA_ROOT_REL)


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_manifest(profile_name: str) -> dict:
    """The profile's trusted {game: sha256} manifest. Raises CellError if it is absent or not the pinned one."""
    profile = ARCHIVE_PROFILES.get(profile_name)
    if profile is None:
        raise CellError(f"unknown archive profile {profile_name}")
    if not profile["manifest"] or not profile["games_canonical_sha256"]:
        raise CellError(f"archive profile {profile_name} has no pinned manifest; its bytes cannot be verified")
    try:
        with open(profile["manifest"], encoding="utf-8") as f:
            games = json.load(f)["games"]
    except (OSError, ValueError, KeyError) as e:
        raise CellError(f"cannot read the {profile_name} archive manifest {profile['manifest']}: {e}") from e
    digest = canonical_sha256(games)
    if digest != profile["games_canonical_sha256"]:
        raise CellError(f"the {profile_name} archive manifest has canonical digest {digest}, not the pinned "
                        f"{profile['games_canonical_sha256']}; refusing to trust it")
    return games


def batch_tasks(batch_path: str) -> list:
    with open(batch_path, encoding="utf-8") as f:
        return sorted({json.loads(l)["task"] for l in f if l.strip()})


def verify_game_archive(data_root: str, tasks: list, profile_name: str = REFERENCE_PROFILE) -> dict:
    """Check every scheduled game's game.tw-pddl under data_root against the profile's pinned manifest.

    Returns {game: sha256} for the checked games. Raises CellError, naming the missing, unknown and changed games,
    if any game fails; the caller then starts nothing.
    """
    manifest = load_manifest(profile_name)
    if not tasks:
        raise CellError("refusing to run: the batch schedules no games")
    missing, unknown, changed, seen = [], [], [], {}
    for task in tasks:
        if task not in manifest:
            unknown.append(task)
            continue
        path = os.path.join(data_root, *task.split("/"), "game.tw-pddl")
        if not os.path.isfile(path):
            missing.append(task)
            continue
        digest = sha_file(path)
        if digest != manifest[task]:
            changed.append((task, digest, manifest[task]))
        seen[task] = digest
    if missing or unknown or changed:
        parts = []
        if missing:
            parts.append(f"{len(missing)} game file(s) not found under {data_root}, e.g. {missing[:3]}")
        if unknown:
            parts.append(f"{len(unknown)} scheduled game(s) not in the pinned manifest, e.g. {unknown[:3]}")
        if changed:
            parts.append(f"{len(changed)} game file(s) with a SHA-256 other than the manifest's, e.g. "
                         + "; ".join(f"{t}: got {g}, expected {e}" for t, g, e in changed[:3]))
        raise CellError(
            f"refusing to run: ALFWorld game archive preflight failed for profile {profile_name} "
            f"({ARCHIVE_PROFILES[profile_name]['archive']}): " + "; ".join(parts)
            + ". The reference is json_2.1.2_tw-pddl.zip as fetched by `alfworld-download` from ALFWorld 0.4.2, "
              "which extracts into json_2.1.1/ (the older json_2.1.1 archive says 'put' where it says 'move'); "
              "set ALFWORLD_DATA or pass --data-root")
    return seen


def records_state(d: str) -> dict:
    p = os.path.join(d, "records.jsonl")
    if not os.path.exists(p):
        return {"records_lines": 0, "records_sha256": None}
    with open(p, encoding="utf-8") as f:
        lines = sum(1 for l in f if l.strip())
    return {"records_lines": lines, "records_sha256": sha_file(p)}


def check_receipts(d: str, card: dict) -> tuple:
    """Whether every record line in the cell was written by a run that passed the archive preflight.

    Returns (reasons, evidence). A card prepared with an archive policy needs a closed chain of receipts: the first
    starts at an empty records file, each starts where the previous one ended, the last ends at the current file
    (same line count and SHA-256), and each names the card's cell, batch digest and pinned manifest. Records imported
    or appended outside `run`, a skipped preflight or a changed batch break the chain. A card without a policy is
    historical evidence only if its cell is in HISTORICAL_CELLS; otherwise it is invalid.
    """
    policy = card.get("archive")
    if policy is None:
        if card.get("cell_id") in HISTORICAL_CELLS:
            return [], "historical: published before the archive preflight; no receipt; class as published"
        return ["the card has no archive policy (prepared without the archive preflight)"], "none"
    profile = ARCHIVE_PROFILES.get(policy.get("profile"))
    reasons = []
    if (profile is None or not profile["games_canonical_sha256"]
            or policy.get("games_canonical_sha256") != profile["games_canonical_sha256"]):
        reasons.append(f"the card's archive profile {policy.get('profile')} does not match a pinned manifest")
    batch = os.path.join(d, "batch.jsonl")
    if (sha_file(batch) if os.path.exists(batch) else None) != card.get("batch_sha256"):
        reasons.append("batch.jsonl differs from the batch the card was prepared with")
    receipts = policy.get("receipts") or []
    state = records_state(d)
    if not receipts:
        if state["records_lines"]:
            reasons.append(f"{state['records_lines']} record line(s) but no archive preflight receipt: "
                           "the records were not produced by `placebo_check.py run`")
        return reasons, "preflight: none"
    prev_lines, prev_sha = 0, None
    for i, r in enumerate(receipts):
        if (r.get("cell_id") != card.get("cell_id") or r.get("batch_sha256") != card.get("batch_sha256")
                or r.get("profile") != policy.get("profile")
                or r.get("games_canonical_sha256") != policy.get("games_canonical_sha256")):
            reasons.append(f"preflight receipt {i} is bound to another cell, batch or manifest")
        if r.get("records_lines_before") != prev_lines or r.get("records_sha256_before") != prev_sha:
            reasons.append(f"records changed outside a preflighted run before run {i}")
        if "records_lines_after" not in r:
            reasons.append(f"run {i} has no closing record state (interrupted before its receipt was closed)")
            break
        prev_lines, prev_sha = r["records_lines_after"], r.get("records_sha256_after")
    else:
        if (state["records_lines"], state["records_sha256"]) != (prev_lines, prev_sha):
            reasons.append("records.jsonl changed after the last preflighted run (imported or edited records)")
    return reasons, f"preflight: {len(receipts)} receipt(s), profile {policy.get('profile')} ({policy.get('class')})"


def cmd_run(a) -> None:
    card = load_card(a.cell)
    for k, p in FIXED_FILES.items():
        if sha_file(p) != card["fixed"]["sha256"].get(k):
            sys.exit(f"{k} changed since prepare ({p}); prepare a new cell")
    if prompt_config(load_agent(card["fixed"]["format_reminder"]), card["fixed"]["format_reminder"]) != card["fixed"]["prompt"]:
        sys.exit("the agent's prompt text differs from the card; prepare a new cell")
    policy = card.get("archive")
    if policy is None:
        sys.exit("refusing to run: the card has no archive policy (prepared before the archive preflight); "
                 "prepare a new cell")
    reasons, _ = check_receipts(a.cell, card)
    if reasons:
        sys.exit("refusing to run: " + "; ".join(reasons))
    batch = os.path.join(a.cell, "batch.jsonl")
    data_root = resolve_data_root(getattr(a, "data_root", None))
    try:
        seen = verify_game_archive(data_root, batch_tasks(batch), policy["profile"])
    except CellError as e:
        sys.exit(str(e))
    before = records_state(a.cell)
    policy["receipts"].append({
        "run": len(policy["receipts"]), "cell_id": card["cell_id"], "batch_sha256": card["batch_sha256"],
        "profile": policy["profile"], "games_canonical_sha256": policy["games_canonical_sha256"],
        "digest_type": ARCHIVE_DIGEST_TYPE, "games_checked": len(seen),
        "checked_games_sha256": canonical_sha256(seen), "data_root": data_root, "checked_at": now(),
        "records_lines_before": before["records_lines"], "records_sha256_before": before["records_sha256"]})
    card["started_at"], card["status"] = card["started_at"] or now(), "running"
    save_card(a.cell, card)
    returncode = None
    try:
        # --data-root is always passed, so the folder the preflight checked is the folder the agent reads.
        r = subprocess.run([sys.executable, FIXED_FILES["agent"], "--batch", batch,
                            "--out", os.path.join(a.cell, "records.jsonl"), "--parallel", str(a.parallel),
                            "--min-tokens", str(card["fixed"]["min_tokens"]), "--data-root", data_root],
                           env=agent_env(card))
        returncode = r.returncode
    finally:
        card = load_card(a.cell)
        after = records_state(a.cell)
        card["archive"]["receipts"][-1].update({"records_lines_after": after["records_lines"],
                                                "records_sha256_after": after["records_sha256"],
                                                "returncode": returncode, "ended_at": now()})
        card["status"] = "ran" if returncode == 0 else f"run exited {returncode}"
        save_card(a.cell, card)
    sys.exit(returncode)


def machine_facts(base_url: str) -> dict:
    out = {}
    try:
        q = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
                           capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
        if q:
            out["gpu"], out["driver"] = [x.strip() for x in q[0].split(",")][:2]
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        with urllib.request.urlopen(base_url + "/version", timeout=5) as r:
            out["vllm_version"] = json.load(r).get("version")
    except Exception:
        pass
    try:
        with urllib.request.urlopen(base_url + "/v1/models", timeout=5) as r:
            out["served_models"] = [m.get("id") for m in json.load(r).get("data", [])]
    except Exception:
        pass
    return out


def read_records(d: str) -> list:
    p = os.path.join(d, "records.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def check_records(recs: list, card: dict) -> tuple[list, dict]:
    """Match the records against the card's declared (game, arm, seed) triples.

    Returns (kept, report). ``kept`` holds exactly one record per declared triple that is present once with the
    declared seed. ``report`` lists what is missing and every reason the cell is invalid: records outside the card
    (extra games or arms), duplicates, a seed other than the card's replicate, and records whose model,
    min_tokens, format_reminder, temperature, max_tokens or max_steps differ from the card.
    """
    seed = card["replicate"]
    want = {(f"{card['cell_id']}~{g}", arm) for g in card["games"] for arm in card["arms"]}
    counts = Counter((r.get("unit"), r.get("arm")) for r in recs)
    extra = sorted(k for k in counts if k not in want)
    duplicates = sorted(k for k, n in counts.items() if n > 1 and k in want)
    missing = sorted(want - set(counts))
    seed_mismatch = sorted({(r.get("unit"), r.get("arm"), r.get("seed")) for r in recs
                            if (r.get("unit"), r.get("arm")) in want and r.get("seed") != seed}, key=str)
    settings = []
    for r in recs:
        if (r.get("unit"), r.get("arm")) not in want:
            continue
        m = r.get("metrics") or {}
        for name in CHECKED_SETTINGS:
            if m.get(name) != card["fixed"].get(name):
                settings.append((r.get("unit"), r.get("arm"), name, m.get(name)))
    reasons = []
    if extra:
        reasons.append(f"{len(extra)} record(s) outside the card's games and arms, e.g. {extra[:3]}")
    if duplicates:
        reasons.append(f"{len(duplicates)} (game, arm) pair(s) recorded more than once, e.g. {duplicates[:3]}")
    if seed_mismatch:
        reasons.append(f"{len(seed_mismatch)} record(s) with a seed other than the replicate {seed}, "
                       f"e.g. {seed_mismatch[:3]}")
    if settings:
        names = sorted({s[2] for s in settings})
        reasons.append(f"{len(settings)} setting(s) differ from the card ({', '.join(names)}), e.g. {settings[:3]}")
    kept = [r for r in recs if (r.get("unit"), r.get("arm")) in want and counts[(r.get("unit"), r.get("arm"))] == 1
            and r.get("seed") == seed]
    report = {"expected": len(want), "present": len(want & set(counts)), "missing": missing,
              "duplicates": len(duplicates), "extra": len(extra), "seed_mismatches": len(seed_mismatch),
              "setting_mismatches": len(settings), "invalid_reasons": reasons}
    return kept, report


def cmd_finish(a) -> None:
    card = load_card(a.cell)
    card["machine"].update({k: v for k, v in machine_facts(a.base_url).items() if v})
    recs = read_records(a.cell)
    kept, report = check_records(recs, card)
    reasons = list(report["invalid_reasons"])
    receipt_reasons, evidence = check_receipts(a.cell, card)
    reasons += receipt_reasons
    card["archive_evidence"] = evidence
    served = card["machine"].get("served_models")
    if served and card["fixed"]["model"] not in served:
        reasons.append(f"the server reports {served}, not the card's model {card['fixed']['model']}")
    card["finished_at"] = now()
    card["records"] = {k: (len(v) if k == "missing" else v) for k, v in report.items() if k != "invalid_reasons"}
    card["invalid_reasons"] = reasons
    card["status"] = "invalid" if reasons else ("incomplete" if report["missing"] else "complete")
    write_per_unit(kept, card, os.path.join(a.cell, "per_unit.csv"))
    save_card(a.cell, card)
    print(json.dumps(card["records"]), card["status"])
    for reason in reasons:
        print("invalid:", reason)
    if report["missing"]:
        print("missing (first 5):", report["missing"][:5])


COUNTERS = ["steps", "empty_retries", "invalid_no_action_tag", "invalid_actions", "memory_tokens",
            "truncated", "untagged_not_truncated"]  # the first five match the lab's per_unit.csv
# Recorded by agent.py since 2026-11-17; written per episode (blank when not recorded), never summed.
SIMILARITY = ["top1_similarity", "memory_similarity"]


def write_per_unit(recs: list, card: dict, path: str) -> None:
    """One row per declared (game, arm, seed) episode with the same counters as the lab's per_unit.csv."""
    kept, _ = check_records(recs, card)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unit", "task", "arm", "seed", "solved"] + COUNTERS + SIMILARITY)
        for r in sorted(kept, key=lambda r: (r["unit"], r["arm"])):
            m = r.get("metrics") or {}
            w.writerow([r["unit"], r["unit"].split("~", 1)[-1], r["arm"], r.get("seed"), int(bool(r.get("solved")))]
                       + [m.get(c, 0) for c in COUNTERS]
                       + ["" if m.get(c) is None else m.get(c) for c in SIMILARITY])


def summarise(recs: list, card: dict) -> dict:
    """The paired comparison over the card's declared triples. Raises CellError if the records do not match the card."""
    kept, report = check_records(recs, card)
    if report["invalid_reasons"]:
        raise CellError("; ".join(report["invalid_reasons"]))
    by = defaultdict(dict)
    for r in kept:
        by[r["unit"]][r["arm"]] = r
    arms = list(card["arms"])
    full = [u for u, v in by.items() if all(a in v for a in arms)]
    out = {"games_with_all_arms": len(full), "games_declared": len(card["games"])}
    for arm in arms:
        rs = [by[u][arm] for u in full]
        steps = sum(r["metrics"]["steps"] for r in rs) or 1
        out[arm] = {"episodes": len(rs), "solved": sum(bool(r["solved"]) for r in rs),
                    "totals": {c: sum((r.get("metrics") or {}).get(c, 0) for r in rs) for c in COUNTERS},
                    "empty_retries_per_step": round(sum(r["metrics"].get("empty_retries", 0) for r in rs) / steps, 3),
                    "untagged_per_step": round(sum(r["metrics"].get("invalid_no_action_tag", 0) for r in rs) / steps, 3),
                    "truncated_per_step": round(sum(r["metrics"].get("truncated", 0) for r in rs) / steps, 3),
                    "untagged_not_truncated_per_step": round(
                        sum(r["metrics"].get("untagged_not_truncated", 0) for r in rs) / steps, 3),
                    "memory_tokens_mean": round(sum(r["metrics"]["memory_tokens"] for r in rs) / max(1, len(rs)))}
    pairs = [("placebo", "none"), ("retrieved_task", "placebo"), ("retrieved_task", "none")]
    if "mismatched_type" in arms:
        pairs += [("mismatched_type", "placebo"), ("retrieved_task", "mismatched_type")]
    for a, b in pairs:
        g = sum(by[u][a]["solved"] and not by[u][b]["solved"] for u in full)
        l = sum(by[u][b]["solved"] and not by[u][a]["solved"] for u in full)
        out[f"{a}-{b}"] = {"wins": g, "losses": l, "difference": round((g - l) / max(1, len(full)), 3)}
    return out


def cmd_summary(a) -> None:
    card = load_card(a.cell)
    recs = read_records(a.cell)
    write_per_unit(recs, card, os.path.join(a.cell, "per_unit.csv"))
    try:
        s = summarise(recs, card)
    except CellError as e:
        sys.exit(f"refusing to summarise {card['cell_id']}: {e}")
    print(json.dumps(s, indent=1))
    print("A single block of 20 games is far too small to decide anything; the maintainer pools cells by block.")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--pool", default="v4")
    p.add_argument("--block", required=True)
    p.add_argument("--replicate", type=int, default=1)
    p.add_argument("--min-tokens", type=int, default=8, choices=[0, 8])
    p.add_argument("--format-reminder", type=int, default=0, choices=[0, 1],
                   help="0 (default): the V3/V4 prompts; 1: add the V5 format reminder to every arm")
    p.add_argument("--kernel", default=None, help="quantisation kernel reported in the vLLM log")
    p.add_argument("--notes", default=None)
    p.add_argument("--archive-profile", default=REFERENCE_PROFILE, choices=sorted(ARCHIVE_PROFILES),
                   help="the ALFWorld game archive the cell will run on; only a profile with a pinned manifest "
                        "can be prepared (today: reference)")
    p.add_argument("--with-mismatched", action="store_true",
                   help="add the mismatched_type arm (walkthroughs of other task types, length-matched)")
    p.set_defaults(f=cmd_prepare)
    for name, f in (("run", cmd_run), ("finish", cmd_finish), ("summary", cmd_summary)):
        q = sub.add_parser(name)
        q.add_argument("cell")
        q.add_argument("--parallel", type=int, default=24)
        q.add_argument("--base-url", default="http://127.0.0.1:8001")
        if name == "run":
            q.add_argument("--data-root", default=None,
                           help="ALFWorld json_2.1.1 folder (default: $ALFWORLD_DATA/json_2.1.1, else the agent.py "
                                "default); always passed on to the agent")
        q.set_defaults(f=f)
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
