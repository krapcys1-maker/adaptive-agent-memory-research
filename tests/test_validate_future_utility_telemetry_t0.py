import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_future_utility_telemetry_t0.py"
SPEC = importlib.util.spec_from_file_location("utility_t0", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FutureUtilityTelemetryT0Tests(unittest.TestCase):
    def test_valid_fixture_exercises_retry_correction_and_censoring(self):
        report = MODULE.build_report()
        valid = report["valid_stream"]
        self.assertEqual(report["status"], "synthetic-schema-validation-passed")
        self.assertEqual(valid["deliveries"], 24)
        self.assertEqual(valid["logical_events"], 23)
        self.assertEqual(valid["exact_retries_collapsed"], 1)
        self.assertEqual(valid["correction_count"], 1)
        self.assertEqual(valid["censored_task_count"], 1)
        self.assertEqual(valid["causal_effect_event_count"], 0)

    def test_all_invalid_fixtures_are_rejected_for_registered_reason(self):
        report = MODULE.build_report()
        self.assertEqual(report["invalid_cases"]["total"], 18)
        self.assertEqual(report["invalid_cases"]["rejected"], 18)
        self.assertEqual(
            len({row["case_id"] for row in report["invalid_cases"]["results"]}),
            18,
        )

    def test_correction_preserves_original_delivery(self):
        events = MODULE.load_jsonl(MODULE.VALID)
        cost = next(event for event in events if event["event_id"] == "TE-000000000000000E")
        original = copy.deepcopy(cost)
        MODULE.validate_stream(events)
        self.assertEqual(cost, original)
        self.assertEqual(cost["payload"]["usd"], 0.0013)
        correction = next(event for event in events if event["event_type"] == "correction")
        self.assertEqual(correction["payload"]["field_corrections"]["/payload/usd"], 0.0014)

    def test_observation_levels_do_not_emit_u5(self):
        report = MODULE.build_report()
        levels = report["valid_stream"]["maximum_observational_level_counts"]
        self.assertEqual(levels, {"U1": 1, "U2": 1, "U3": 0, "U4": 1})
        self.assertNotIn("U5", levels)

    def test_report_is_byte_deterministic(self):
        expected = json.dumps(MODULE.build_report(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        self.assertEqual(MODULE.REPORT.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
