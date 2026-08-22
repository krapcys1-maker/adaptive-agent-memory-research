import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_obligation_mapping_deepseek.py"
SPEC = importlib.util.spec_from_file_location("run_obligation_mapping_deepseek", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_batches_never_mix_bilingual_pairs():
    jobs = MODULE.read_jsonl(MODULE.RUN_DIR / "jobs.jsonl")
    for batch in MODULE.batches_by_language(jobs, 7):
        assert len({item["language"] for item in batch}) == 1
        groups = [item["query_id"].rsplit("-", 1)[0] for item in batch]
        assert len(groups) == len(set(groups))


def test_validator_rejects_applicable_certificate_for_ambiguous_case():
    batch = [{"query_id": "X", "raw_query": "Who owns Mercury?"}]
    schema = json.loads((ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "schema-v0.json").read_text(encoding="utf-8"))
    content = json.dumps({"results": [{"query_id": "X", "query_status": "ambiguous", "nodes": [{"obligation_id": "O1", "operator": "SELECT", "span_text": "Mercury", "depends": [], "entity": "ambiguous:project:mercury,person:mercury", "predicate": "project.owner", "namespaces": ["canonical-events"], "time": "current", "authorization": "allowed", "certificate": "applicable"}]}]})
    try:
        MODULE.validate_response(content, batch, schema)
    except ValueError as exc:
        assert "unsafe certificate" in str(exc)
    else:
        raise AssertionError("unsafe ambiguous certificate was accepted")
