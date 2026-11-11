"""Fail-closed UpdateWulf self-update behavior; never contacts a real network."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import self_update as updater

A = "a" * 40
B = "b" * 40

class SelfUpdateSafety(unittest.TestCase):
    def test_branch_rejects_injection_and_invalid_git_refs(self):
        for value in ("", "../main", "/main", "main..test", "main//test",
                      "main.lock", "main/", "main\n-hello", "ref@{head}"):
            with self.subTest(value=value), self.assertRaises(updater.UpdateError):
                updater.validate_branch(value)
        self.assertEqual(updater.validate_branch("integration/multi-os-updatewulf-v2"),
                         "integration/multi-os-updatewulf-v2")

    def test_missing_deployed_identity_requires_manual_bootstrap(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            with patch.object(updater, "release_root", return_value=source / "releases"):
                with self.assertRaisesRegex(updater.UpdateError, "bootstrap"):
                    updater.apply(updater.DEFAULT_BRANCH, source)
                self.assertFalse((source / "releases" / ".apply.lock").exists())

    def test_marker_accepts_only_complete_sha(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            self.assertIsNone(updater.current_sha(source))
            (source / "DEPLOYED_COMMIT").write_text("short\n", encoding="ascii")
            self.assertIsNone(updater.current_sha(source))
            (source / "DEPLOYED_COMMIT").write_text(A + "\n", encoding="ascii")
            self.assertEqual(updater.current_sha(source), A)

    def test_ls_remote_ref_is_exact_and_checked(self):
        from subprocess import CompletedProcess
        with patch.object(updater, "call", return_value=CompletedProcess([], 0,
                  A + "\trefs/heads/" + updater.DEFAULT_BRANCH + "\n", "")):
            self.assertEqual(updater.remote_sha(updater.DEFAULT_BRANCH), A)
        with patch.object(updater, "call", return_value=CompletedProcess([], 0,
                  A + "\trefs/heads/other\n", "")):
            with self.assertRaisesRegex(updater.UpdateError, "unexpected"):
                updater.remote_sha(updater.DEFAULT_BRANCH)

    def test_windows_read_only_git_object_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / ".git"
            (target / "objects").mkdir(parents=True)
            object_file = target / "objects" / "packed.idx"
            object_file.write_text("fixture", encoding="ascii")
            object_file.chmod(0o444)
            import shutil
            shutil.rmtree(target, onerror=updater._make_writable_and_retry)
            self.assertFalse(target.exists())

    def test_up_to_date_never_activates(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            (source / "DEPLOYED_COMMIT").write_text(A + "\n", encoding="ascii")
            with patch.object(updater, "release_root", return_value=source / "releases"), \
                 patch.object(updater, "remote_sha", return_value=A), \
                 patch.object(updater, "install") as install:
                self.assertEqual(updater.apply(updater.DEFAULT_BRANCH, source), 0)
                install.assert_not_called()

    def test_untrusted_release_does_not_get_installed(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)
            (source / "DEPLOYED_COMMIT").write_text(A + "\n", encoding="ascii")
            with patch.object(updater, "release_root", return_value=source / "releases"), \
                 patch.object(updater, "remote_sha", return_value=B), \
                 patch.object(updater, "verified_checkout", side_effect=updater.UpdateError("invalid ancestry")), \
                 patch.object(updater, "install") as install:
                with self.assertRaisesRegex(updater.UpdateError, "ancestry"):
                    updater.apply(updater.DEFAULT_BRANCH, source)
                install.assert_not_called()

if __name__ == "__main__":
    unittest.main()
