#!/usr/bin/env python3
"""Verified, rollback-aware UpdateWulf *application* self-update from GitHub.

This is NOT GitSyncWulf: it fetches only the pinned UpdateWulf application
branch into an isolated temporary directory. It never synchronizes user repos.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY = "https://github.com/n-e-o-w-u-l-f/UpdateWulf.git"
DEFAULT_BRANCH = "main"
SHA = re.compile(r"^[0-9a-f]{40}$")
REF = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,120}$")
REQUIRED = ("pc_mesh.py", "update_control.py", "apply_updates.py", "apply_windows.ps1",
            "install.py", "install_windows.ps1", "prompt_windows.ps1", "self_update.py",
            "test_update_announce.py", "tests/test_self_update.py",
            "tests/test_public_self_update.py", "tests/test_cli_hostname_prompt.py",
            "hooks/updatewulf.bash.in", "scripts/install.sh", "scripts/uninstall.sh")

class UpdateError(RuntimeError):
    pass

def validate_branch(branch):
    if (not REF.fullmatch(branch) or ".." in branch or "//" in branch
            or branch.endswith(("/", ".", ".lock")) or "@{" in branch):
        raise UpdateError("invalid GitHub release branch")
    return branch

def call(argv, *, cwd=None, timeout=120, check=True, env=None):
    environment = os.environ.copy()
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    if env:
        environment.update(env)
    try:
        result = subprocess.run(argv, cwd=cwd, env=environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateError("tool failed or timed out: " + str(argv[0])) from exc
    if check and result.returncode:
        # Avoid leaking credential helper output, URLs with embedded tokens, etc.
        raise UpdateError("%s failed (exit %d)" % (argv[0], result.returncode))
    return result

def current_sha(source):
    path = source / "DEPLOYED_COMMIT"
    if not path.is_file():
        return None
    value = path.read_text(encoding="ascii").strip()
    return value if SHA.fullmatch(value) else None

def needs_bootstrap(source):
    """Only the first explicit private-to-public migration skips ancestry.

    A previously installed public release must have a matching commit and
    origin marker. Malformed or missing markers are treated as legacy.
    """
    source = Path(source)
    installed = current_sha(source)
    if not installed:
        return True
    try:
        origin = json.loads((source / "SELF_UPDATE_ORIGIN.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return True
    return not (isinstance(origin, dict) and origin.get("repository") == REPOSITORY
                and origin.get("commit") == installed)


def remote_sha(branch):
    branch = validate_branch(branch)
    response = call(["git", "ls-remote", "--exit-code", "--heads", REPOSITORY,
                     "refs/heads/" + branch], timeout=30).stdout.strip().splitlines()
    if len(response) != 1:
        raise UpdateError("GitHub returned an ambiguous release ref")
    parts = response[0].split()
    if (len(parts) != 2 or not SHA.fullmatch(parts[0])
            or parts[1] != "refs/heads/" + branch):
        raise UpdateError("unexpected GitHub ref response")
    return parts[0]

def release_root():
    # App-owned, not a user's source checkout or GitSyncWulf worktree.
    return Path.home() / ".local" / "share" / "updatewulf" / "releases"

# Only these app-owned names may occur in an obsolete release eligible for
# deletion. Unknown user data, even inside a release, blocks removal.
OWNED_RELEASE_FILES = frozenset((
    ".gitignore", ".gitattributes", "AGENTS.md", "README.md", "LICENSE",
    "DEPLOYED_COMMIT", "SELF_UPDATE_ORIGIN.json", "pc_mesh.py",
    "update_control.py", "apply_updates.py", "apply_windows.ps1",
    "collect_windows.ps1", "install.py", "install_windows.ps1",
    "prompt_windows.ps1", "self_update.py", "tui.py", "owner_profiles.py",
    "install_netbsd_root_cli.py", "enable_machine_updates.py",
    "enable_machine_updates_netbsd.py", "enable_machine_updates_windows.ps1",
    "enable_fixed_installer_windows.ps1", "install_termux.py",
    "termux_supervisor.py", "machine_installer.py", "enroll.py",
    "enroll_machine_transport.py", "enroll_transport.py",
    "bootstrap_windows_git.ps1", "bootstrap_windows_python.ps1",
    "register_keys.py", "verify_windows.ps1", "test_update_announce.py",
))
OWNED_RELEASE_DIRECTORIES = frozenset(("hooks", "scripts", "tests", "__pycache__"))


def prune_owned_releases(root, *, active, previous=None):
    """Remove *only* superseded verified public releases; preserve rollback.

    Never touch configuration, external state, unknown folders, symlinks,
    non-public old releases or the current/previous releases.
    """
    root, active = Path(root), Path(active)
    if root.is_symlink() or not root.is_dir() or root.resolve() != active.resolve().parent:
        raise UpdateError("release cleanup outside trusted application release root")
    previous = Path(previous).resolve() if previous is not None else None
    deleted = []
    for candidate in root.iterdir():
        if (candidate.is_symlink() or not candidate.is_dir()
                or not SHA.fullmatch(candidate.name)
                or candidate.resolve() in (active.resolve(), previous)
                or candidate.resolve().parent != root.resolve()
                or current_sha(candidate) != candidate.name):
            continue
        try:
            origin = json.loads((candidate / "SELF_UPDATE_ORIGIN.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(origin, dict) or origin.get("repository") != REPOSITORY or origin.get("commit") != candidate.name:
            continue
        contents = list(candidate.iterdir())
        if any(item.is_symlink()
               or (item.is_dir() and item.name not in OWNED_RELEASE_DIRECTORIES)
               or (item.is_file() and item.name not in OWNED_RELEASE_FILES)
               or (not item.is_dir() and not item.is_file()) for item in contents):
            continue
        if any(item.is_symlink() for item in candidate.rglob("*")):
            continue
        shutil.rmtree(candidate)
        deleted.append(candidate.name)
    return deleted


def assert_files(path):
    for name in REQUIRED:
        if not (path / name).is_file():
            raise UpdateError("incomplete GitHub source: " + name)
    if (path / ".git").exists():
        raise UpdateError("git control directory must not be activated")

def _make_writable_and_retry(func, path, error):
    """Remove Git's read-only pack files on Windows during staging cleanup."""
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    func(path)


