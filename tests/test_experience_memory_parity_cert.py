"""The parity certificate of experience_memory is recomputed from its log and checked against git and the
published V5B program record, the same conditions the lab's goal code (milestone M4) checks."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "experience_memory" / "parity"))
import make_parity_cert as mpc  # noqa: E402
import check_v5b_parity as parity  # noqa: E402

CERT = json.loads((REPO / mpc.CERT).read_text(encoding="utf-8"))
LOG = (REPO / mpc.LOG).read_text(encoding="utf-8")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def test_certificate_equals_the_one_recomputed_from_the_log():
    have = (REPO / mpc.CERT).read_text(encoding="utf-8").replace("\r\n", "\n")
    assert have == mpc.render(mpc.build_cert(LOG))


def test_log_digest_and_result():
    assert CERT["test"]["log"] == mpc.LOG
    assert CERT["test"]["log_sha256"] == mpc.lf_sha256(LOG)
    header, summary = mpc.parse_log(LOG)
    assert summary["mismatch_count"] == 0 == CERT["test"]["mismatches"]
    assert summary["inputs_match_v5b_pins"] is True and summary["mode"] == "private"
    assert summary["units_with_exclusions"] == 0
    n = CERT["unit_set"]["n"]
    assert n == summary["queries"] and CERT["test"]["comparisons"] == summary["comparisons"] >= n
    assert summary["comparisons"] == n * len(summary["seeds"])
    assert "MISMATCH" not in LOG


def test_instrument_and_units_match_the_published_program_record():
    env = mpc.program_envelope()
    assert CERT["program"] == mpc.PROGRAM == env["id"]
    assert CERT["instrument"]["pins"] == sorted(str(v) for v in env["instrument"]["sha256"].values())
    assert CERT["instrument"]["files"] == mpc.instrument_files(env)
    assert CERT["instrument"]["units_sha256"] == env["domain_params"]["units_sha256"]


def test_runner_pins_and_command_are_the_parity_checks_own():
    assert CERT["instrument"]["runner_pins"] == parity.V5B_PINS
    assert CERT["instrument"]["units_sha256"] == parity.V5B_PINS["data/units.json"]
    assert CERT["test"]["command"] == mpc.COMMAND
    assert CERT["test"]["parity_script_sha256"] == mpc.lf_sha256((REPO / mpc.PARITY_SCRIPT).read_text(encoding="utf-8")), (
        "the parity script changed after the certified run: re-run make_parity_cert.py run and build on the lab machine")


def test_component_pins_a_commit_version_and_unchanged_code():
    comp = CERT["component"]
    assert comp["name"] == mpc.NAME and re.fullmatch(r"[0-9a-f]{40}", comp["commit"])
    if git("cat-file", "-e", comp["commit"] + "^{commit}").returncode != 0:
        pytest.skip("the certified commit is not in this clone (shallow checkout)")
    assert git("merge-base", "--is-ancestor", comp["commit"], "HEAD").returncode == 0
    at_commit = git("show", f"{comp['commit']}:{mpc.PACKAGE_INIT}").stdout
    assert re.search(r"^__version__\s*=\s*[\"']" + re.escape(comp["version"]) + r"[\"']\s*$", at_commit, re.M)
    diff = git("diff", "--name-only", comp["commit"], "--", mpc.PACKAGE_DIR)
    assert diff.returncode == 0 and not diff.stdout.strip(), (
        "the package code differs from the certified commit: the certificate is stale. Re-run "
        "`python tools/experience_memory/parity/make_parity_cert.py run` and `build` on the lab machine")


def test_build_refuses_a_failing_or_foreign_log():
    with pytest.raises(ValueError):
        mpc.build_cert(LOG.replace('"mismatch_count": 0', '"mismatch_count": 1'))
    with pytest.raises(ValueError):
        mpc.build_cert(LOG.replace("PASS: 0 mismatches", "FAIL: 1 mismatch(es)"))
    with pytest.raises(ValueError):
        mpc.build_cert(LOG.replace('"mode": "private"', '"mode": "public"'))
    with pytest.raises(ValueError):
        mpc.build_cert("something else\n")
