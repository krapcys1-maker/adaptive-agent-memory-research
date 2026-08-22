import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"


class PmlabMapStageDesignTests(unittest.TestCase):
    def test_allocation_totals_and_stages_match_schema(self):
        schema = json.loads((DATA / "case-schema-v1.json").read_text(encoding="utf-8"))
        with (DATA / "case-allocation-v1.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        data_rows = [row for row in rows if row["stage"] != "TOTAL"]
        total = next(row for row in rows if row["stage"] == "TOTAL")
        self.assertEqual({row["stage"] for row in data_rows}, set(schema["allowed_stages"]))
        self.assertEqual(sum(int(row["dev_semantic_groups"]) for row in data_rows), int(total["dev_semantic_groups"]))
        self.assertEqual(sum(int(row["later_challenge_groups"]) for row in data_rows), int(total["later_challenge_groups"]))

    def test_every_stage_has_required_metrics(self):
        schema = json.loads((DATA / "case-schema-v1.json").read_text(encoding="utf-8"))
        for stage in schema["allowed_stages"]:
            self.assertTrue(schema["stage_outputs"][stage]["required_metrics"])


if __name__ == "__main__":
    unittest.main()
