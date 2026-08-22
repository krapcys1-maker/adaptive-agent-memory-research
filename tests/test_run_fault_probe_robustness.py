from __future__ import annotations

import unittest

from scripts import run_fault_probe_robustness as robust


class FaultProbeRobustnessTests(unittest.TestCase):
    def test_matrix_size_and_ids(self) -> None:
        cases = robust.make_cases()
        self.assertEqual(58 * 34, len(cases))
        self.assertEqual(len(cases), len({case["case_id"] for case in cases}))

    def test_repeat_all_repairs_single_transient_flip_and_timeout(self) -> None:
        truth = robust.truth_probes(["F2"], None)
        for noise_class in ("transient-flip", "transient-timeout"):
            scenario = {"scenario": f"{noise_class}:oracle_query_retrieval_probe", "noise_class": noise_class, "target_probe": "oracle_query_retrieval_probe"}
            observed = robust.observations(truth, scenario)
            diagnosis, _ = robust.run_arm(observed, "repeat-all-naive")
            self.assertEqual(["F2"], diagnosis["fault_stages"])

    def test_adaptive_abnormal_misses_transient_false_healthy(self) -> None:
        truth = robust.truth_probes(["F2"], None)
        scenario = {"scenario": "transient-flip:oracle_query_retrieval_probe", "noise_class": "transient-flip", "target_probe": "oracle_query_retrieval_probe"}
        diagnosis, _ = robust.run_arm(robust.observations(truth, scenario), "adaptive-abnormal-naive")
        self.assertNotIn("F2", diagnosis["fault_stages"])

    def test_diverse_gate_avoids_correlated_recovery_false_positive(self) -> None:
        truth = robust.truth_probes([], None)
        scenario = {"scenario": "correlated-storage-false", "noise_class": "correlated", "target_probe": "recovery-triad"}
        observed = robust.observations(truth, scenario)
        naive, _ = robust.run_arm(observed, "repeat-all-naive")
        diverse, _ = robust.run_arm(observed, "adaptive-storage-diverse")
        self.assertTrue(naive["physical_data_loss"])
        self.assertIsNone(diverse["physical_data_loss"])

    def test_diverse_gate_abstains_on_false_healthy_loss_signal(self) -> None:
        truth = robust.truth_probes(["F1"], "physical-loss")
        scenario = {"scenario": "persistent-flip:direct_id_found", "noise_class": "persistent-flip", "target_probe": "direct_id_found"}
        diagnosis, _ = robust.run_arm(robust.observations(truth, scenario), "adaptive-storage-diverse")
        self.assertIsNone(diagnosis["physical_data_loss"])

    def test_all_arms_are_exact_without_noise(self) -> None:
        clean = {"scenario": "clean", "noise_class": "clean", "target_probe": None}
        for spec in robust.fault_specs():
            observed = robust.observations(
                robust.truth_probes(spec["fault_stages"], spec["f1_mode"]), clean
            )
            for arm in ("single-naive", "repeat-all-naive", "adaptive-abnormal-naive", "adaptive-storage-diverse"):
                diagnosis, _ = robust.run_arm(observed, arm)
                self.assertEqual(spec["fault_stages"], diagnosis["fault_stages"])
                self.assertEqual(spec["f1_mode"] == "physical-loss", diagnosis["physical_data_loss"])


if __name__ == "__main__":
    unittest.main()
