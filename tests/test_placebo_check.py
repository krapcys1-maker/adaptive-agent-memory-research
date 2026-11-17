"""CPU tests of the placebo-check cell tool and its frozen pools (no GPU, no model, no ALFWorld install)."""
import importlib.util
import json
import pathlib

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
    d = tmp_path / "placebo-v4-B00-r2-mt0"
    batch = [json.loads(l) for l in (d / "batch.jsonl").read_text().splitlines()]
    card = json.loads((d / "card.json").read_text())
    assert len(batch) == 60 and {b["arm"] for b in batch} == set(pc.ARMS)
    assert all(b["seed"] == 2 and b["unit"].startswith("placebo-v4-B00-r2-mt0~") for b in batch)
    assert card["fixed"]["min_tokens"] == 0 and card["fixed"]["sha256"]["bank"] == pc.sha_file(pc.FIXED_FILES["bank"])
    with pytest.raises(SystemExit):
        pc.main(["prepare", "--block", "B99"])


def fake_records(cid, games, solved):
    out = []
    for g in games:
        for arm in ("none", "placebo", "retrieved_task"):
            out.append({"unit": f"{cid}~{g}", "arm": arm, "seed": 1, "solved": solved(g, arm), "memory_sources": [],
                        "metrics": {"steps": 10, "empty_retries": 2 if arm == "none" else 0,
                                    "invalid_no_action_tag": 1, "memory_tokens": 0 if arm == "none" else 800}})
    return out


def test_finish_and_summary(pc, tmp_path, monkeypatch):
    pc.main(["prepare", "--block", "B01"])
    d = tmp_path / "placebo-v4-B01-r1-mt8"
    card = json.loads((d / "card.json").read_text())
    games = card["games"]
    recs = fake_records(card["cell_id"], games, lambda g, arm: arm != "none" or g == games[0])
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs[:-1]))
    monkeypatch.setattr(pc, "machine_facts", lambda url: {"gpu": "TEST"})
    pc.main(["finish", str(d)])
    assert json.loads((d / "card.json").read_text())["status"] == "incomplete"
    (d / "records.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    pc.main(["finish", str(d)])
    card = json.loads((d / "card.json").read_text())
    assert card["status"] == "complete" and card["machine"]["gpu"] == "TEST"
    assert card["block"] == "B01" and len(card["block_games_sha256"]) == 64 and len(card["pools_file_sha256"]) == 64
    rows = (d / "per_unit.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == ("unit,task,arm,seed,solved,steps,empty_retries,invalid_no_action_tag,invalid_actions,"
                       "memory_tokens,truncated,untagged_not_truncated")
    assert len(rows) == 61
    s = pc.summarise(recs)
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
