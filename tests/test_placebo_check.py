"""CPU tests of the placebo-check cell tool and its frozen pools (no GPU, no model, no ALFWorld install)."""
import importlib.util
import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools" / "alfworld_ladder"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, TOOLS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def pc(tmp_path, monkeypatch):
    monkeypatch.setenv("AAMR_CONTRIB_ROOT", str(tmp_path))
    monkeypatch.delenv("LADDER_MODEL", raising=False)
    monkeypatch.delenv("LADDER_FORMAT_REMINDER", raising=False)
    return load("placebo_check", "placebo_check.py")


def test_pools_are_frozen_train_blocks_disjoint_from_the_bank():
    pools = json.loads((TOOLS / "contrib" / "pools.json").read_text(encoding="utf-8"))
    bank_fams = {json.loads(l)["family"] for l in (TOOLS / "data" / "bank.jsonl").read_text(encoding="utf-8").splitlines()}
    for name in ("v4", "fresh"):
        blocks = pools[name]["blocks"]
        games = [g for b in blocks.values() for g in b]
        assert all(len(b) == 20 for b in blocks.values())
        assert len(games) == len(set(games))
        assert all(g.startswith("train/") for g in games)
        assert not any("valid_unseen" in g for g in games)
        assert not {g.split("/")[1] for g in games} & bank_fams
        assert len({g.split("/")[1] for g in games}) == len(games)  # one game per family


def test_prepare_writes_batch_and_card(pc, tmp_path):
    pc.main(["prepare", "--pool", "v4", "--block", "B00", "--replicate", "2", "--min-tokens", "0"])
    d = tmp_path / "placebo-v4-B00-r2-mt0-fr0"
    batch = [json.loads(l) for l in (d / "batch.jsonl").read_text().splitlines()]
    card = json.loads((d / "card.json").read_text())
    assert len(batch) == 60 and {b["arm"] for b in batch} == set(pc.ARMS)
    assert all(b["seed"] == 2 and b["unit"].startswith("placebo-v4-B00-r2-mt0-fr0~") for b in batch)
    assert card["fixed"]["min_tokens"] == 0 and card["fixed"]["sha256"]["bank"] == pc.sha_file(pc.FIXED_FILES["bank"])
    with pytest.raises(SystemExit):
        pc.main(["prepare", "--block", "B99"])


SETTINGS = {"model": "Qwen/Qwen3-4B-Instruct-2507-FP8", "min_tokens": 8, "format_reminder": False,
            "temperature": 0.7, "max_tokens": 2048, "max_steps": 50}


def fake_records(cid, games, solved, seed=1, **settings):
    out = []
    for g in games:
        for arm in ("none", "placebo", "retrieved_task"):
            out.append({"unit": f"{cid}~{g}", "arm": arm, "seed": seed, "solved": solved(g, arm), "memory_sources": [],
                        "metrics": {"steps": 10, "empty_retries": 2 if arm == "none" else 0,
                                    "invalid_no_action_tag": 1, "memory_tokens": 0 if arm == "none" else 800,
                                    "top1_similarity": 0.5,
                                    "memory_similarity": 0.4 if arm == "retrieved_task" else None,
                                    **{**SETTINGS, **settings}}})
    return out


