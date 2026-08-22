from __future__ import annotations

import unittest

from scripts import run_fault_probe_comparison as probes


class FaultProbeComparisonTests(unittest.TestCase):
    def test_factorial_size_and_unique_ids(self) -> None:
        cases = probes.make_cases()
        self.assertEqual(174, len(cases))
        self.assertEqual(174, len({case["case_id"] for case in cases}))

    def test_passive_trace_cascades_after_first_fault(self) -> None:
        trace = probes.passive_trace(["F2", "F4"], "complete")
        self.assertTrue(trace["F1"])
        self.assertFalse(trace["F2"])
        self.assertFalse(trace["F3"])
        self.assertFalse(trace["F4"])
        self.assertEqual(["F2"], probes.diagnose_passive(trace)["fault_stages"])

    def test_active_probes_reveal_masked_faults(self) -> None:
        active = probes.active_probes(["F2", "F4"], None)
        self.assertEqual(["F2", "F4"], probes.diagnose_active(active)["fault_stages"])

    def test_active_probes_separate_loss_from_recoverable_storage_fault(self) -> None:
        lost = probes.diagnose_active(probes.active_probes(["F1"], "physical-loss"))
        recoverable = probes.diagnose_active(probes.active_probes(["F1"], "recoverable-schema"))
        self.assertTrue(lost["physical_data_loss"])
        self.assertFalse(recoverable["physical_data_loss"])

    def test_active_arm_is_exact_on_authored_instrument(self) -> None:
        cases = probes.make_cases()
        for case in cases:
            diagnosis = probes.diagnose_active(case["active_probes"])
            self.assertEqual(case["fault_stages"], diagnosis["fault_stages"])
            self.assertEqual(case["physical_data_loss"], diagnosis["physical_data_loss"])


if __name__ == "__main__":
    unittest.main()
