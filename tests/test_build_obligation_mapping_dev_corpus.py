import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_obligation_mapping_dev_corpus.py"
SPEC = importlib.util.spec_from_file_location("build_obligation_mapping_dev_corpus", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_sources_validate_and_cover_every_operator():
    data_dir = ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
    schema = MODULE.read_json(data_dir / "schema-v0.json")
    entities = MODULE.read_json(data_dir / "entities-v0.json")
    groups = MODULE.read_jsonl(data_dir / "template-groups.jsonl")
    MODULE.validate_sources(schema, entities, groups)
    covered = {node["op"] for group in groups for node in group["nodes"]}
    assert covered == MODULE.OPERATORS


def test_bilingual_groups_build_to_two_cases_without_gold_in_model_payload():
    case_text, model_text, manifest_text = MODULE.build(ROOT)
    cases = MODULE.read_jsonl_from_text(case_text) if hasattr(MODULE, "read_jsonl_from_text") else [MODULE.json.loads(line) for line in case_text.splitlines()]
    model_cases = [MODULE.json.loads(line) for line in model_text.splitlines()]
    manifest = MODULE.json.loads(manifest_text)
    assert manifest["template_group_count"] == 28
    assert manifest["case_count"] == 56
    assert manifest["equivalence_fixture_count"] == 4
    assert len(cases) == len(model_cases) == 56
    assert {case["language"] for case in cases} == {"en", "pl"}
    assert all("graph" not in row and "evaluation_metadata" not in row for row in model_cases)


def test_equivalence_fixtures_cover_both_metric_disagreements():
    data_dir = ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
    fixtures = MODULE.read_jsonl(data_dir / "equivalence-fixtures.jsonl")
    MODULE.validate_equivalence_fixtures(fixtures)
    assert {item["class"] for item in fixtures} == {
        "different-structure-same-denotation",
        "same-structure-different-denotation",
    }


def test_unsafe_resolution_states_do_not_receive_applicable_certificates():
    case_text, _, _ = MODULE.build(ROOT)
    cases = [MODULE.json.loads(line) for line in case_text.splitlines()]
    unsafe_statuses = {"ambiguous", "unauthorized", "unsupported_structure"}
    forbidden = {"applicable", "explicit-negative", "requires-complete-scope"}
    for case in cases:
        if case["query_status"] in unsafe_statuses:
            assert all(node["certificate_query"]["status"] not in forbidden for node in case["graph"]["nodes"])
