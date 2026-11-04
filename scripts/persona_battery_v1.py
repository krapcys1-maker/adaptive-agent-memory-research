"""Versioned integrity successor to the frozen persona battery (PR 90 R1–R3).

The predecessor supplies unchanged task builders, controls and statistical
definitions. This entry point adds immutable execution identity, record checks,
saved execution provenance and stage coverage. No thresholds or seeds change.
Legacy folders are read-only and require --legacy-provenance SAVED/results.json;
they cannot be resumed or silently converted into a new execution.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import persona_battery as pb

CONFIG = pb.ROOT / "data/lab/aam-p-persona-v1/config.json"
FILES = {"p1": "p1.jsonl", "p2": "p2.jsonl", "p3": "p3.jsonl",
         "p7_answers": "p7/answers.jsonl", "p7_labels": "p7/labels2.jsonl"}


def sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def execution(ctx) -> dict:
    value = {"script_sha256": pb.contract.sha256_file(Path(__file__)),
            "kernel_sha256": pb.contract.sha256_file(Path(pb.mk.__file__)),
            "kernel_version": pb.mk.VERSION,
            "kernel_override": bool(os.environ.get("PERSONA_BATTERY_KERNEL")),
            "honour_record": pb.HONOUR_RECORD,
            "profile_override": os.environ.get("PERSONA_BATTERY_PROFILE"),
            "profile": ctx.profile(),
            "items_sha256": ctx.items["meta"]["sha256_of_items_file"], "card_sha256": ctx.card_sha256,
            "notes_sha256": ctx.notes_sha256}
    return json.loads(json.dumps(value))


def identity(ctx) -> dict:
    profile = ctx.profile()
    value = {"schema": 1, "execution": execution(ctx), "config_sha256": sha(ctx.cfg),
            "effective_profile": pb.mk.PROFILES[profile] if isinstance(profile, str) else profile,
            "notes_sha256": sha(ctx.notes), "items_content_sha256": sha(ctx.items),
            "free_controls_sha256": pb.contract.sha256_file(ctx.workdir / "free_controls.json"),
            "proxy_urls": ctx.urls,
            "prompt_fingerprint": pb.prompt_fingerprint(ctx),
            "embedder": type(ctx.embedder).__module__ + "." + type(ctx.embedder).__qualname__,
            "scripts": {name: pb.contract.sha256_file(pb.ROOT / name)
                        for name in ctx.cfg["script_sha256"]}}
    return json.loads(json.dumps(value))  # Profiles may contain tuples; disk JSON contains arrays.


def read_records(ctx) -> dict:
    rows = {name: pb.ps.load_jsonl(ctx.workdir / rel) for name, rel in FILES.items()}
    for name, records in rows.items():
        seen = set()
        for r in records:
            if not isinstance(r, dict) or not isinstance(r.get("key"), str) or not isinstance(r.get("text"), str):
                raise ValueError("invalid record in " + name)
            if r["key"] in seen:
                raise ValueError("duplicate record key in " + name)
            seen.add(r["key"])
    return rows


def saved_execution(ctx, legacy_provenance: Path | None = None) -> tuple[dict, bool]:
    path = ctx.workdir / "baseline.json"
    if not path.exists():
        raise ValueError("run prepare first; no saved execution identity")
    baseline = pb.load_json(path)
    manifest = baseline.get("execution_manifest")
    if manifest is not None:
        if baseline.get("execution_manifest_sha256") != sha(manifest) or manifest != identity(ctx):
            raise ValueError("execution identity changed; use the original settings or a new work folder")
        if legacy_provenance is not None:
            raise ValueError("legacy provenance is only for legacy folders")
        return copy.deepcopy(manifest["execution"]), False
    if legacy_provenance is None:
        raise ValueError("legacy folder: analysis requires --legacy-provenance; resuming is refused")
    declared = pb.load_json(legacy_provenance).get("provenance", {})
    current = execution(ctx)
    # The old JSON records the input file digest, not the normalized object.
    current["items_sha256"] = ctx.items["meta"]["sha256_of_items_file"]
    for key in ("items_sha256", "card_sha256", "kernel_version", "honour_record", "profile", "kernel_override"):
        value = declared.get(key, False if key in ("honour_record", "kernel_override") else None)
        if value != current[key]:
            raise ValueError("legacy provenance/settings mismatch: " + key)
    for key in ("items_sha256", "notes_sha256", "kernel_version", "kernel_sha256", "prompt_fingerprint"):
        expected = current.get(key, pb.prompt_fingerprint(ctx) if key == "prompt_fingerprint" else None)
        if baseline.get(key) != expected:
            raise ValueError("legacy baseline mismatch: " + key)
    for key, current_value in (("honour_record", pb.HONOUR_RECORD),
                               ("profile_override", os.environ.get("PERSONA_BATTERY_PROFILE"))):
        if key in baseline and baseline[key] != current_value:
            raise ValueError("legacy baseline mismatch: " + key)
    digest = declared.get("script_sha256", "")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("legacy provenance requires the historical runner digest")
    return copy.deepcopy(declared), True


def label_tasks(ctx, answers):
    tasks = pb.bp.label_tasks(pb.p7_probes(ctx.items), answers, [], contextual=True)
    for t in tasks:
        t["meta"]["psha"] = pb.sha256_text(t["system"] + "\x00" + t["user"])[:16]
    return tasks


def validate_records(records, tasks, *, legacy_labels=False) -> dict:
    expected = {t["key"]: t for t in tasks}
    if len(expected) != len(tasks):
        raise ValueError("duplicate planned task key")
    for r in records:
        t = expected.get(r["key"])
        if t is None:
            raise ValueError("unknown record key")
        for key, value in t["meta"].items():
            if legacy_labels and key == "psha" and key not in r:
                continue  # The predecessor did not record a digest for judge prompts.
            if r.get(key) != value:
                raise ValueError("record metadata/prompt digest mismatch: " + key)
    return {"status": "complete" if len(records) == len(tasks) else "partial" if records else "not_started",
            "expected": len(tasks), "actual": len(records), "missing": len(tasks) - len(records)}


def coverage(ctx, rows, *, legacy=False) -> dict:
    p2 = rows["p2"]
    s1 = pb.p2_s1_tasks(ctx)
    s2 = pb.p2_later_tasks(ctx, p2, "s2")
    s3 = pb.p2_later_tasks(ctx, p2, "s3")
    expected = {"p1": pb.p1_tasks(ctx), "p2": s1 + s2 + s3,
                "p3": pb.p3_tasks(ctx), "p7_answers": pb.p7_answer_tasks(ctx),
                "p7_labels": label_tasks(ctx, rows["p7_answers"])}
    # Dependent observations must never survive missing prerequisites.
    keys = {r["key"] for r in p2}
    if any(r.get("arm") != "S1" for r in p2) and not all(t["key"] in keys for t in s1):
        raise ValueError("P2 s1 is incomplete before a later step")
    if any(r.get("arm") == "S3W" for r in p2) and not all(t["key"] in keys for t in s2):
        raise ValueError("P2 s2 is incomplete before s3")
    out = {name: validate_records(rows[name], tasks, legacy_labels=legacy and name == "p7_labels")
           for name, tasks in expected.items()}
    if out["p7_answers"]["status"] != "complete" and rows["p7_labels"]:
        raise ValueError("P7 answers are incomplete before labelling")
    return out


def prepare(ctx, items_path):
    baseline = ctx.workdir / "baseline.json"
    rows = read_records(ctx)
    if baseline.exists():
        saved_execution(ctx)
        coverage(ctx, rows)
        return pb.load_json(ctx.workdir / "free_controls.json")
    if any(rows.values()):
        raise ValueError("answers exist without an execution manifest; use a new work folder")
    problems = pb.frozen_problems(ctx, items_path)
    if problems:
        raise ValueError("frozen inputs differ: " + " | ".join(problems))
    controls = pb.stage_prepare(ctx, items_path)
    data = pb.load_json(baseline)
    manifest = identity(ctx)
    data.update(execution_manifest=manifest, execution_manifest_sha256=sha(manifest))
    pb.write_json(baseline, data)
    return controls


def run_chunked(ctx, tasks, role, path, guard):
    records = pb.ps.load_jsonl(path)
    selected = {t["key"] for t in tasks}
    validate_records([r for r in records if r["key"] in selected], tasks)
    return pb.run_chunked(ctx, tasks, role, path, guard)


def run_stage(ctx, stage, items_path, step="all"):
    saved_execution(ctx)
    problems = pb.frozen_problems(ctx, items_path)
    if problems:
        raise ValueError("frozen inputs differ: " + " | ".join(problems))
    rows = read_records(ctx)
    state = coverage(ctx, rows)  # Validate every existing record before proxy access.
    work = ctx.workdir

    def run(tasks, name, role, path):
        if role == "writer":
            pb.guard_tasks(ctx, tasks)
        pb.cap_check(ctx, name, tasks)
        return pb.paid_stage(ctx, stage + ":" + name, role,
                             lambda g: run_chunked(ctx, tasks, role, path, g))

    if stage in ("run-p1", "run-p3"):
        name = stage[4:]
        return run(getattr(pb, name + "_tasks")(ctx), name, "writer", work / FILES[name])
    if stage == "run-p2":
        if step not in ("all", "s1", "s2", "s3"):
            raise ValueError("run-p2 --step must be all, s1, s2 or s3")
        asked = 0
        for sub in ("s1", "s2", "s3"):
            if step not in ("all", sub):
                continue
            records = read_records(ctx)["p2"]
            previous = pb.p2_s1_tasks(ctx) if sub == "s2" else pb.p2_later_tasks(ctx, records, "s2")
            if sub != "s1" and not all(t["key"] in {r["key"] for r in records} for t in previous):
                raise ValueError("previous P2 step is incomplete")
            tasks = pb.p2_s1_tasks(ctx) if sub == "s1" else pb.p2_later_tasks(ctx, records, sub)
            asked += run(tasks, "p2", "writer", work / FILES["p2"])
        return asked
    if step not in ("all", "answer", "label"):
        raise ValueError("run-p7 --step must be all, answer or label")
    asked = 0
    if step in ("all", "answer"):
        asked += run(pb.p7_answer_tasks(ctx), "p7", "writer", work / FILES["p7_answers"])
        state = coverage(ctx, read_records(ctx))
    if step in ("all", "label"):
        if state["p7_answers"]["status"] != "complete":
            raise ValueError("P7 answers are incomplete before labelling")
        asked += run(label_tasks(ctx, read_records(ctx)["p7_answers"]), "p7", "judge", work / FILES["p7_labels"])
    return asked


def analyse(ctx, legacy_provenance=None):
    provenance, legacy = saved_execution(ctx, legacy_provenance)
    rows = read_records(ctx)
    state = coverage(ctx, rows, legacy=legacy)
    work = ctx.workdir
    free = pb.load_json(work / "free_controls.json")

    def labels(folder, stem, label, entries, classes, filename):
        _, mapping = pb.blind_pack(label, entries)
        if not legacy:
            pb.write_sheet(folder, stem, label, entries)
        return pb.read_labels(folder / filename, mapping, classes)

    h1 = labels(work, "p1_unanswered", "p1", pb.unanswered_entries(ctx, rows["p1"]), pb.UNANSWERED_CLASSES, "p1_unanswered_labels.json")
    h3 = labels(work, "p3_blind", "p3", pb.blind_entries(ctx, rows["p3"]), pb.BLIND_CLASSES, "p3_blind_labels.json")
    entries = pb.hand_entries(ctx.items, rows["p7_answers"])
    h7 = labels(work / "p7", "hand", "p7", entries, pb.HAND_CLASSES, "hand_labels.json")
    _, mapping = pb.blind_pack("p7", entries)
    h7b = pb.read_labels(work / "p7/hand_labels_2.json", mapping, pb.HAND_CLASSES)
    summaries = {"p1": pb.p1_summary(ctx, rows["p1"], h1) if rows["p1"] else None,
                 "p2": pb.p2_summary(ctx, rows["p2"]) if rows["p2"] else None,
                 "p3": pb.p3_summary(ctx, rows["p3"], h3) if rows["p3"] else None,
                 "p7": pb.p7_summary(ctx, rows["p7_answers"], h7, h7b) if rows["p7_answers"] else None}
    readings = {}
    for name, summary in summaries.items():
        values = (pb.p1_readings(summary) if name == "p1" else
                  getattr(pb, name + "_readings")(summary, free)) if summary else None
        ready = state["p7_answers" if name == "p7" else name]["status"] == "complete"
        if name == "p7":
            ready = ready and state["p7_labels"]["status"] == "complete"
        # P1 readings use automatic fact scores; its separate unanswered-question
        # annotation status remains in the descriptive summary. P3/P7 need labels.
        if name == "p3" and summary:
            ready = ready and summary["blind_read"]["status"] == "complete"
        if name == "p7" and summary:
            ready = ready and summary["hand_labels"]["status"] == "complete"
        if values and not ready:
            values = dict.fromkeys(values)
        readings[name] = values
        state.setdefault(name, {})["readings_ready"] = ready
    return dict(summaries, free_controls=free, readings=readings, coverage=state,
                records={name: len(records) for name, records in rows.items()},
                provenance=provenance,
                analysis_provenance={"script_sha256": pb.contract.sha256_file(Path(__file__)),
                                     "execution_identity": "legacy-declared" if legacy else "manifest-verified",
                                     "legacy_judge_prompt_digests_unavailable": legacy})


def main(argv=None, generate=None, judge=None, embedder=None, summary_fn=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=pb.STAGES)
    for name in ("items", "workdir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    for name in ("notes", "card", "ledger", "json", "legacy-provenance"):
        parser.add_argument("--" + name, type=Path)
    for name in ("writer-url", "judge-url"):
        parser.add_argument("--" + name)
    parser.add_argument("--embedder", choices=("none", "minilm"), default="none")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--step", default="all")
    args = parser.parse_args(argv)
    try:
        if args.legacy_provenance and args.stage != "analyse":
            raise ValueError("legacy folders may only be analysed")
        ctx = pb.load_context(args, embedder, generate, judge, summary_fn)
        if args.stage == "prepare":
            prepare(ctx, args.items)
        elif args.stage == "analyse":
            # Explicit exports must never overwrite any saved run artifact.
            if args.json and (args.json.resolve().is_relative_to(args.workdir.resolve()) or args.json.exists()):
                raise ValueError("analysis export needs a new path outside the run folder")
            result = analyse(ctx, args.legacy_provenance)
            if pb.find_item_text(result, ctx.items):
                raise ValueError("private item text detected in aggregates")
            if args.json:
                pb.write_json(args.json, result)
            print(json.dumps(result["coverage"], sort_keys=True))
        else:
            print("done: %d new calls" % run_stage(ctx, args.stage, args.items, args.step))
    except (pb.rb.BudgetStop, pb.rb.PreflightFailed, pb.backends.SpendCapRefused) as exc:
        print("stopped: %s" % exc, file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
