"""Installer boundaries: isolated homes and inert external-command stubs only."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


@unittest.skipUnless(BASH and os.name != "nt", "Unix Bash entry points")
class ShellEntryPoints(unittest.TestCase):
    def test_install_dispatch_preserves_source_and_argument_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source with spaces"
            (source / "scripts").mkdir(parents=True)
            wrapper = source / "scripts/install.sh"
            shutil.copyfile(ROOT / "scripts/install.sh", wrapper)
            (source / "install.py").write_text("# inert source fixture\n")
            interpreter = base / "python with spaces"
            interpreter.write_text(
                "#!" + sys.executable + "\nimport json, sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
            )
            interpreter.chmod(0o755)
            arguments = ["--config", "a file with spaces.json", "--state", "literal;$(printf bad)"]
            result = subprocess.run(
                [BASH, str(wrapper), *arguments], capture_output=True, text=True,
                env=dict(os.environ, UPDATEWULF_PYTHON=str(interpreter)), check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), [str(source / "install.py"), *arguments])

    def test_help_does_not_create_home_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = subprocess.run(
                [BASH, str(ROOT / "scripts/install.sh"), "--help"],
                capture_output=True, text=True, check=False,
                env=dict(os.environ, HOME=str(home), UPDATEWULF_PYTHON=sys.executable,
                         PYTHONDONTWRITEBYTECODE="1"),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--prompt-only", result.stdout)
            self.assertEqual(list(home.iterdir()), [])

    def test_missing_interpreter_fails_without_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [BASH, str(ROOT / "scripts/install.sh"), "--help"],
                capture_output=True, text=True, check=False,
                env=dict(os.environ, UPDATEWULF_PYTHON=str(Path(directory) / "missing-python")),
            )
            self.assertEqual(result.returncode, 127)
            self.assertIn("Python", result.stderr)

    def test_uninstall_never_invokes_external_commands_or_claims_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            commands = base / "commands"
            commands.mkdir()
            log = base / "commands.log"
            # The old script is harmless even if this test is run as root:
            # every external command it could execute is an inert recorder.
            for name in ("id", "systemctl", "rm"):
                stub = commands / name
                stub.write_text(
                    "#!" + BASH + "\n"
                    'printf "%s\\n" "$0 $*" >> "$UPDATEWULF_TEST_COMMAND_LOG"\n'
                    + ('printf "0\\n"\n' if name == "id" else "")
                )
                stub.chmod(0o755)
            sentinel = base / "preserve.txt"
            sentinel.write_text("untouched")
            env = dict(os.environ, PATH=str(commands), UPDATEWULF_TEST_COMMAND_LOG=str(log))
            for arguments, expected in (([], 2), (["--purge-config", "--purge-state"], 2), (["--help"], 0)):
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        [BASH, str(ROOT / "scripts/uninstall.sh"), *arguments],
                        capture_output=True, text=True, env=env, check=False,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertIn("docs/installation.md#uninstall", result.stdout + result.stderr)
                    self.assertNotIn("removed.", result.stdout + result.stderr)
                    self.assertFalse(log.exists(), "uninstaller invoked a system command")
                    self.assertEqual(sentinel.read_text(), "untouched")


@unittest.skipIf(os.name == "nt", "Unix user installer")
class UserInstallerPreflight(unittest.TestCase):
    def invoke(self, home, *arguments):
        with patch.object(Path, "home", return_value=home), \
             patch.object(sys, "argv", ["install.py", *arguments]), \
             patch.object(install, "read_crontab", side_effect=AssertionError("unexpected cron access")), \
             patch.object(install, "enable_user_service", side_effect=AssertionError("unexpected service access")), \
             patch.object(install, "enable_boot_fallback", side_effect=AssertionError("unexpected worker launch")), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return install.main()

    def test_missing_config_preserves_existing_profile_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            profile = home / ".bashrc"
            profile.write_text("# owner configuration\n")
            with self.assertRaises(SystemExit) as raised:
                self.invoke(home, "--source", str(ROOT))
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(profile.read_text(), "# owner configuration\n")
            self.assertEqual(list(home.iterdir()), [profile])

    def test_missing_source_is_rejected_before_creating_hook_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            home = base / "home"
            home.mkdir()
            with self.assertRaises(SystemExit) as raised:
                self.invoke(home, "--prompt-only", "--source", str(base / "missing-source"))
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(list(home.iterdir()), [])

    def test_missing_hook_is_rejected_before_any_profile_write(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            for name in ("pc_mesh.py", "update_control.py", "apply_updates.py", "self_update.py", "tui.py", "owner_profiles.py"):
                (source / name).write_text("# fixture\n")
            home = base / "home"
            home.mkdir()
            with self.assertRaises(SystemExit) as raised:
                self.invoke(home, "--prompt-only", "--source", str(source))
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(list(home.iterdir()), [])

    def test_invalid_config_is_rejected_before_any_profile_write(self):
        for content in ("not json", "[]"):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                config = home / "config.json"
                config.write_text(content)
                with self.assertRaises(SystemExit) as raised:
                    self.invoke(home, "--source", str(ROOT), "--config", str(config))
                self.assertEqual(raised.exception.code, 2)
                self.assertEqual(list(home.iterdir()), [config])

    def test_prompt_only_works_without_config_and_never_starts_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.invoke(home, "--source", str(ROOT), "--prompt-only")
            self.assertTrue((home / ".local/bin/updatewulf").is_file())
            self.assertTrue((home / ".config/pc-mesh/prompt.bash").is_file())
            self.assertFalse((home / ".config/pc-mesh/config.json").exists())
            self.assertFalse((home / ".local/state/pc-mesh").exists())


if __name__ == "__main__":
    unittest.main()