def test_finish_and_summary(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B01")
    pc.main(["prepare", "--block", "B01"])
    d = tmp_path / "placebo-v4-B01-r1-mt8-fr0"
    card = json.loads((d / "card.json").read_text())
    games = card["games"]
    recs = fake_records(card["cell_id"], games, lambda g, arm: arm != "none" or g == games[0])
    spy_run(monkeypatch, pc, writes=recs[:-1])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    monkeypatch.setattr(pc, "machine_facts", lambda url: {"gpu": "TEST"})
    pc.main(["finish", str(d)])
    assert json.loads((d / "card.json").read_text())["status"] == "incomplete"
    spy_run(monkeypatch, pc, writes=recs[-1:])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "complete" and card["machine"]["gpu"] == "TEST"
    assert card["block"] == "B01" and len(card["block_games_sha256"]) == 64 and len(card["pools_file_sha256"]) == 64
    rows = (d / "per_unit.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == ("unit,task,arm,seed,solved,steps,empty_retries,invalid_no_action_tag,invalid_actions,"
                       "memory_tokens,truncated,untagged_not_truncated,top1_similarity,memory_similarity")
    assert len(rows) == 61
    by_arm = {r.split(",")[2]: r for r in rows[1:]}
    assert by_arm["none"].endswith(",0.5,") and by_arm["retrieved_task"].endswith(",0.5,0.4")
    s = pc.summarise(recs, card)
    assert s["games_with_all_arms"] == 20
    assert s["placebo-none"] == {"wins": 19, "losses": 0, "difference": 0.95}
    assert s["none"]["totals"]["steps"] == 200 and s["none"]["totals"]["empty_retries"] == 40
    assert s["none"]["empty_retries_per_step"] == 0.2 and s["placebo"]["empty_retries_per_step"] == 0.0


def test_agent_min_tokens_switch(monkeypatch):
    monkeypatch.setenv("LADDER_MIN_TOKENS", "0")
    agent = load("ladder_agent_mt", "agent.py")
    assert agent.CFG["min_tokens"] == 0
    monkeypatch.delenv("LADDER_MIN_TOKENS")
    assert load("ladder_agent_mt8", "agent.py").CFG["min_tokens"] == 8


def test_prepare_with_mismatched_arm(pc, tmp_path):
    pc.main(["prepare", "--block", "B02", "--with-mismatched"])
    d = tmp_path / "placebo-v4-B02-r1-mt8-fr0-mis"
    batch = [json.loads(l) for l in (d / "batch.jsonl").read_text().splitlines()]
    assert len(batch) == 80 and "mismatched_type" in {b["arm"] for b in batch}
    assert json.loads((d / "card.json").read_text())["arms"][-1] == "mismatched_type"


# Finding 2 of the external audit (gpt raport, 2026-11-18): the card must pin the configuration the agent runs.

def test_card_records_model_prompt_and_format_reminder(pc, tmp_path):
    pc.main(["prepare", "--block", "B03", "--min-tokens", "0"])
    card = json.loads((tmp_path / "placebo-v4-B03-r1-mt0-fr0" / "card.json").read_text())
    fixed = card["fixed"]
    assert fixed["format_reminder"] is False and fixed["min_tokens"] == 0
    assert fixed["model"] == pc.load_agent().CFG["model"] == pc.V3V4_MODEL
    assert fixed["prompt"]["prompt_template_sha256"] == pc.V3V4_PROMPT_TEMPLATE_SHA256
    assert fixed["prompt"]["prompts_match_v3_v4"] is True
    assert fixed["sha256"]["prompt_template"] == pc.V3V4_PROMPT_TEMPLATE_SHA256
    assert card["replication"].startswith("V3/V4")


def test_format_reminder_on_is_a_v5_prompt_cell(pc, tmp_path):
    pc.main(["prepare", "--block", "B03", "--format-reminder", "1"])
    card = json.loads((tmp_path / "placebo-v4-B03-r1-mt8-fr1" / "card.json").read_text())
    assert card["fixed"]["format_reminder"] is True
    assert card["fixed"]["prompt"]["prompts_match_v3_v4"] is False
    assert card["replication"].startswith("conceptual")


def test_the_card_model_comes_from_the_agent_config_and_changes_the_cell_id(pc, tmp_path, monkeypatch):
    monkeypatch.setenv("LADDER_MODEL", "some-other/model-7B")
    pc.main(["prepare", "--block", "B03"])
    (d,) = [p for p in tmp_path.iterdir() if p.name.startswith("placebo-v4-B03-r1-mt8-fr0-x")]
    card = json.loads((d / "card.json").read_text())
    assert card["fixed"]["model"] == "some-other/model-7B" and card["replication"].startswith("conceptual")


# The archive preflight: every scheduled game against a pinned manifest, a receipt per run, finish requires the chain.

def test_the_reference_manifest_is_pinned_and_covers_every_pool_game(pc):
    games = pc.load_manifest(pc.REFERENCE_PROFILE)  # raises unless the canonical digest is the pinned one
    pools = json.loads((TOOLS / "contrib" / "pools.json").read_text(encoding="utf-8"))
    pool_games = {g for name in ("v4", "fresh") for b in pools[name]["blocks"].values() for g in b}
    assert pool_games <= set(games)
    assert games[pc.ARCHIVE_CHECK_GAME] == pc.ARCHIVE_CHECK_SHA256  # the SETUP_SAME.md sentinel
    assert all(len(v) == 64 for v in games.values())


def test_a_manifest_that_is_not_the_pinned_one_is_refused(pc, tmp_path, monkeypatch):
    fake = tmp_path / "manifest.json"
    fake.write_text(json.dumps({"games": {"train/x/trial_T0": "0" * 64}}))
    monkeypatch.setitem(pc.ARCHIVE_PROFILES["reference"], "manifest", str(fake))
    with pytest.raises(pc.CellError, match="not the pinned"):
        pc.load_manifest("reference")


def fake_archive(pc, monkeypatch, tmp_path, block, name="alfworld_data"):
    """Game files for every game of the block plus a manifest pinned for them. Returns (base, data_root)."""
    pools = json.loads((TOOLS / "contrib" / "pools.json").read_text(encoding="utf-8"))
    base = tmp_path / name
    data_root = base / "json_2.1.1"
    games = {}
    for g in pools["v4"]["blocks"][block]:
        p = data_root.joinpath(*g.split("/"), "game.tw-pddl")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(f"json_2.1.2 game {g}\n".encode())
        games[g] = pc.sha_file(str(p))
    manifest = tmp_path / f"{name}-manifest.json"
    manifest.write_text(json.dumps({"games": games}))
    monkeypatch.setitem(pc.ARCHIVE_PROFILES["reference"], "manifest", str(manifest))
    monkeypatch.setitem(pc.ARCHIVE_PROFILES["reference"], "games_canonical_sha256", pc.canonical_sha256(games))
    return base, data_root


class Done:
    returncode = 0


def spy_run(monkeypatch, pc, writes=None):
    """Replace subprocess.run; on each call optionally append `writes` records to the --out file."""
    calls = []

    def fake_run(cmd, env=None, **kw):
        calls.append({"cmd": cmd, "env": env})
        if writes is not None:
            with open(cmd[cmd.index("--out") + 1], "a", encoding="utf-8") as f:
                for r in writes:
                    f.write(json.dumps(r) + "\n")
        return Done()

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    return calls


def run_cell(pc, d, *extra):
    with pytest.raises(SystemExit) as exit_:
        pc.main(["run", str(d), *extra])
    return exit_.value.code


def test_run_passes_the_card_settings_to_the_agent(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B04")
    pc.main(["prepare", "--block", "B04", "--min-tokens", "0"])
    d = tmp_path / "placebo-v4-B04-r1-mt0-fr0"
    monkeypatch.setenv("LADDER_FORMAT_REMINDER", "1")  # the agent's own default is the V5 reminder: run must override
    monkeypatch.setenv("ALFWORLD_DATA", str(base))
    calls = spy_run(monkeypatch, pc)
    assert run_cell(pc, d) == 0
    seen = calls[0]
    assert seen["env"]["LADDER_FORMAT_REMINDER"] == "0"
    assert seen["env"]["LADDER_MODEL"] == pc.V3V4_MODEL and seen["env"]["LADDER_MIN_TOKENS"] == "0"
    assert seen["cmd"][seen["cmd"].index("--min-tokens") + 1] == "0"
    assert seen["cmd"][seen["cmd"].index("--data-root") + 1] == str(data_root)
    card = json.loads((d / "card.json").read_text())
    receipt = card["archive"]["receipts"][0]
    assert card["archive"]["profile"] == "reference" and card["archive"]["class"] == "primary"
    assert receipt["games_checked"] == 20 and receipt["batch_sha256"] == card["batch_sha256"]
    assert receipt["records_lines_before"] == 0 and receipt["records_lines_after"] == 0
    assert "game.tw-pddl" in receipt["digest_type"] and card["status"] == "ran"


@pytest.mark.parametrize("damage", ["altered", "missing", "mixed", "sentinel_only"])
def test_run_refuses_a_damaged_archive_and_launches_nothing(pc, tmp_path, monkeypatch, damage):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B04")
    pc.main(["prepare", "--block", "B04"])
    d = tmp_path / "placebo-v4-B04-r1-mt8-fr0"
    card = json.loads((d / "card.json").read_text())
    files = [data_root.joinpath(*g.split("/"), "game.tw-pddl") for g in card["games"]]
    if damage == "altered":  # one scheduled game changed, the rest intact
        files[5].write_bytes(b"old json_2.1.1 archive: put x in/on y\n")
    elif damage == "missing":
        files[7].unlink()
    elif damage == "mixed":  # some games from another archive, some absent
        for f in files[:3]:
            f.write_bytes(b"other bytes\n")
        files[-1].unlink()
    else:  # only one intact game left: a lone sentinel must not start a pool
        for f in files[1:]:
            f.unlink()
    calls = spy_run(monkeypatch, pc)
    msg = str(run_cell(pc, d, "--data-root", str(data_root)))
    assert "preflight failed" in msg and "json_2.1.2" in msg
    if damage in ("altered", "mixed"):
        assert "SHA-256 other than the manifest's" in msg
    if damage in ("missing", "mixed", "sentinel_only"):
        assert "not found" in msg
    assert calls == []
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "prepared" and after["archive"]["receipts"] == []


def test_run_refuses_a_scheduled_game_outside_the_manifest(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B04")
    pc.main(["prepare", "--block", "B04"])
    d = tmp_path / "placebo-v4-B04-r1-mt8-fr0"
    card = json.loads((d / "card.json").read_text())
    with open(d / "batch.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"unit": "x", "task": "train/not-pinned/trial_T0", "arm": "none", "seed": 1}) + "\n")
    calls = spy_run(monkeypatch, pc)
    assert "batch.jsonl differs" in str(run_cell(pc, d, "--data-root", str(data_root)))
    assert calls == []
    # Even with the batch digest updated to match, an unpinned game blocks the run.
    card["batch_sha256"] = pc.sha_file(str(d / "batch.jsonl"))
    (d / "card.json").write_text(json.dumps(card))
    assert "not in the pinned manifest" in str(run_cell(pc, d, "--data-root", str(data_root)))
    assert calls == []


def test_the_older_archive_profile_cannot_be_prepared_without_a_pinned_manifest(pc, tmp_path):
    with pytest.raises(SystemExit) as exit_:
        pc.main(["prepare", "--block", "B04", "--archive-profile", "older-json_2.1.1"])
    assert "no pinned manifest" in str(exit_.value.code)
    assert not (tmp_path / "placebo-v4-B04-r1-mt8-fr0-aolder-json_2.1.1").exists()


def test_a_non_reference_profile_is_its_own_cell_class(pc, tmp_path, monkeypatch):
    """If a sensitivity profile gets a pinned manifest, its cells carry the class and a separate cell id."""
    pools = json.loads((TOOLS / "contrib" / "pools.json").read_text(encoding="utf-8"))
    games = {g: "1" * 64 for g in pools["v4"]["blocks"]["B04"]}
    manifest = tmp_path / "older.json"
    manifest.write_text(json.dumps({"games": games}))
    monkeypatch.setitem(pc.ARCHIVE_PROFILES["older-json_2.1.1"], "manifest", str(manifest))
    monkeypatch.setitem(pc.ARCHIVE_PROFILES["older-json_2.1.1"], "games_canonical_sha256", pc.canonical_sha256(games))
    pc.main(["prepare", "--block", "B04", "--archive-profile", "older-json_2.1.1"])
    card = json.loads((tmp_path / "placebo-v4-B04-r1-mt8-fr0-aolder-json_2.1.1" / "card.json").read_text())
    assert card["archive"]["class"] == "sensitivity" and card["cell_id"].endswith("-aolder-json_2.1.1")


def test_finish_requires_a_closed_receipt_chain(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    # prepare -> records written directly (agent.py by hand, or imported) -> finish: invalid, no receipt.
    write_records(d, recs)
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["archive_evidence"] == "preflight: none"
    assert any("no archive preflight receipt" in r for r in after["invalid_reasons"])
    # ... and run refuses to bless those records afterwards.
    calls = spy_run(monkeypatch, pc)
    assert "no archive preflight receipt" in str(run_cell(pc, d, "--data-root", str(data_root)))
    assert calls == []


def test_finish_accepts_records_written_by_a_preflighted_run(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs[:30])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    spy_run(monkeypatch, pc, writes=recs[30:])  # a resumed run appends: the chain continues
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "complete" and after["invalid_reasons"] == []
    assert after["archive_evidence"].startswith("preflight: 2 receipt(s), profile reference (primary)")


@pytest.mark.parametrize("tamper", ["appended", "replaced", "receipt_for_other_batch", "unclosed"])
def test_finish_rejects_records_outside_the_receipt_chain(pc, tmp_path, monkeypatch, tamper):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs[:-1])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    card = json.loads((d / "card.json").read_text())
    if tamper == "appended":  # an imported record after the run
        with open(d / "records.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(recs[-1]) + "\n")
    elif tamper == "replaced":  # the run's file swapped for records from elsewhere (same games, all three arms)
        write_records(d, recs)
    elif tamper == "receipt_for_other_batch":
        card["archive"]["receipts"][0]["batch_sha256"] = "0" * 64
        (d / "card.json").write_text(json.dumps(card))
    else:  # an interrupted run whose file then received a line that is no record of this cell
        open_receipt(card)
        (d / "card.json").write_text(json.dumps(card))
        with open(d / "records.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"unit": "elsewhere~train/x", "arm": "none", "seed": 1, "solved": True,
                                "metrics": {}}) + "\n")
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid"


def open_receipt(card, i=-1):
    """What a hard kill leaves: the receipt written before the launch, never closed."""
    for k in ("records_lines_after", "records_sha256_after", "records_bytes_after", "returncode", "ended_at",
              "closed_as"):
        card["archive"]["receipts"][i].pop(k, None)


def spy_jobs(monkeypatch, pc, writes):
    """Like spy_run, and records how many jobs each launch was given."""
    jobs = []

    def fake_run(cmd, env=None, **kw):
        jobs.append(len(open(cmd[cmd.index("--batch") + 1], encoding="utf-8").read().splitlines()))
        with open(cmd[cmd.index("--out") + 1], "a", encoding="utf-8") as f:
            for r in writes:
                f.write(json.dumps(r) + "\n")
        return Done()

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    return jobs


def test_an_interrupted_run_is_recovered_and_the_rest_resumes(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs[:30])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    card = json.loads((d / "card.json").read_text())
    open_receipt(card)  # killed after 30 episodes, before the receipt was closed
    (d / "card.json").write_text(json.dumps(card))
    jobs = spy_jobs(monkeypatch, pc, writes=recs[30:])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    assert jobs == [30]  # only the episodes without a record run again
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    # The 30 recovered records are not shown to come from a checked run: a distinct status, not pooled.
    assert after["status"] == "complete-recovered" and after["invalid_reasons"] == []
    assert len(after["recovered_unverified_jobs"]) == 30
    first = after["archive"]["receipts"][0]
    assert first["closed_as"] == "recovered" and first["recovery"]["appended_record_lines"] == 30
    assert "recovered" in after["archive_evidence"]
    # A third run has nothing left to do and adds no receipt.
    calls = spy_run(monkeypatch, pc)
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    assert calls == [] and len(json.loads((d / "card.json").read_text())["archive"]["receipts"]) == 2


def test_finish_recovers_an_interrupted_last_run_without_a_new_run(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs)
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    card = json.loads((d / "card.json").read_text())
    open_receipt(card)
    (d / "card.json").write_text(json.dumps(card))
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "complete-recovered" and after["archive"]["receipts"][0]["closed_as"] == "recovered"
    assert len(after["recovered_unverified_jobs"]) == 60


@pytest.mark.parametrize("damage", ["earlier_records_changed", "foreign_line"])
def test_an_interrupted_run_that_cannot_be_recovered_stays_invalid(pc, tmp_path, monkeypatch, damage):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs[:20])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    spy_run(monkeypatch, pc, writes=recs[20:40])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    card = json.loads((d / "card.json").read_text())
    open_receipt(card)  # the second run was killed
    (d / "card.json").write_text(json.dumps(card))
    lines = (d / "records.jsonl").read_text(encoding="utf-8").splitlines(keepends=True)
    if damage == "earlier_records_changed":
        lines[3] = json.dumps(dict(recs[3], solved=False)) + "\n"
    else:
        lines.append("not a record\n")
    (d / "records.jsonl").write_text("".join(lines), encoding="utf-8")
    calls = spy_run(monkeypatch, pc)
    assert "not recoverable" in str(run_cell(pc, d, "--data-root", str(data_root)))
    assert calls == []
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and any("not recoverable" in r for r in after["invalid_reasons"])
    assert "closed_as" not in after["archive"]["receipts"][1]


def legacy_card(pc, d):
    """Turn a freshly prepared card into one written by placebo_check.py before the archive preflight."""
    card = json.loads((d / "card.json").read_text())
    del card["archive"], card["batch_sha256"]
    (d / "card.json").write_text(json.dumps(card))
    return card


def test_a_card_prepared_before_the_preflight_is_upgraded_by_run(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, _ = prepared_cell(pc, tmp_path, monkeypatch)
    card = legacy_card(pc, d)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    write_records(d, recs[:10])  # episodes run before the preflight existed
    pc.main(["finish", str(d)])
    assert "`run` upgrades it" in json.loads((d / "card.json").read_text())["invalid_reasons"][-1]
    jobs = spy_jobs(monkeypatch, pc, writes=recs)
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    assert jobs == [60]  # the pre-receipt episodes are not counted: every job runs under a receipt
    after = json.loads((d / "card.json").read_text())
    up = after["archive"]["upgraded_from_legacy"]
    assert after["archive"]["profile"] == "reference" and up["pre_receipt"]["lines"] == 10
    assert up["pre_receipt"]["counted"] is False and (d / "records.pre_receipt.jsonl").exists()
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "complete" and "upgraded" in after["archive_evidence"]


@pytest.mark.parametrize("problem", ["archive", "batch"])
def test_a_legacy_card_is_not_upgraded_when_a_check_fails(pc, tmp_path, monkeypatch, problem):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, _ = prepared_cell(pc, tmp_path, monkeypatch)
    card = legacy_card(pc, d)
    write_records(d, fake_records(card["cell_id"], card["games"], lambda g, arm: True)[:10])
    if problem == "archive":
        data_root.joinpath(*card["games"][0].split("/"), "game.tw-pddl").write_bytes(b"other\n")
    else:
        with open(d / "batch.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"unit": "x", "task": card["games"][0], "arm": "none", "seed": 1}) + "\n")
    calls = spy_run(monkeypatch, pc)
    msg = str(run_cell(pc, d, "--data-root", str(data_root)))
    assert ("preflight failed" if problem == "archive" else "cannot be upgraded") in msg
    assert calls == [] and "archive" not in json.loads((d / "card.json").read_text())
    assert (d / "records.jsonl").exists() and not (d / "records.pre_receipt.jsonl").exists()


def test_the_receipt_stores_no_absolute_path(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, _ = prepared_cell(pc, tmp_path, monkeypatch)
    spy_run(monkeypatch, pc)
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    text = (d / "card.json").read_text()
    receipt = json.loads(text)["archive"]["receipts"][0]
    assert receipt["data_root"] == {"source": "--data-root", "folder": "json_2.1.1"}
    assert str(data_root) not in text and json.dumps(str(data_root))[1:-1] not in text
    assert len(receipt["placebo_check_sha256"]) == 64 and len(receipt["manifest_file_sha256"]) == 64


def test_a_card_without_an_archive_policy_is_historical_only_for_published_cells(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    del card["archive"]
    (d / "card.json").write_text(json.dumps(card))
    write_records(d, fake_records(card["cell_id"], card["games"], lambda g, arm: True))
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and "no archive policy" in after["invalid_reasons"][0]
    monkeypatch.setattr(pc, "HISTORICAL_CELLS", frozenset({card["cell_id"]}))
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "complete" and after["archive_evidence"].startswith("historical")
    with pytest.raises(SystemExit) as exit_:  # and it can never start a new run
        pc.main(["run", str(d)])
    assert "no archive policy" in str(exit_.value.code)


def test_the_published_b03_cell_is_labelled_historical():
    card = json.loads((TOOLS.parents[1] / "data" / "contrib" / "placebo-v4-B03-r1-mt0-fr0" / "card.json")
                      .read_text(encoding="utf-8"))
    assert "archive" not in card and card["cell_id"] in load("pc_hist", "placebo_check.py").HISTORICAL_CELLS


def prepared_cell(pc, tmp_path, monkeypatch, block="B05"):
    pc.main(["prepare", "--block", block])
    d = tmp_path / f"placebo-v4-{block}-r1-mt8-fr0"
    monkeypatch.setattr(pc, "machine_facts", lambda url: {})
    return d, json.loads((d / "card.json").read_text())


def write_records(d, recs):
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs))


@pytest.mark.parametrize("name,value", [("model", "some-other/model-7B"), ("min_tokens", 0),
                                        ("format_reminder", True), ("temperature", 1.0), ("max_tokens", 512),
                                        ("max_steps", 30)])
def test_finish_marks_the_cell_invalid_when_a_record_setting_differs(pc, tmp_path, monkeypatch, name, value):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    recs[7]["metrics"][name] = value
    write_records(d, recs)
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "invalid" and card["records"]["setting_mismatches"] == 1
    assert name in card["invalid_reasons"][0]
    with pytest.raises(SystemExit) as exit_:
        pc.main(["summary", str(d)])
    assert exit_.value.code not in (0, None)


def test_finish_marks_the_cell_invalid_when_the_server_serves_another_model(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    write_records(d, fake_records(card["cell_id"], card["games"], lambda g, arm: True))
    monkeypatch.setattr(pc, "machine_facts", lambda url: {"served_models": ["some-other/model-7B"]})
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "invalid" and card["machine"]["served_models"] == ["some-other/model-7B"]


# Finding 3: only the card's declared (game, arm, seed) triples count.

def test_an_extra_game_is_rejected_and_never_summarised(pc, tmp_path, monkeypatch):
    """The audit's reproduction: 20 declared games with memory = placebo, plus one undeclared game where memory wins.
    Before the fix, finish said complete and summary counted 21 games (memory - placebo +0.048)."""
    d, card = prepared_cell(pc, tmp_path, monkeypatch, block="B03")
    declared = fake_records(card["cell_id"], card["games"], lambda g, arm: arm != "none")
    extra = fake_records(card["cell_id"], ["train/not-on-the-card/trial_T0"], lambda g, arm: arm == "retrieved_task")
    write_records(d, declared + extra)
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["extra"] == 3
    assert "outside the card" in after["invalid_reasons"][0]
    assert len((d / "per_unit.csv").read_text(encoding="utf-8").splitlines()) == 61  # 20 declared games x 3 arms
    with pytest.raises(pc.CellError):
        pc.summarise(declared + extra, card)
    with pytest.raises(SystemExit) as exit_:
        pc.main(["summary", str(d)])
    assert "outside the card" in str(exit_.value.code)
    s = pc.summarise(declared, card)
    assert s["games_with_all_arms"] == 20 and s["retrieved_task-placebo"]["difference"] == 0.0


def test_a_seed_mismatch_is_rejected(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    recs[0]["seed"] = 99
    write_records(d, recs)
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["seed_mismatches"] == 1
    with pytest.raises(pc.CellError, match="seed"):
        pc.summarise(recs, card)


def test_a_duplicate_is_rejected_not_silently_overwritten(pc, tmp_path, monkeypatch):
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: arm != "none")
    duplicate = dict(recs[2], solved=False)
    write_records(d, recs + [duplicate])
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "invalid" and after["records"]["duplicates"] == 1
    with pytest.raises(pc.CellError, match="more than once"):
        pc.summarise(recs + [duplicate], card)


# The prompt the agent actually sends, compared with the version's template (no GPU, no ALFWorld).

class FakeEnv:
    def __init__(self):
        self.t = 0

    def reset(self):
        return ("-= Welcome to TextWorld, ALFRED! =-\n\nYou are in the middle of a room.\n\n"
                "Your task is to: put a mug in sinkbasin."), {"admissible_commands": ["go to sinkbasin 1", "help"],
                                                               "won": False}

    def step(self, action):
        self.t += 1
        return f"You arrive at sinkbasin {self.t}.", 0, self.t >= 2, {"won": self.t >= 2,
                                                                       "admissible_commands": ["look"]}

    def close(self):
        pass


def fake_alfworld(monkeypatch):
    import types
    tw = types.ModuleType("textworld")
    gym = types.ModuleType("textworld.gym")
    tw.EnvInfos = lambda **kw: kw
    gym.register_game = lambda *a, **kw: "env-id"
    gym.make = lambda env_id: FakeEnv()
    tw.gym = gym
    alfred = types.ModuleType("alfworld.agents.environment.alfred_tw_env")
    alfred.AlfredDemangler, alfred.AlfredInfos = object, object
    for name, module in {"textworld": tw, "textworld.gym": gym, "alfworld": types.ModuleType("alfworld"),
                         "alfworld.agents": types.ModuleType("alfworld.agents"),
                         "alfworld.agents.environment": types.ModuleType("alfworld.agents.environment"),
                         "alfworld.agents.environment.alfred_tw_env": alfred}.items():
        monkeypatch.setitem(sys.modules, name, module)


TASK = "train/pick_and_place_simple-Mug-None-SinkBasin-9/trial_T0"
BANK = [{"task": f"train/pick_and_place_simple-Mug-None-SinkBasin-{i}/trial_T0", "type": "pick_and_place_simple",
         "family": f"pick_and_place_simple-Mug-None-SinkBasin-{i}",
         "initial_observation": "You are in a kitchen.\n\nYour task is to: put a mug in sinkbasin.",
         "steps": [{"observation": "You pick up the mug.", "action": "take mug 1 from countertop 1"}]} for i in (1, 2)]


@pytest.mark.parametrize("arm", ["none", "retrieved_task"])
@pytest.mark.parametrize("reminder", [False, True])
def test_the_agent_prompt_equals_the_version_template(pc, monkeypatch, arm, reminder):
    """Runs agent.episode on a fake two-step game and compares every prompt it sends with
    instrument/prompt_template.txt (the V3/V4 pin), plus the V5 reminder only when it is switched on."""
    fake_alfworld(monkeypatch)
    agent = pc.load_agent(reminder)
    agent.DATA_ROOT, agent.BANK = "/nowhere", [dict(b) for b in BANK]
    for b in agent.BANK:
        b["goal"] = agent.goal_of(b["initial_observation"])
    monkeypatch.setattr(agent, "count_tokens", lambda text: len(text.split()))
    prompts = []

    def chat(prompt, seed):
        prompts.append(prompt)
        return "<think>go</think><action>go to sinkbasin 1</action>", 10, 0, "stop"

    monkeypatch.setattr(agent, "chat", chat)
    record = agent.episode({"unit": f"u~{TASK}", "task": TASK, "arm": arm, "seed": 1})
    assert record["solved"] is True and len(prompts) == 2
    assert record["metrics"]["format_reminder"] is reminder and record["metrics"]["model"] == pc.V3V4_MODEL

    t = pc.template_sections((TOOLS / "instrument" / "prompt_template.txt").read_text(encoding="utf-8"))
    if arm == "none":
        tail = t["ACTION_INSTR"]
    else:
        block, _ = agent.choose_memory(TASK, "put a mug in sinkbasin", arm, 1, agent.BANK)
        tail = t["MEMORY_WRAPPER"].replace("{retrieved_exp}", block)
    if reminder:
        tail += "\n\n" + agent.FORMAT_REMINDER.strip()
    first_obs = "You are in the middle of a room.\n\nYour task is to: put a mug in sinkbasin."
    step1 = t["TEMPLATE_NO_HIS"].format(current_observation=first_obs, admissible_actions="'go to sinkbasin 1'")
    assert prompts[0].strip() == step1 + "\n\n" + tail
    step2 = t["TEMPLATE"].format(
        task_description="put a mug in sinkbasin", step_count=1, history_length=1,
        action_history=f"[Observation 1: '{first_obs}', Action 1: 'go to sinkbasin 1']",
        current_step=2, current_observation="You arrive at sinkbasin 1.", admissible_actions="'look'")
    assert prompts[1].strip() == step2 + "\n\n" + tail


def test_a_torn_last_line_is_set_aside_and_its_job_runs_again(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    spy_run(monkeypatch, pc, writes=recs[:20])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    card = json.loads((d / "card.json").read_text())
    open_receipt(card)  # power cut while the 21st record was being written
    (d / "card.json").write_text(json.dumps(card))
    with open(d / "records.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(recs[20])[:25])
    jobs = spy_jobs(monkeypatch, pc, writes=recs[20:])
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    assert jobs == [40]  # the torn record's job runs again
    assert (d / "records.torn.jsonl").read_text(encoding="utf-8") == json.dumps(recs[20])[:25] + "\n"
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    rec = after["archive"]["receipts"][0]["recovery"]
    assert rec["torn_fragment_bytes"] == 25 and rec["appended_record_lines"] == 20
    assert after["status"] == "complete-recovered" and len(after["recovered_unverified_jobs"]) == 20


def test_a_run_without_recovery_stays_plain_complete(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, card = prepared_cell(pc, tmp_path, monkeypatch)
    spy_run(monkeypatch, pc, writes=fake_records(card["cell_id"], card["games"], lambda g, arm: True))
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    pc.main(["finish", str(d)])
    after = json.loads((d / "card.json").read_text())
    assert after["status"] == "complete" and after["recovered_unverified_jobs"] == []


def test_an_upgrade_interrupted_before_the_move_is_finished_on_retry(pc, tmp_path, monkeypatch):
    base, data_root = fake_archive(pc, monkeypatch, tmp_path, "B05")
    d, _ = prepared_cell(pc, tmp_path, monkeypatch)
    card = legacy_card(pc, d)
    recs = fake_records(card["cell_id"], card["games"], lambda g, arm: True)
    write_records(d, recs[:10])
    real_replace = pc.os.replace

    def crash(src, dst):
        raise KeyboardInterrupt("power cut")

    monkeypatch.setattr(pc.os, "replace", crash)
    calls = spy_run(monkeypatch, pc)
    with pytest.raises(KeyboardInterrupt):
        pc.main(["run", str(d), "--data-root", str(data_root)])
    assert calls == [] and json.loads((d / "card.json").read_text())["archive"]["upgraded_from_legacy"][
        "pre_receipt"]["moved"] is False
    monkeypatch.setattr(pc.os, "replace", real_replace)
    jobs = spy_jobs(monkeypatch, pc, writes=recs)
    assert run_cell(pc, d, "--data-root", str(data_root)) == 0
    assert jobs == [60] and (d / "records.pre_receipt.jsonl").exists()
    after = json.loads((d / "card.json").read_text())
    assert after["archive"]["upgraded_from_legacy"]["pre_receipt"]["moved"] is True
    pc.main(["finish", str(d)])
    assert json.loads((d / "card.json").read_text())["status"] == "complete"
