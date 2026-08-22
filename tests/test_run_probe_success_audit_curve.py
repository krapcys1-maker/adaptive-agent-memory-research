from __future__ import annotations

import unittest

from scripts import run_probe_success_audit_curve as audit


class ProbeSuccessAuditCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = audit.contributions()

    def test_contribution_count(self) -> None:
        self.assertEqual(580, len(self.rows))

    def test_curve_is_monotonic_for_localization_and_cost(self) -> None:
        points = [audit.summarize(self.rows, rate) for rate in audit.RATES]
        exact = [point["expected_exact_fault_set_accuracy"] for point in points]
        costs = [point["expected_probe_units"] for point in points]
        self.assertEqual(exact, sorted(exact))
        self.assertEqual(costs, sorted(costs))

    def test_endpoints_match_diverse_policy_and_full_repetition(self) -> None:
        zero = audit.summarize(self.rows, 0.0)
        full = audit.summarize(self.rows, 1.0)
        self.assertAlmostEqual(0.8189655172413793, zero["expected_exact_fault_set_accuracy"])
        self.assertEqual(1.0, full["expected_exact_fault_set_accuracy"])
        self.assertEqual(30.0, full["expected_probe_units"])

    def test_loss_decisions_remain_safe(self) -> None:
        for rate in audit.RATES:
            point = audit.summarize(self.rows, rate)
            self.assertEqual(0.0, point["expected_false_data_loss_rate"])
            self.assertEqual(0.0, point["expected_false_no_loss_rate"])

    def test_three_quarter_audit_passes_exact_threshold(self) -> None:
        point = audit.summarize(self.rows, 0.75)
        self.assertGreaterEqual(point["expected_exact_fault_set_accuracy"], 0.95)


if __name__ == "__main__":
    unittest.main()
