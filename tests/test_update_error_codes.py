import tempfile
import unittest
from pathlib import Path

import pc_mesh
from update_control import ControlQueue


class PublicUpdateErrors(unittest.TestCase):
    def test_current_and_legacy_install_errors_expose_codes_only(self):
        with tempfile.TemporaryDirectory() as root:
            queue = ControlQueue(Path(root) / "commands.json",
                                 {"member": {"allow_install": True}},
                                 pc_mesh.read_json, pc_mesh.save_json)
            job = queue.enqueue("operator", "member", "install", "0" * 24)
            queue.result("member", job["id"], "RUNNING")
            result = queue.result("member", job["id"], "FAILED", "private native output")
            self.assertEqual(result["detail"], "UW_UPDATE_FAILED")
            queue.jobs[0]["detail"] = "legacy private output"
            queue.jobs[0]["diagnostic"] = "private preview from an old state"
            batch = [{"target": "member", "action": "install", "request_id": "0" * 24}]
            for saved in (queue.snapshot()[0],
                          queue.result("member", job["id"], "FAILED"),
                          queue.enqueue("operator", "member", "install", "0" * 24),
                          queue.enqueue_many("operator", batch)[0]):
                self.assertEqual(saved["error_code"], "UW_UPDATE_FAILED")
                self.assertEqual(saved["detail"], "UW_UPDATE_FAILED")
                self.assertNotIn("diagnostic", saved)


if __name__ == "__main__":
    unittest.main()
