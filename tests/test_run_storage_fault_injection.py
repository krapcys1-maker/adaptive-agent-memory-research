from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import run_storage_fault_injection as storage


class StorageFaultInjectionTests(unittest.TestCase):
    def test_temp_root_guard_rejects_non_temp_path(self) -> None:
        with self.assertRaises(ValueError):
            storage.safe_temp_root(Path.cwd())

    def test_every_injection_classifies_without_physical_loss_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pmlab-storage-") as temporary:
            root = storage.safe_temp_root(Path(temporary))
            for injection in storage.INJECTIONS:
                row = storage.execute_trial(root, injection, 0)
                self.assertEqual(storage.EXPECTED[injection], row["predicted_outcome"])
                self.assertFalse(row["physical_loss_confirmed"])

    def test_same_device_loss_uses_logical_label(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pmlab-storage-") as temporary:
            root = storage.safe_temp_root(Path(temporary))
            row = storage.execute_trial(root, "both-missing", 0)
            self.assertEqual("LOGICAL_REPLICA_LOSS", row["predicted_outcome"])
            self.assertNotEqual("PHYSICAL_LOSS_CONFIRMED", row["predicted_outcome"])


if __name__ == "__main__":
    unittest.main()