def validate_staged(path):
    assert_files(path)
    call([sys.executable, "-m", "py_compile", "pc_mesh.py", "update_control.py",
          "tui.py", "owner_profiles.py", "self_update.py"], cwd=path, timeout=60)
    call([sys.executable, "test_update_announce.py"], cwd=path, timeout=120)
    for pattern in ("test_self_update.py", "test_public_self_update.py",
                    "test_cli_hostname_prompt.py"):
        call([sys.executable, "-m", "unittest", "discover", "-s", "tests",
              "-p", pattern, "-q"], cwd=path, timeout=120)
    if os.name == "nt":
        # Native PowerShell syntax, avoiding startup/profile side effects.
        ps = shutil.which("powershell.exe") or shutil.which("pwsh")
        if not ps:
            raise UpdateError("PowerShell is required for Windows activation")
        for name in ("install_windows.ps1", "prompt_windows.ps1"):
            # -EncodedCommand bypasses nested PowerShell argument-quote loss on
            # Windows PowerShell 5.1 and correctly handles spaces/apostrophes.
            escaped = str(path / name).replace("'", "''")
            command = ("$e=$null;$t=$null;[System.Management.Automation.Language.Parser]"
                       "::ParseFile('" + escaped + "',[ref]$t,[ref]$e)|Out-Null;"
                       "if($e.Count){exit 2}")
            encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
            call([ps, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                 timeout=35)
    else:
        if shutil.which("bash"):
            call(["bash", "-n", "scripts/install.sh", "scripts/uninstall.sh"],
                 cwd=path, timeout=20)

def verified_checkout(branch, stage, expected_sha, previous):
    call(["git", "clone", "--no-tags", "--single-branch", "--branch", branch,
          REPOSITORY, str(stage)], timeout=150)
    actual = call(["git", "-C", str(stage), "rev-parse", "HEAD"], timeout=15).stdout.strip()
    if not SHA.fullmatch(actual) or actual != expected_sha:
        raise UpdateError("GitHub release moved while downloading; retry later")
    origin = call(["git", "-C", str(stage), "remote", "get-url", "origin"]).stdout.strip()
    if origin != REPOSITORY:
        raise UpdateError("release source remote identity mismatch")
    call(["git", "-C", str(stage), "fsck", "--full", "--no-reflogs"], timeout=150)
    if previous:
        if not SHA.fullmatch(previous):
            raise UpdateError("invalid previous release identity")
        exists = call(["git", "-C", str(stage), "cat-file", "-e", previous + "^{commit}"],
                      check=False, timeout=15)
        if exists.returncode:
            raise UpdateError("installed release not in GitHub ancestry; manual migration required")
        ancestor = call(["git", "-C", str(stage), "merge-base", "--is-ancestor",
                         previous, actual], check=False, timeout=25)
        if ancestor.returncode:
            raise UpdateError("GitHub branch rewound or diverged; refusing automatic downgrade")
    if remote_sha(branch) != expected_sha:
        raise UpdateError("GitHub ref changed during release verification")
    # Copy tracked checkout only; never execute code from the git object database.
    shutil.rmtree(stage / ".git", onerror=_make_writable_and_retry)
    assert_files(stage)
    (stage / "DEPLOYED_COMMIT").write_text(actual + "\n", encoding="ascii")
    (stage / "SELF_UPDATE_ORIGIN.json").write_text(json.dumps({
        "repository": REPOSITORY, "branch": branch, "commit": actual,
        "staged_at": int(time.time())}, sort_keys=True) + "\n", encoding="utf-8")
    validate_staged(stage)

def verify_installed_source(release):
    """Confirm the installed CLI points to the activated, tested release."""
    name = "updatewulf.cmd" if os.name == "nt" else "updatewulf"
    wrapper = Path.home() / ".local" / "bin" / name
    try:
        content = wrapper.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise UpdateError("installed UpdateWulf command is not readable") from exc
    expected = str(release / "pc_mesh.py")
    if expected.lower() not in content.lower():
        raise UpdateError("installed UpdateWulf command still targets the old release")
    probe = call([sys.executable, str(release / "pc_mesh.py"), "--version"],
                 timeout=20).stdout.strip()
    if not probe.startswith("UpdateWulf "):
        raise UpdateError("updated CLI version check failed")


def install(release, previous, state):
    if os.name == "nt":
        ps = shutil.which("powershell.exe") or shutil.which("pwsh")
        if not ps:
            raise UpdateError("PowerShell unavailable")
        args = [ps, "-NoProfile", "-NonInteractive", "-File",
                str(release / "install_windows.ps1"), "-Source", str(release),
                "-Python", sys.executable]
        if state:
            args += ["-State", str(state)]
        try:
            call(args, timeout=165)
            verify_installed_source(release)
        except UpdateError:
            # Roll back by re-invoking the *previous* locally retained installer.
            if previous and (previous / "install_windows.ps1").is_file():
                try:
                    args[args.index(str(release / "install_windows.ps1"))] = str(previous / "install_windows.ps1")
                    args[args.index(str(release))] = str(previous)
                    call(args, timeout=165)
                except UpdateError:
                    raise UpdateError("activation and rollback failed; previous source retained")
            raise
    else:
        # Never replace a protected machine service through a user-level
        # installer: it would create a second daemon and change ownership.
        if os.geteuid() == 0:
            raise UpdateError("root machine deployment requires the native privileged release runbook")
        if shutil.which("systemctl"):
            units = call(["systemctl", "is-active", "pc-mesh-announce.service"],
                         check=False, timeout=10)
            if units.stdout.strip() == "active":
                raise UpdateError("machine service active; native machine release handover required")
        call([sys.executable, str(release / "install.py")], timeout=165)
        verify_installed_source(release)

def apply(branch, source, state=None, bootstrap=False):
    branch = validate_branch(branch)
    root = release_root()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".apply.lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise UpdateError("self-update already running or interrupted; inspect lock") from exc
    try:
        old = current_sha(source)
        if old is None and not bootstrap:
            raise UpdateError("first migration requires an explicit --bootstrap")
        latest = remote_sha(branch)
        if old == latest:
            print("UP_TO_DATE " + latest)
            return 0
        with tempfile.TemporaryDirectory(prefix=".updatewulf-fetch-", dir=root) as td:
            stage = Path(td) / "checkout"
            verified_checkout(branch, stage, latest, None if bootstrap else old)
            destination = root / latest
            if destination.exists():
                # Never overwrite an existing staged or installed release.
                assert_files(destination)
                if current_sha(destination) != latest:
                    raise UpdateError("existing release path has an invalid identity")
            else:
                stage.rename(destination)
            install(destination, source if (source / "install_windows.ps1").is_file() else None, state)
            try:
                prune_owned_releases(root, active=destination, previous=source)
            except (OSError, UpdateError) as exc:
                # A cleanup failure must not conceal a successful activation.
                print("STALE_RELEASE_CLEANUP_DEFERRED: " + type(exc).__name__, file=sys.stderr)
        print("INSTALLED " + latest)
        return 0
    finally:
        lock.rmdir()

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args(argv)
    if args.check and args.apply:
        parser.error("--check and --apply are mutually exclusive")
    try:
        latest = remote_sha(args.branch)
        installed = current_sha(args.source)
        if args.check or not args.apply:
            print(json.dumps({"installed": installed, "github": latest,
                              "same": installed == latest, "branch": args.branch}))
            return 0
        return apply(args.branch, args.source, args.state, args.bootstrap)
    except UpdateError as exc:
        print("SELF_UPDATE_BLOCKED: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
