"""UpdateWulf public self-update contract: offline, no network or host mutation."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pc_mesh
import self_update


class PublicUpdateContract(unittest.TestCase):
    def test_public_repository_and_stable_release_branch(self):
        self.assertEqual(self_update.REPOSITORY,
                         "https://github.com/n-e-o-w-u-l-f/UpdateWulf.git")
        self.assertEqual(self_update.DEFAULT_BRANCH, "main")

    def test_explicit_self_update_command_routes_to_updater(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d)
            argv = ["pc_mesh.py", "--self", "update", "--state", str(state)]
            with patch.object(sys, "argv", argv), \
                 patch.object(self_update, "main", return_value=0) as invoked:
                self.assertEqual(pc_mesh.main(), 0)
                options = invoked.call_args.args[0]
            self.assertIn("--apply", options)
            self.assertIn("--source", options)
            self.assertIn("--state", options)
            self.assertEqual(options[options.index("--state") + 1], str(state))
            self.assertIn("--bootstrap", options)

    def test_self_flag_cannot_trigger_remote_os_package_update(self):
        with patch.object(sys, "argv", ["pc_mesh.py", "--self", "all", "update"]), \
             patch.object(self_update, "main", return_value=0) as invoked:
            with self.assertRaises(SystemExit):
                pc_mesh.main()
            invoked.assert_not_called()

    def test_existing_public_release_preserves_ancestry_gate(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "DEPLOYED_COMMIT").write_text("a" * 40 + "\n")
            (folder / "SELF_UPDATE_ORIGIN.json").write_text(json.dumps({
                "repository": self_update.REPOSITORY, "branch": "main",
                "commit": "a" * 40
            }))
            self.assertFalse(self_update.needs_bootstrap(folder))
            with patch.object(pc_mesh, "__file__", str(folder / "pc_mesh.py")), \
                 patch.object(sys, "argv", ["pc_mesh.py", "--self", "update"]), \
                 patch.object(self_update, "main", return_value=0) as invoked:
                pc_mesh.main()
            self.assertNotIn("--bootstrap", invoked.call_args.args[0])

    def test_private_to_public_migration_requires_explicit_operator_action(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "DEPLOYED_COMMIT").write_text("a" * 40 + "\n")
            (folder / "SELF_UPDATE_ORIGIN.json").write_text(json.dumps({
                "repository": "https://github.com/n-e-o-w-u-l-f/.UpdateWulf-Service.git",
                "branch": "integration/multi-os-updatewulf-v2",
                "commit": "a" * 40
            }))
            self.assertTrue(self_update.needs_bootstrap(folder))

    def test_only_owned_obsolete_release_packages_may_be_pruned(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            root = base / "releases"
            root.mkdir()
            active = root / ("b" * 40)
            previous = root / ("a" * 40)
            obsolete = root / ("c" * 40)
            unrelated = root / "custom-data"
            config = base / "config.json"
            config.write_text('{"setting":"keep"}')
            for item in (active, previous, obsolete, unrelated):
                item.mkdir()
                (item / ("private.conf" if item == unrelated else "pc_mesh.py")).write_text("fixture")
            for item in (active, previous, obsolete):
                (item / "DEPLOYED_COMMIT").write_text(item.name + "\n")
                (item / "SELF_UPDATE_ORIGIN.json").write_text(
                    json.dumps({"repository": self_update.REPOSITORY, "commit": item.name}))
            self_update.prune_owned_releases(root, active=active, previous=previous)
            self.assertTrue(active.exists())
            self.assertTrue(previous.exists())
            self.assertTrue(unrelated.exists())
            self.assertFalse(obsolete.exists())
            self.assertEqual(config.read_text(), '{"setting":"keep"}')


if __name__ == "__main__":
    unittest.main()
