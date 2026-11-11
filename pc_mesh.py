#!/usr/bin/env python3
"""Cross-platform update status, notifications and operator-controlled upgrades.

Python 3.9+, standard library only. Fixed package updates require an explicit
authorized LAN request and native privileges. No automatic commits, resets,
stashes, force pushes, privilege escalation or automatic reboot.
"""
from __future__ import annotations

import argparse
import io
import contextlib
import hashlib
import hmac
import ipaddress
import json
import logging
import logging.handlers
import os
import platform
import re
import secrets
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import update_control

VERSION = "2.1.0"
LOG = logging.getLogger("pc-mesh")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
BUNDLE_LIMIT = 32 * 1024 * 1024


def bundle_id(name):
    return hashlib.sha256(name.lower().encode()).hexdigest()


def private_binary(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.pc-mesh-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
        if os.name != 'nt':
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def atomic_write(path, content, private=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pc-mesh-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
        if os.name != "nt":
            os.chmod(tmp, 0o600 if private else 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save_json(path, value, private=False):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", private)


class FileLock:
    """OS lock released even when a worker crashes. Never trust a stale PID."""
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "a+b")
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            self.file = None
            raise RuntimeError("another pc-mesh process holds this lock")
        return self

    def __exit__(self, *args):
        self.file.close()


def run(args, timeout=60, env=None):
    environ = os.environ.copy()
    environ.update({"LC_ALL": "C", "LANG": "C", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    if env:
        environ.update(env)
    opts = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    p = subprocess.Popen([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=environ, **opts)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            # Terminate only the process we created. UpdateWulf no longer
            # invokes taskkill or an external kill supervisor.
            with contextlib.suppress(OSError):
                p.kill()
        else:
            import signal
            with contextlib.suppress(ProcessLookupError):
                os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise TimeoutError("command exceeded %ss" % timeout)
    return p.returncode, out.strip(), err.strip()


def github_name(url):
    # Reject credential-bearing URLs, local paths and lookalike hosts.
    m = re.fullmatch(r"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([^/]+/[^/]+?)(?:\.git)?/?", url or "")
    return m.group(1).lower() if m else None


def sync_repo(repo, state_dir, client=None):
    path = Path(repo["path"]).expanduser().resolve()
    result = {"path": str(path), "name": repo.get("name", path.name), "status": "UNKNOWN"}
    if repo.get("pinned") or repo.get("enabled") is False:
        return dict(result, status="PINNED")
    key = hashlib.sha256(str(path).encode()).hexdigest()[:20]
    try:
        with FileLock(Path(state_dir) / ("git-" + key + ".lock")):
            env = {}
            if repo.get("ssh_key"):
                ssh = repo.get("ssh_binary", "ssh")
                kh = repo.get("known_hosts")
                parts = [ssh, "-i", repo["ssh_key"], "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10"]
                if kh:
                    parts += ["-o", "UserKnownHostsFile=" + kh]
                env["GIT_SSH_COMMAND"] = " ".join(shlex.quote(v.replace("\\", "/")) for v in parts)
            if not path.exists():
                if not repo.get("clone") or not github_name(repo.get("url")):
                    return dict(result, status="MISSING")
                path.parent.mkdir(parents=True, exist_ok=True)
                clone_source = repo["url"]
                if repo.get("relay"):
                    clone_source = client.download_bundle(repo, state_dir)
                rc, _, err = run(["git", "clone", "--single-branch", "--branch", repo.get("branch", "main"), *([] if repo.get("relay") else ["--depth", "1"]), clone_source, path], 180, env)
                if rc:
                    check, refs, _ = run(["git", "ls-remote", repo["url"]], 45, env) if not repo.get("relay") else (1, "", "")
                    if check == 0 and not refs:
                        return dict(result, status="EMPTY_REMOTE")
                    return dict(result, status="AUTH_OR_NETWORK_ERROR", error=err[-300:])
                if repo.get("relay"):
                    run(["git", "-C", path, "remote", "set-url", "origin", repo["url"]], 15)
            def git(*args):
                return run(["git", "-C", path, *args], 90, env)
            rc, remote, _ = git("remote", "get-url", repo.get("remote", "origin"))
            name = github_name(remote)
            if rc or not name:
                return dict(result, status="NON_GITHUB")
            if repo.get("name") and name != repo["name"].lower():
                return dict(result, status="REMOTE_MISMATCH")
            _, branch, _ = git("branch", "--show-current")
            if not branch:
                return dict(result, status="DETACHED")
            if repo.get("branch") and branch != repo["branch"]:
                return dict(result, status="OTHER_BRANCH", branch=branch)
            _, gd, _ = git("rev-parse", "--absolute-git-dir")
            if any((Path(gd) / p).exists() for p in ["index.lock", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "BISECT_LOG"]):
                return dict(result, status="BUSY")
            rc, dirty, _ = git("status", "--porcelain", "--untracked-files=normal")
            if rc or dirty:
                return dict(result, status="LOCAL_CHANGES")
            rc, upstream, _ = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
            if rc:
                return dict(result, status="NO_UPSTREAM")
            expected_remote = repo.get("remote", "origin")
            if not upstream.startswith(expected_remote + "/"):
                return dict(result, status="UPSTREAM_MISMATCH")
            if repo.get("relay"):
                bundle = client.download_bundle(repo, state_dir)
                rc, _, err = git("bundle", "verify", bundle)
                if rc:
                    return dict(result, status="INVALID_BUNDLE", error=err[-300:])
                rc, _, err = git("fetch", "--no-tags", bundle, "refs/heads/" + branch + ":refs/remotes/" + expected_remote + "/" + branch)
            else:
                rc, _, err = git("fetch", "--no-tags", expected_remote)
            if rc:
                return dict(result, status="AUTH_OR_NETWORK_ERROR", error=err[-300:])
            _, counts, _ = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}")
            ahead, behind = map(int, counts.split())
            if ahead:
                return dict(result, status="DIVERGED" if behind else "LOCAL_COMMITS", ahead=ahead, behind=behind)
            # Recheck after fetch; fail closed if another writer began an edit.
            _, dirty, _ = git("status", "--porcelain", "--untracked-files=normal")
            if dirty:
                return dict(result, status="LOCAL_CHANGES")
            if behind:
                rc, _, err = git("-c", "core.hooksPath=" + os.devnull, "merge", "--ff-only", "--no-edit", "@{upstream}")
                if rc:
                    return dict(result, status="FF_FAILED", error=err[-300:])
            _, head, _ = git("rev-parse", "HEAD")
            _, remote_head, _ = git("rev-parse", "@{upstream}")
            return dict(result, status="SYNCED" if head == remote_head else "VERIFY_FAILED", head=head, branch=branch)
    except Exception as e:
        return dict(result, status="ERROR", error=str(e)[:250])


def scan_arch(state):
    # Read public version metadata as the real unprivileged user. Do not run
    # fakeroot, change pacman's databases or disable its download sandbox.
    rc, out, err = run(["pacman", "-Q"], 30)
    if rc:
        raise RuntimeError(err[-300:])
    installed = dict(line.split(None, 1) for line in out.splitlines())
    rc, out, err = run(["pacman-conf", "--repo-list"], 10)
    if rc or not out:
        raise RuntimeError(err or "no configured repositories")
    available = {}
    for repository in out.splitlines():
        rc, mirrors, err = run(["pacman-conf", "--repo", repository, "Server"], 10)
        if rc:
            raise RuntimeError(err[-250:])
        servers = [s for s in mirrors.splitlines() if s.startswith("https://")][:4]
        failures, entries = [], 0
        for server in servers:
            try:
                with urllib.request.urlopen(server.rstrip("/") + "/" + repository + ".db", timeout=20) as response:
                    raw = response.read(64 * 1024 * 1024 + 1)
                if len(raw) > 64 * 1024 * 1024:
                    raise ValueError("repository metadata exceeds size limit")
                repo_versions = parse_arch_database(raw, installed)
                entries = repo_versions.pop(None)
                for name, version in repo_versions.items():
                    available.setdefault(name, version)  # configured repo priority
                break
            except (OSError, ValueError, tarfile.TarError) as e:
                failures.append(str(e)[:120])
        if not entries:
            raise RuntimeError(repository + " metadata unavailable: " + "; ".join(failures)[-250:])
    packages = []
    for name, remote_version in available.items():
        if remote_version != installed[name]:
            rc, comparison, err = run(["vercmp", remote_version, installed[name]], 10)
            if rc or not re.fullmatch(r"-?\d+", comparison):
                raise RuntimeError(err or "vercmp failed")
            if int(comparison) > 0:
                packages.append(name)
    return {"status": "OK", "count": len(packages), "packages": sorted(packages), "source": "configured Arch repositories (HTTPS metadata, native vercmp)", "metadata_fresh": True}


def parse_arch_database(raw, installed):
    versions, entries = {}, 0
    # Stream tar metadata, never extract archive paths onto the filesystem.
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r|*") as archive:
        for entry in archive:
            if not entry.isfile() or not entry.name.endswith("/desc"):
                continue
            if entry.size > 65536 or entries > 200000:
                raise ValueError("invalid repository database size")
            body = archive.extractfile(entry).read().decode("utf-8")
            fields = dict(re.findall(r"%([A-Z]+)%\n([^\n]+)", body))
            name, version = fields.get("NAME"), fields.get("VERSION")
            if not name or not version:
                raise ValueError("invalid package version metadata")
            entries += 1
            if name in installed:
                versions[name] = version
    if not entries:
        raise ValueError("empty repository database")
    versions[None] = entries
    return versions


def scan_apt(state):
    lists = state / "apt-lists"
    (lists / "partial").mkdir(parents=True, exist_ok=True)
    import pwd
    options = ["-o", "Dir::State::Lists=" + str(lists), "-o", "Dir::Cache=" + str(state / "apt-cache"), "-o", "Debug::NoLocking=true", "-o", "APT::Get::List-Cleanup=false", "-o", "APT::Update::Error-Mode=any", "-o", "APT::Sandbox::User=" + pwd.getpwuid(os.getuid()).pw_name]
    rc, _, err = run(["apt-get", *options, "update"], 180)
    if rc:
        raise RuntimeError(err[-350:])
    rc, out, err = run(["apt-get", *options, "-s", "dist-upgrade"], 90)
    if rc:
        raise RuntimeError(err[-350:])
    packages = [s.split()[1] for s in out.splitlines() if s.startswith("Inst ") and "[" in s]
    return {"status": "OK", "count": len(set(packages)), "packages": sorted(set(packages)), "source": "Debian/apt repositories", "metadata_fresh": True}


def scan_pkgin(state):
    pkgin = shutil.which("pkgin") or "/usr/pkg/bin/pkgin"
    fresh = False
    if os.geteuid() == 0:
        rc, _, err = run([pkgin, "update"], 180)
        if rc:
            raise RuntimeError(err[-300:])
        fresh = True
    rc, out, err = run([pkgin, "-n", "upgrade"], 120)
    if rc not in (0, 1):
        raise RuntimeError(err[-300:])
    # pkgin prints diagnostics and some summaries to stderr. Native zero and
    # upgrade summaries are confirmed by upstream pkgin and target output.
    output = out + "\n" + err
    totals = dict((name, int(number)) for number, name in re.findall(r"(\d+)\s+to\s+(remove|refresh|upgrade|install)\b", output))
    m = re.search(r"(\d+)\s+packages?\s+to\s+(?:be\s+)?(?:upgraded|upgrade)", output, re.I)
    if "upgrade" in totals and "refresh" in totals:
        count = totals["upgrade"] + totals["refresh"]
    elif m:
        count = int(m.group(1))
    elif re.search(r"nothing to (?:upgrade|do)|no packages? to upgrade|all packages are up.to.date", output, re.I):
        count = 0
    else:
        lines = [s for s in output.splitlines() if re.match(r"^(?:upgrade|upgrading)\s+\S+", s, re.I)]
        if not lines:
            raise RuntimeError("pkgin output could not be parsed; count unknown")
        count = len(lines)
    packages = []
    for body in re.findall(r"\d+\s+packages?\s+to\s+(?:refresh|upgrade):\s*\n(.*?)(?:\n\s*\n|$)", output, re.S):
        packages.extend(body.split())
    return {"status": "OK" if fresh else "CACHED", "count": count, "packages": sorted(set(packages)), "source": "NetBSD pkgsrc/pkgin", "metadata_fresh": fresh}


def collect_updates(state, source_dir):
    started = time.time()
    try:
        if platform.system() == "Windows":
            exe = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
            rc, out, err = run([exe, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", source_dir / "collect_windows.ps1"], 240)
            if rc:
                raise RuntimeError(err[-350:])
            data = json.loads(out)
            if data.get("status") != "OK":
                raise RuntimeError(data.get("error", "Windows Update scan incomplete"))
        elif platform.system() == "NetBSD":
            data = scan_pkgin(state)
        elif shutil.which("pacman"):
            data = scan_arch(state)
        elif shutil.which("apt-get"):
            data = scan_apt(state)
        else:
            return {"status": "UNSUPPORTED", "count": None, "source": platform.system(), "checked_at": started}
        data["checked_at"] = time.time()
        return data
    except Exception as e:
        LOG.error("update scan: %s", e)
        previous = read_json(Path(state) / "local.json", {}).get("updates", {})
        if previous.get("status") in ("OK", "CACHED") and type(previous.get("count")) is int:
            cached = dict(previous)
            cached["status"] = "CACHED"
            cached["scan_error_at"] = started
            cached["error"] = ("fresh scan failed: " + str(e))[:350]
            return cached
        return {"status": "ERROR", "count": None, "checked_at": started, "error": str(e)[:350]}


def update_signature(data):
    return hashlib.sha256(json.dumps([data.get("count"), sorted(data.get("packages", []))], ensure_ascii=False).encode()).hexdigest()


def package_fingerprint(source):
    if os.name == "nt":
        ps = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        rc, out, err = run([ps, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", Path(source) / "collect_windows.ps1", "-Fingerprint"], 30)
        if rc:
            raise RuntimeError(err[-200:] or "Windows history fingerprint failed")
        return out
    paths = ["/var/lib/dpkg/status", "/var/lib/pacman/local", "/var/db/pkg", "/var/db/pkgin/pkgin.db"]
    prefix = os.environ.get("PREFIX", "")
    if prefix:
        paths.append(prefix + "/var/lib/dpkg/status")
    found = []
    for name in paths:
        try:
            value = Path(name).stat()
            found.append((name, value.st_mtime_ns, value.st_size))
        except OSError:
            pass
    return tuple(found)


def terminal_width():
    # Prompt hooks pipe stdout to their shell. Use the controlling SSH terminal
    # so a pipe does not silently revert a phone's 40 columns to 80.
    if os.name != 'nt':
        try:
            fd = os.open('/dev/tty', os.O_RDONLY | os.O_NOCTTY)
            try:
                return os.get_terminal_size(fd).columns
            finally:
                os.close(fd)
        except OSError:
            pass
    return shutil.get_terminal_size((80, 24)).columns


STATUS_ANSI = {
    "QUEUED": "36",
    "RUNNING": "33",
    "SUCCEEDED": "32",
    "FAILED": "31",
    "NEEDS_ADMIN": "35",
    "EXPIRED": "90",
    "INTERRUPTED": "33",
}


def ansi_enabled(mode="auto", stream=None):
    """Show colors for interactive terminals; never leak ANSI to JSON or pipes."""
    if mode == "never":
        return False
    if mode == "always":
        return True
    stream = sys.stdout if stream is None else stream
    return ("NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
            and bool(getattr(stream, "isatty", lambda: False)()))


def colored_status(status, enabled=False):
    raw = str(status)
    ansi = STATUS_ANSI.get(raw.upper()) if re.fullmatch(r"[A-Za-z_]+", raw) else None
    return "\x1b[" + ansi + "m" + raw + "\x1b[0m" if enabled and ansi else raw


def fleet_summary(fleet, width=None, color=False):
    width = max(28, width or terminal_width())
    rows = ["UpdateWulf - Updates", ""]
    for node in sorted(fleet.get("nodes", []), key=lambda n: n.get("name", "")):
        one = dict(fleet, nodes=[node])
        line = re.sub(r"[\x00-\x1f\x7f]", "", fleet_line(one).removeprefix("[Updates] "))
        rows.extend(textwrap.wrap(line, width=width, subsequent_indent="  ") or [""])
    for job in fleet.get("commands", [])[-5:]:
        status = str(job.get("status", "?"))
        wrapped = textwrap.wrap("%s %s: %s" % (job["target"], job["action"], status), width=width)
        for line in wrapped:
            # Decorate after wrapping: ANSI control sequences occupy zero columns.
            if color and line.endswith(status):
                line = line[:-len(status)] + colored_status(status, True)
            rows.append(line)
    rows += ["", "UpdateWulf tui", "UpdateWulf refresh HOST", "UpdateWulf update HOST", "UpdateWulf sync HOST"]
    return "\n".join(rows)


def fleet_line(fleet, now=None):
    if not fleet.get("nodes"):
        return "[Updates] Statusdienst startet"
    now = time.time() if now is None else now
    rows = []
    for node in sorted(fleet.get("nodes", []), key=lambda v: v.get("name", v.get("id", "")).lower()):
        data = node.get("updates", {})
        count = data.get("count")
        label = node.get("name", node.get("id", "?"))
        # Re-evaluate freshness at read time so a dead hub cannot look live.
        if now - node.get("received_at", 0) > fleet.get("offline_after", 150):
            value = ((str(count) + " (offline)") if count is not None else "offline") if node.get("received_at") else "ausstehend"
        elif data.get("status") == "ERROR":
            value = "Prueffehler"
        elif count is None:
            value = "?"
        elif now - data.get("checked_at", 0) > fleet.get("stale_after", 5400):
            value = str(count) + " (veraltet)"
        else:
            value = str(count) + ("~" if data.get("status") == "CACHED" else "")
        rows.append(label + ": " + value)
    return "[Updates] " + " | ".join(rows)


# Routing identities remain authenticated member IDs and enrolled/reported names.
# Prompt-only labels may fall back to the configured friendly machine name when
# an offline/unenrolled node has not yet reported a hostname. Never route by label.
HOSTNAME_SAFE = re.compile(r"^[A-Za-z0-9_-]{1,63}(?:\.[A-Za-z0-9_-]{1,63})*$")
SGR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def canonical_hostname(value, fallback="unknown"):
    if not isinstance(value, str):
        value = ""
    value = value.strip().rstrip(".")
    if not value or len(value) > 253 or not HOSTNAME_SAFE.fullmatch(value):
        value = fallback if isinstance(fallback, str) else "unknown"
    first = value.split(".", 1)[0]
    if not first and fallback == "":
        return ""
    return first if HOSTNAME_SAFE.fullmatch(first) else "unknown"


def display_machine_name(node):
    """Safe, suffix-free prompt label, independent of DNS and CLI routing.

    A host may be offline before its first heartbeat; prefer the reported
    machine name, then enrollment, then the display name, then the member ID.
    A friendly name is only a label, never a verified transport identity.
    """
    for key in ("hostname", "enrolled_hostname", "name", "id"):
        value = node.get(key)
        if not isinstance(value, str):
            continue
        value = value.strip().rstrip(".")
        if value and len(value) <= 253 and HOSTNAME_SAFE.fullmatch(value):
            return value.split(".", 1)[0]
    return "unknown"


def prompt_node_status(node, fleet, now):
    updates = node.get("updates") or {}
    count = updates.get("count")
    received = node.get("received_at") or 0
    generated = fleet.get("generated_at")
    cache_age = now - generated if isinstance(generated, (int, float)) else float("inf")
    # A stopped hub or a stalled client produces an old fleet snapshot. That
    # alone is NOT proof that every machine is offline. Report [stale] instead.
    hub_fresh = -300 <= cache_age <= max(60, min(180, fleet.get("offline_after", 150)))
    status = updates.get("status")
    count_label = str(count) + " Update(s)" if type(count) is int and count >= 0 else "? Update(s)"
    if not received:
        state = "?"
    elif not hub_fresh:
        state = "stale"
    elif now - received > fleet.get("offline_after", 150):
        state = "off"
    elif status in ("ERROR", "UNKNOWN", "UNSUPPORTED", "CHECKING"):
        state = "err" if status == "ERROR" else "?"
    elif not isinstance(updates.get("checked_at"), (int, float)) or now - updates["checked_at"] > fleet.get("stale_after", 5400):
        state = "stale"
    elif status == "CACHED":
        state = "cached"
    else:
        state = None
    return count_label, state


def _prompt_node(node, fleet, now, color):
    hostname = display_machine_name(node)
    count, state = prompt_node_status(node, fleet, now)
    label = "\x1b[1;38;5;255m" + hostname + "\x1b[0m" if color else hostname
    value = label + " " + count
    if state:
        if state == "off" and color:
            value += " [" + "\x1b[38;5;196m" + "off" + "\x1b[0m" + "]"
        else:
            value += " [" + state + "]"
    return value


def _prompt_visible_length(text):
    return len(SGR_PATTERN.sub("", text))


def fleet_preprompt(fleet, now=None, width=160, color=True):
    """One transient pre-PS1 header, never an automatically wrapped line.

    Healthy zero-update machines are summarized as +N. Positive or erroneous
    machines retain their own labels when space permits. A final ellipsis
    means *additional nonzero/problem machines* are hidden by terminal width.
    Reserve one physical column so readline/PowerShell does not wrap at EOL.
    """
    now = time.time() if now is None else now
    width = max(22, int(width))
    nodes = sorted(fleet.get("nodes", []), key=lambda n: display_machine_name(n).lower())
    def hidden_zero(node):
        update = node.get("updates") or {}
        return (type(update.get("count")) is int and update["count"] == 0
                and update.get("status") in ("OK", "CACHED"))
    zeros = sum(hidden_zero(n) for n in nodes)
    entries = [_prompt_node(n, fleet, now, color) for n in nodes
               if type((n.get("updates") or {}).get("count")) is int
               and not hidden_zero(n)]
    green = "\x1b[1;38;5;85m" if color else ""
    blue = "\x1b[38;5;39m" if color else ""
    reset = "\x1b[0m" if color else ""
    prefix = "[ " + green + "UpdateWulf" + reset
    sep = " " + blue + ":::" + reset + " "
    tail = sep + "+" + str(zeros) if zeros else ""
    final = " ]"
    chosen = []
    for index, entry in enumerate(entries):
        # Budget the suffix before accepting this entry: never split a hostname.
        overflow = index < len(entries) - 1
        extra = (" ..." if overflow else "")
        candidate = prefix + "".join(sep + part for part in chosen + [entry]) + tail + extra + final
        if _prompt_visible_length(candidate) < width:
            chosen.append(entry)
        else:
            break
    overflow = len(chosen) < len(entries)
    if not entries and not zeros:
        tail = sep + "keine ausstehenden Updates"
    result = prefix + "".join(sep + part for part in chosen) + tail
    if overflow:
        result += " ..."
    result += final
    # Extremely narrow terminals show only a compact aggregate.
    if _prompt_visible_length(result) >= width:
        missing = len(entries) - len(chosen) + zeros
        result = prefix + (" +" + str(missing) if missing else "") + final
    if _prompt_visible_length(result) >= width:
        result = "[ UpdateWulf ]"
    return result

def bash_safe_prompt(ansi_line):
    """Bash PS1 nonprinting delimiters prevent editline width corruption."""
    return SGR_PATTERN.sub(lambda m: r"\[" + m.group() + r"\]", ansi_line)

def netbsd_safe_prompt(ansi_line):
    """NetBSD sh/editline PSlit SOH pairs around nonprinting SGR sequences."""
    return SGR_PATTERN.sub(lambda m: "\x01" + m.group() + "\x01", ansi_line)


class Hub:
    def __init__(self, config, state):
        self.config, self.state = config, Path(state)
        old = read_json(self.state / "hub.json", {})
        self.nodes = old.get("nodes", {})
        self.events = old.get("events", [])
        self.sequence = old.get("sequence", 0)
        self.condition = threading.Condition()
        self.members = {m["id"]: m for m in config["members"]}
        self.control = update_control.ControlQueue(self.state / "commands.json", self.members, read_json, save_json)

    def report(self, node_id, data):
        if node_id not in self.members or not isinstance(data, dict):
            raise ValueError("unknown member")
        updates = data.get("updates", {})
        count = updates.get("count")
        if count is not None and (type(count) is not int or not 0 <= count <= 100000):
            raise ValueError("invalid update count")
        if updates.get("status") not in ("OK", "CACHED", "ERROR", "UNKNOWN", "UNSUPPORTED", "CHECKING"):
            raise ValueError("invalid status")
        packages = updates.get("packages", [])
        if not isinstance(packages, list) or len(packages) > 20000 or any(not isinstance(s, str) or len(s) > 300 for s in packages):
            raise ValueError("invalid packages")
        checked = updates.get("checked_at", 0)
        if not isinstance(checked, (int, float)) or not 0 <= checked <= time.time() + 300:
            raise ValueError("invalid scan timestamp")
        with self.condition:
            old = self.nodes.get(node_id, {})
            if updates.get("checked_at", 0) < old.get("updates", {}).get("checked_at", 0):
                updates = old["updates"]  # older in-flight scans cannot undo a fresh installed count
                count = updates.get("count")
            # An in-flight/error report must not erase the last successful count.
            last_good = old.get("last_good_updates")
            if updates.get("status") in ("OK", "CACHED"):
                signature = update_signature(updates)
                previous_signature = old.get("last_signature")
                if signature != previous_signature and (count or previous_signature):
                    self.sequence += 1
                    message = (self.members[node_id]["name"] + ": " + str(count) + " ausstehende Updates")
                    self.events.append({"seq": self.sequence, "at": time.time(), "node": node_id, "message": message, "signature": signature})
                    self.events = self.events[-100:]
                last_good = updates
            else:
                signature = old.get("last_signature")
            self.nodes[node_id] = {"id": node_id, "name": self.members[node_id]["name"],
                                   "hostname": canonical_hostname(data.get("hostname"), old.get("hostname") or ""),
                                   "os": data.get("os", ""),
                                   "updates": updates, "git": data.get("git", old.get("git", [])), "received_at": time.time(),
                                   "last_signature": signature, "last_good_updates": last_good, "agent": data.get("agent", "")}
            save_json(self.state / "hub.json", {"nodes": self.nodes, "events": self.events, "sequence": self.sequence}, True)
            self.condition.notify_all()

    def snapshot(self, since=0, wait=0):
        with self.condition:
            if wait and since >= self.sequence:
                self.condition.wait(min(wait, 25))
            nodes = [dict(self.nodes.get(i, {"id": i, "name": m["name"], "received_at": 0,
                      "updates": {"status": "UNKNOWN", "count": None}}),
                      **({"enrolled_hostname": m["hostname"]} if m.get("hostname") else {}))
                     for i, m in self.members.items()]
            return {"nodes": nodes, "events": [e for e in self.events if e["seq"] > since], "sequence": self.sequence,
                    "generated_at": time.time(), "offline_after": self.config.get("offline_after", 150),
                    "stale_after": self.config.get("stale_after", 5400), "commands": self.control.snapshot()}


def start_hub(config, state):
    hub = Hub(config, state)
    allowed = [ipaddress.ip_network(n) for n in config.get("allowed_networks", ["127.0.0.0/8", "10.1.0.0/24", "100.64.0.0/10"])]
    relay = {bundle_id(r['name']): r for r in config.get('relay_repositories', [])}
    bundles = Path(state) / 'bundles'
    bundles.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        bundles.chmod(0o700)
    bundle_guard = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def auth(self, write=False):
            ip = ipaddress.ip_address(self.client_address[0])
            if not any(ip in n for n in allowed):
                return None
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            if config.get("operator_token") and hmac.compare_digest(token, config["operator_token"]):
                return "operator"
            if not write and hmac.compare_digest(token, config["read_token"]):
                return "reader"
            for member in config["members"]:
                if member.get("token") and hmac.compare_digest(token, member["token"]):
                    return member["id"]
            return None

        def respond(self, status, value):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(raw)

        def do_GET(self):
            who = self.auth()
            if not who:
                return self.respond(401, {"error": "unauthorized"})
            p = urllib.parse.urlparse(self.path)
            if p.path == "/commands":
                try:
                    return self.respond(200, {"commands": hub.control.pending(who)})
                except PermissionError as e:
                    return self.respond(403, {"error": str(e)})
            if p.path.startswith('/bundle/'):
                key = p.path.split('/')[-1]
                if key not in relay:
                    return self.respond(404, {'error': 'repository not enrolled for relay'})
                with bundle_guard:
                    metadata = read_json(bundles / (key + '.json'))
                    if not metadata:
                        return self.respond(503, {'error': 'authorized source has not published a bundle yet'})
                    raw = (bundles / (key + '.bundle')).read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('X-PC-Mesh-Head', metadata['head'])
                self.send_header('X-PC-Mesh-SHA256', metadata['sha256'])
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(raw)
                return
            if p.path not in ("/fleet", "/events"):
                return self.respond(404, {"error": "unknown route"})
            try:
                qs = urllib.parse.parse_qs(p.query)
                since = int(qs.get("since", ["0"])[0])
                wait = min(25, max(0, int(qs.get("wait", ["0"])[0])))
            except ValueError:
                return self.respond(400, {"error": "invalid cursor"})
            self.respond(200, hub.snapshot(since, wait))

        def do_POST(self):
            who = self.auth(True)
            if not who or self.path not in ("/report", "/control", "/control-batch", "/command-result"):
                return self.respond(401, {"error": "unauthorized"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 524288:
                    raise ValueError("invalid length")
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("JSON object required")
                if self.path == "/control":
                    result = hub.control.enqueue(who, data.get("target"), data.get("action"), data.get("request_id"))
                    with hub.condition:
                        hub.condition.notify_all()
                    return self.respond(200, result)
                if self.path == "/control-batch":
                    result = hub.control.enqueue_many(who, data.get("requests"))
                    with hub.condition:
                        hub.condition.notify_all()
                    return self.respond(200, {"jobs": result})
                if self.path == "/command-result":
                    result = hub.control.result(who, data.get("id"), data.get("status"), data.get("detail", ""))
                    with hub.condition:
                        hub.condition.notify_all()
                    return self.respond(200, result)
                hub.report(who, data)
            except PermissionError as e:
                return self.respond(403, {"error": str(e)})
            except (ValueError, OSError) as e:
                return self.respond(400, {"error": str(e)})
            self.respond(200, {"ok": True, "sequence": hub.sequence})

        def do_PUT(self):
            who = self.auth(True)
            key = self.path.removeprefix('/bundle/')
            if who != config.get('relay_provider') or key not in relay:
                return self.respond(403, {'error': 'relay write not authorized'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                head = self.headers.get('X-PC-Mesh-Head', '')
                if not 0 < length <= BUNDLE_LIMIT or not re.fullmatch(r'[0-9a-f]{40,64}', head):
                    raise ValueError('invalid bundle length or head')
                self.connection.settimeout(30)
                raw = self.rfile.read(length)
                if len(raw) != length or not raw.startswith((b'# v2 git bundle\n', b'# v3 git bundle\n')):
                    raise ValueError('incomplete or invalid Git bundle')
                branch = relay[key].get('branch', 'main')
                with bundle_guard:
                    temp = bundles / (key + '.incoming')
                    private_binary(temp, raw)
                    rc, refs, err = run(['git', 'bundle', 'list-heads', temp], 15)
                    if rc or refs.strip() != head + ' refs/heads/' + branch:
                        temp.unlink(missing_ok=True)
                        raise ValueError('unexpected bundle refs')
                    os.replace(temp, bundles / (key + '.bundle'))
                    save_json(bundles / (key + '.json'), {'head': head, 'sha256': hashlib.sha256(raw).hexdigest(), 'at': time.time()}, True)
            except (ValueError, OSError) as e:
                return self.respond(400, {'error': str(e)[:200]})
            self.respond(200, {'ok': True, 'head': head})
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.load_cert_chain(config["certificate"], config["private_key"])
    class MeshHTTPServer(ThreadingHTTPServer):
        request_queue_size = 64
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(10)
            # TLS negotiation belongs to the request thread. An idle TCP peer
            # must not stop every fleet report at the accept loop.
            try:
                return tls.wrap_socket(connection, server_side=True, do_handshake_on_connect=False), address
            except Exception:
                connection.close()
                raise
    server = MeshHTTPServer((config.get("bind", "0.0.0.0"), config.get("port", 9797)), Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    LOG.info("hub listening on %s:%s", config.get("bind", "0.0.0.0"), config.get("port", 9797))
    return server


class Client:
    def __init__(self, config):
        self.config = config
        self.context = ssl.create_default_context(cafile=config["certificate"])
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.preferred = 0

    def request(self, route, data=None, timeout=10):
        urls = self.config["hubs"]
        failures = []
        for index in [(self.preferred + j) % len(urls) for j in range(len(urls))]:
            base = urls[index]
            if not base.startswith("https://"):
                raise ValueError("HTTPS hub URL required")
            req = urllib.request.Request(base.rstrip("/") + route, data=json.dumps(data).encode() if data is not None else None,
                                         headers={"Authorization": "Bearer " + self.config["token"], "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=self.context) as response:
                    result = json.loads(response.read(1048576))
                self.preferred = index
                return result
            except urllib.error.HTTPError as e:
                # An HTTP rejection is a response from an application, not a
                # TCP outage. Never blindly retry an operator write on another
                # hub if one endpoint already rejected it.
                if 400 <= e.code < 500 and e.code not in (408, 429):
                    reason = ""
                    content_type = e.headers.get("Content-Type", "") if e.headers else ""
                    if content_type.split(";", 1)[0].strip().lower() == "application/json":
                        try:
                            error = json.loads(e.read(2048))
                            if isinstance(error, dict) and isinstance(error.get("error"), str):
                                reason = re.sub(r"[\x00-\x1f\x7f]", " ", error["error"])[:160]
                        except (ValueError, OSError):
                            pass
                    raise RuntimeError("hub rejected %s: HTTP %d%s" % (
                        route, e.code, ("; " + reason) if reason else "")) from None
                failures.append("HTTP %d" % e.code)
            except (OSError, ValueError) as e:
                failures.append(type(e).__name__ + ": " + str(e)[:100])
        raise RuntimeError("hub unreachable: " + "; ".join(failures)[:250])

    def bundle_request(self, name, raw=None, head=None):
        errors = []
        urls = self.config['hubs']
        for j in range(len(urls)):
            index = (self.preferred + j) % len(urls)
            base = urls[index]
            if not base.startswith('https://'):
                raise ValueError('HTTPS hub URL required')
            headers = {'Authorization': 'Bearer ' + self.config['token']}
            if raw is not None:
                headers.update({'Content-Type': 'application/octet-stream', 'X-PC-Mesh-Head': head})
            request = urllib.request.Request(base.rstrip('/') + '/bundle/' + bundle_id(name), data=raw,
                                             headers=headers, method='PUT' if raw is not None else 'GET')
            try:
                with urllib.request.urlopen(request, timeout=40, context=self.context) as response:
                    body = response.read(BUNDLE_LIMIT + 1)
                    metadata = dict(response.headers)
                if len(body) > BUNDLE_LIMIT:
                    raise ValueError('bundle exceeds limit')
                self.preferred = index
                return body, metadata
            except (OSError, ValueError) as e:
                errors.append(str(e))
        raise RuntimeError('bundle relay unavailable: ' + '; '.join(errors)[:250])

    def download_bundle(self, repo, state):
        raw, metadata = self.bundle_request(repo['name'])
        if hashlib.sha256(raw).hexdigest() != metadata.get('X-PC-Mesh-SHA256'):
            raise ValueError('bundle digest mismatch')
        path = Path(state) / ('bundle-' + bundle_id(repo['name']) + '.bundle')
        private_binary(path, raw)
        return str(path)

    def publish_bundle(self, repo, result, state):
        if result['status'] != 'SYNCED':
            return
        key = bundle_id(repo['name'])
        stamp = Path(state) / ('published-' + key + '.json')
        if read_json(stamp, {}).get('head') == result['head']:
            return
        path = Path(state) / ('publish-' + key + '.bundle')
        rc, shallow, _ = run(['git', '-C', repo['path'], 'rev-parse', '--is-shallow-repository'], 15)
        if rc:
            raise RuntimeError('cannot inspect relay source')
        if shallow == 'true':
            rc, _, err = run(['git', '-C', repo['path'], 'fetch', '--unshallow', 'origin'], 90)
            if rc:
                raise RuntimeError(err[-250:])
        rc, _, err = run(['git', '-C', repo['path'], 'bundle', 'create', path, 'refs/heads/' + repo.get('branch', 'main')], 60)
        if rc:
            raise RuntimeError(err[-250:])
        if path.stat().st_size > BUNDLE_LIMIT:
            raise RuntimeError('relay bundle exceeds configured limit')
        raw = path.read_bytes()
        self.bundle_request(repo['name'], raw, result['head'])
        save_json(stamp, {'head': result['head'], 'at': time.time()}, True)


def tunnel_worker(config, stopping):
    spec = config['ssh_tunnel']
    args = [spec.get('ssh', 'ssh'), '-N', '-L', '127.0.0.1:%d:127.0.0.1:9797' % spec.get('port', 19897),
            '-i', spec['key'].replace('\\', '/'), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + spec['known_hosts'].replace('\\', '/'),
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
            '-o', 'ConnectTimeout=8', spec['user'] + '@' + spec['host']]
    while not stopping.is_set():
        opts = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **opts)
        LOG.info('starting scoped SSH transport PID=%s', process.pid)
        while process.poll() is None and not stopping.wait(2):
            pass
        if process.poll() is None:
            process.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=5)
        error = process.stderr.read(4096).decode(errors='replace').strip()
        if error:
            LOG.warning('SSH transport exit=%s: %s', process.returncode, error[-700:])
        stopping.wait(10)


def current_announcements(fleet, since=0):
    # Collapse older same-host announcements and omit counts superseded by a
    # completed scan. Old backlog must not look like newly pending packages.
    latest = {e.get("node", str(e["seq"])): e for e in fleet.get("events", []) if e["seq"] > since and time.time() - e["at"] < 3600}
    nodes = {n["id"]: n for n in fleet.get("nodes", [])}
    messages = []
    for e in sorted(latest.values(), key=lambda v: v["seq"]):
        node = nodes.get(e.get("node"))
        if node and e.get("signature") and e["signature"] != node.get("last_signature"):
            continue
        if node and not e.get("signature") and e["message"] != "%s: %s ausstehende Updates" % (node["name"], node.get("updates", {}).get("count")):
            continue
        messages.append(e["message"])
    return ["[NEU] " + re.sub(r"[\x00-\x1f\x7f]", "", m) for m in messages[-3:]]


def prompt_output(cache, since=0):
    fleet = read_json(Path(cache) / "fleet.json", {})
    if not fleet:
        return "[Updates] Statusdienst startet", since
    messages = current_announcements(fleet, since)
    messages.append(fleet_line(fleet))
    width = max(28, terminal_width())
    return "\n".join(textwrap.fill(m, width=width, subsequent_indent="  ") for m in messages), max(since, fleet.get("sequence", 0))


def daemon(config, state):
    state.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    with FileLock(state / "daemon.lock"):
        server = start_hub(config["hub"], state) if config.get("hub") else None
        client = Client(config)
        current = read_json(state / "local.json", {"updates": {"status": "CHECKING", "count": None}, "git": []})
        current.update({"os": platform.platform(), "agent": VERSION, "hostname": socket.gethostname()})
        guard, stopping = threading.Lock(), threading.Event()
        scan_guard, git_guard = threading.Lock(), threading.Lock()
        scan_requested, report_requested = threading.Event(), threading.Event()
        def refresh():
            with scan_guard:
                data = collect_updates(state, source)
                with guard:
                    current["updates"] = data
                    save_json(state / "local.json", current)
                LOG.info("updates status=%s count=%s", data.get("status"), data.get("count"))
                report_requested.set()
                return data
        def scans():
            while not stopping.is_set():
                scan_requested.clear()
                refresh()
                scan_requested.wait(config.get("scan_interval", 1800))
        def monitor():
            previous, changed_at, dirty = None, 0, False
            interval = 60 if os.name == "nt" else 5
            while not stopping.wait(interval):
                try:
                    fingerprint = package_fingerprint(source)
                    if previous is not None and fingerprint != previous:
                        changed_at, dirty = time.time(), True
                    previous = fingerprint
                    if dirty and time.time() - changed_at >= 10:
                        scan_requested.set()
                        dirty = False
                except Exception as e:
                    LOG.warning("package change monitor: %s", e)
        def heartbeats():
            while not stopping.is_set():
                save_json(state / "heartbeat.json", {"pid": os.getpid(), "at": time.time(), "version": VERSION})
                stopping.wait(5)
        def sync():
            with git_guard:
                results = []
                for repo in config.get('repositories', []):
                    result = sync_repo(repo, state, client)
                    if repo.get('relay_publish'):
                        try:
                            client.publish_bundle(repo, result, state)
                            result['relay'] = 'PUBLISHED' if result['status'] == 'SYNCED' else 'PRESERVED'
                        except Exception as e:
                            result['relay'] = 'ERROR'
                            result['relay_error'] = str(e)[:250]
                            LOG.warning('relay %s: %s', repo['name'], e)
                    results.append(result)
                with guard:
                    current["git"] = results
                    save_json(state / "local.json", current)
                LOG.info("git %s", {s: sum(r["status"] == s for r in results) for s in set(r["status"] for r in results)})
                report_requested.set()
                return results
        def git_worker():
            while not stopping.is_set():
                sync()
                stopping.wait(config.get("git_interval", 300))
        def reports():
            while not stopping.is_set():
                try:
                    with guard:
                        data = json.loads(json.dumps(current))
                    if config.get("announce_only"):
                        data.pop("git", None)
                    client.request("/report", data)
                except Exception as e:
                    LOG.warning("report: %s", e)
                report_requested.wait(config.get("report_interval", 20))
                report_requested.clear()
        def control():
            update_control.worker(client, state, stopping, refresh, sync,
                                  lambda: update_control.run_install(source, state, save_json, config.get("native_installer", False)), read_json, save_json, LOG,
                                  allowed_actions={"refresh", "install"} if config.get("announce_only") else update_control.ACTIONS)
        def self_updates():
            # Application releases only; OS upgrades stay explicitly operator-triggered.
            if stopping.wait(300):
                return
            while not stopping.is_set():
                try:
                    cmd = [sys.executable, str(source / "self_update.py"), "--apply",
                           "--source", str(source), "--state", str(state),
                           "--branch", config.get("self_update_branch", "main")]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900,
                                            stdin=subprocess.DEVNULL)
                    if result.returncode == 0 and "INSTALLED " in result.stdout:
                        LOG.info("UpdateWulf application release activated; handing over worker")
                        stopping.set()
                        return
                    if result.returncode:
                        LOG.warning("UpdateWulf self-update blocked (exit %s); existing release preserved",
                                    result.returncode)
                except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                    LOG.warning("UpdateWulf self-update check unavailable: %s", type(exc).__name__)
                stopping.wait(max(3600, min(86400, int(config.get("self_update_interval", 21600)))))
        functions = ((scans, reports, monitor, control) if config.get("machine_control") else (scans, reports, monitor)) if config.get("announce_only") else (scans, git_worker, reports, monitor, control)
        functions += (heartbeats,)
        if config.get("auto_self_update", True) and (os.name == "nt" or
                (not config.get("machine_control") and os.geteuid() != 0)):
            functions += (self_updates,)
        for fn in functions:
            threading.Thread(target=fn, daemon=True).start()
        transport = None
        if config.get('ssh_tunnel'):
            transport = threading.Thread(target=tunnel_worker, args=(config, stopping), daemon=True)
            transport.start()
        cursor = 0
        try:
            while not (state / "stop.request").exists():
                try:
                    fleet = client.request("/events?since=%d&wait=20" % cursor, timeout=30)
                    # Persist the bounded event history, not just a long-poll delta.
                    old = read_json(state / "fleet.json", {})
                    events = {e["seq"]: e for e in old.get("events", []) + fleet.get("events", [])}
                    fleet["events"] = [events[k] for k in sorted(events)[-100:]]
                    save_json(state / "fleet.json", fleet)
                    atomic_write(state / "fleet.txt", fleet_line(fleet) + "\n")
                    atomic_write(state / "fleet-prompt.txt", fleet_preprompt(fleet, color=False, width=4096) + "\n")
                    atomic_write(state / "fleet-prompt.ansi", fleet_preprompt(fleet, color=True, width=4096) + "\n")
                    atomic_write(state / "fleet-prompt.bash", bash_safe_prompt(fleet_preprompt(fleet, color=True, width=4096)) + "\n")
                    for prompt_width in (22, 40, 80, 120, 160, 240):
                        atomic_write(state / ("fleet-prompt.bash." + str(prompt_width)),
                                     bash_safe_prompt(fleet_preprompt(fleet, color=True, width=prompt_width)) + "\n")
                    atomic_write(state / "fleet-prompt.netbsd", netbsd_safe_prompt(fleet_preprompt(fleet, color=True, width=4096)) + "\n")
                    for prompt_width in (22, 40, 80, 120, 160, 240):
                        atomic_write(state / ("fleet-prompt.netbsd." + str(prompt_width)),
                                     netbsd_safe_prompt(fleet_preprompt(fleet, color=True, width=prompt_width)) + "\n")
                    atomic_write(state / "sequence.txt", str(fleet["sequence"]) + "\n")
                    atomic_write(state / "notifications.txt", "\n".join(current_announcements(fleet)) + "\n")
                    atomic_write(state / "heartbeat.txt", str(int(time.time())) + "\n")
                    cursor = fleet["sequence"]
                except Exception as e:
                    LOG.warning("fleet: %s", e)
                    stopping.wait(10)
        finally:
            stopping.set()
            scan_requested.set()
            report_requested.set()
            (state / "stop.request").unlink(missing_ok=True)
            if transport:
                transport.join(timeout=8)  # release this worker's forwarding port before exiting
            if server:
                server.shutdown()


def resolve_fleet_targets(fleet, requested):
    """Resolve input to authenticated member IDs, never to DNS shell strings.

    .local denotes a reported or explicitly enrolled hostname. Friendly
    display names are not identities.
    """
    wanted = (requested or "").strip().rstrip(".").lower()
    if wanted == "all":
        return [n["id"] for n in fleet.get("nodes", []) if n.get("id")]
    if not wanted or not HOSTNAME_SAFE.fullmatch(wanted):
        raise ValueError("invalid hostname or member id")
    result = []
    for node in fleet.get("nodes", []):
        member_id = str(node.get("id", "")).lower()
        reported = canonical_hostname(node.get("hostname"), "")
        enrolled = canonical_hostname(node.get("enrolled_hostname"), "")
        names = {x.lower() for x in (reported, enrolled) if x}
        aliases = names | {name + ".local" for name in names}
        if wanted == member_id or wanted in aliases:
            result.append(node["id"])
    if len(result) > 1:
        raise ValueError("ambiguous hostname: multiple enrolled hosts match")
    if not result:
        raise ValueError("unknown hostname; check UpdateWulf status and host enrollment")
    return result


def parse_operator_order(first, second):
    """Old action-first and new host-first forms share one authorized path."""
    actions = {"refresh", "update", "sync", "status", "diagnose"}
    if isinstance(first, str) and first.lower() in actions:
        return first.lower(), second
    if isinstance(second, str) and second.lower() in actions:
        return second.lower(), first
    return first, second


def main():
    ap = argparse.ArgumentParser(description=__doc__, epilog="Examples: updatewulf bmax-b6.local update; updatewulf legion.local refresh; updatewulf all update --wait 600; UpdateWulf status")
    ap.add_argument("action", nargs="?", default="status", help="action, or hostname.local with host-first syntax")
    ap.add_argument("target", nargs="?", help="hostname.local, member id or all; or action with host-first syntax")
    ap.add_argument("--config", type=Path, default=Path.home() / ".config/pc-mesh/config.json")
    ap.add_argument("--state", type=Path, default=Path.home() / ".local/state/pc-mesh")
    ap.add_argument("--since", type=int, default=0)
    ap.add_argument("--json", action="store_true", help="raw status JSON")
    ap.add_argument("--color", choices=("auto", "always", "never"), default="auto", help="ANSI status colors (default: interactive terminals only)")
    ap.add_argument("--no-color", action="store_const", const="never", dest="color", help="disable ANSI status colors")
    ap.add_argument("--wait", type=int, default=None, help="wait for completion (update: 600 seconds by default; 0: asynchronous)")
    ap.add_argument("--version", action="version", version="UpdateWulf " + VERSION)
    ap.add_argument("--self", action="store_true", help="operate on UpdateWulf itself (use: --self update)")
    ap.add_argument("--check", action="store_true", help="check GitHub UpdateWulf application release")
    ap.add_argument("--bootstrap", action="store_true", help="explicit first migration of an existing installation")
    ap.add_argument("--branch", default=None, help="GitHub application release channel")
    args = ap.parse_args()
    if args.self:
        if args.action != "update" or args.target:
            ap.error("--self supports only the local application update: updatewulf --self update")
        import self_update
        source = Path(__file__).resolve().parent
        opts = ["--check" if args.check else "--apply", "--source", str(source),
                "--state", str(args.state)]
        if args.branch:
            opts.extend(["--branch", args.branch])
        # The user-issued command authorizes a one-time migration from the
        # earlier private release; subsequent public upgrades enforce ancestry.
        if args.bootstrap or (not args.check and self_update.needs_bootstrap(source)):
            opts.append("--bootstrap")
        return self_update.main(opts)
    args.action, args.target = parse_operator_order(args.action, args.target)
    allowed_actions = {"daemon", "once", "refresh", "update", "sync", "line", "prompt", "watch", "status", "tui", "diagnose", "self-update"}
    if args.action not in allowed_actions:
        ap.error("unknown action; use updatewulf <hostname.local> update|refresh|sync or updatewulf status")
    if args.target and args.action not in {"refresh", "update", "sync", "status"}:
        ap.error("this action does not accept a remote target")
    if args.action == "self-update":
        import self_update
        opts = ["--check" if args.check else "--apply", "--source", str(Path(__file__).resolve().parent),
                "--state", str(args.state)]
        if args.branch:
            opts.extend(["--branch", args.branch])
        if args.bootstrap:
            opts.append("--bootstrap")
        return self_update.main(opts)
    if args.action == "diagnose":
        # Read-only endpoint check. Never enqueue/replay an update job.
        operator_file = Path.home() / ".config/pc-mesh/control.json"
        config = read_json(operator_file) if args.config == Path.home() / ".config/pc-mesh/config.json" and operator_file.exists() else read_json(args.config)
        if not config or not isinstance(config.get("hubs"), list) or not config["hubs"]:
            ap.error("readable LAN control configuration required for diagnosis")
        reachable = 0
        for index, base in enumerate(config["hubs"], start=1):
            if not isinstance(base, str) or not base.startswith("https://"):
                print("Hub %d: invalid HTTPS endpoint" % index)
                continue
            try:
                snapshot = Client(dict(config, hubs=[base])).request("/fleet", timeout=6)
                if not isinstance(snapshot, dict) or not isinstance(snapshot.get("nodes"), list):
                    raise RuntimeError("invalid fleet response")
                print("Hub %d: GET /fleet succeeded; %d enrolled devices" % (index, len(snapshot["nodes"])))
                reachable += 1
            except (RuntimeError, OSError, ValueError, ssl.SSLError) as exc:
                # Report the error category without printing the bearer token
                # or certificate paths. No network address or request body is logged.
                detail = re.sub(r"[\x00-\x1f\x7f]", " ", str(exc))[:160]
                print("Hub %d: GET /fleet failed: %s" % (index, detail))
        return 0 if reachable else 2
    if args.action in ("line", "prompt", "watch", "status"):
        if args.action == "status":
            fleet = read_json(args.state / "fleet.json", {})
            if args.target:
                try:
                    ids = set(resolve_fleet_targets(fleet, args.target))
                except ValueError as e:
                    ap.error(str(e))
                fleet = dict(fleet, nodes=[node for node in fleet.get("nodes", []) if node.get("id") in ids])
            print(json.dumps(fleet, ensure_ascii=False, indent=2) if args.json else fleet_summary(fleet, color=ansi_enabled(args.color)))
        elif args.action == "line":
            print(fleet_line(read_json(args.state / "fleet.json", {})) or "[Updates] Statusdienst startet")
        elif args.action == "prompt":
            out, seq = prompt_output(args.state, args.since)
            print(out)
            print("PC_MESH_SEQ=" + str(seq))
        else:
            seq, previous = args.since, None
            while True:
                out, latest = prompt_output(args.state, seq)
                if out != previous:
                    print(out, flush=True)
                previous = out
                seq = latest
                time.sleep(1)
        return 0
    if args.action in ("refresh", "update", "tui") or (args.action == "sync" and args.target):
        operator_file = Path.home() / ".config/pc-mesh/control.json"
        config = read_json(operator_file) if args.config == Path.home() / ".config/pc-mesh/config.json" and operator_file.exists() else read_json(args.config)
        if not config:
            ap.error("LAN control configuration is required for this account")
        client = Client(config)
        if args.action == "tui":
            from tui import menu
            return menu(client, config)
        fleet = client.request("/fleet")
        wanted = (args.target or config.get("id", "")).lower()
        try:
            targets = resolve_fleet_targets(fleet, wanted)
        except ValueError as e:
            ap.error(str(e))
        control_action = "install" if args.action == "update" else args.action
        if wanted == "all":
            requests = [{"target": target, "action": control_action, "request_id": secrets.token_hex(12)} for target in targets]
            jobs = client.request("/control-batch", {"requests": requests}).get("jobs", [])
            if len(jobs) != len(requests):
                raise RuntimeError("hub returned an incomplete control batch")
        else:
            jobs = [client.request("/control", {"target": targets[0], "action": control_action, "request_id": secrets.token_hex(12)})]
        wait_seconds = (600 if args.action == "update" else 0) if args.wait is None else max(0, min(args.wait, 600))
        if not wait_seconds:
            for job in jobs:
                print("%s %s: %s [%s]" % (job["target"], job["action"],
                      colored_status(job["status"], ansi_enabled(args.color)), job["id"]), flush=True)
        previous = {j["id"]: j["status"] for j in jobs}
        deadline = time.time() + wait_seconds
        while wait_seconds and time.time() < deadline:
            states = {j["id"]: j for j in client.request("/fleet").get("commands", [])}
            if all(states.get(j["id"], {}).get("status") in update_control.TERMINAL for j in jobs):
                for j in jobs:
                    done = states[j["id"]]
                    print("%s: %s %s" % (done["target"], colored_status(done["status"], ansi_enabled(args.color)), done.get("detail", "")))
                return 0 if all(states[j["id"]]["status"] == "SUCCEEDED" for j in jobs) else 1
            for job in jobs:
                current = states.get(job["id"], {}).get("status")
                if current and current != previous[job["id"]]:
                    print("%s: %s [%s]" % (job["target"], colored_status(current, ansi_enabled(args.color)), job["id"]), flush=True)
                    previous[job["id"]] = current
            time.sleep(2)
        if wait_seconds:
            print("Wartezeit abgelaufen; Ausfuehrung nicht bestaetigt abgeschlossen. Laufende Installation wird nicht abgebrochen.", file=sys.stderr)
            return 2
        return 0
    config = read_json(args.config)
    if not config:
        ap.error("readable config file required")
    state = args.state
    state.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(state / "service.log", maxBytes=1000000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOG.setLevel(logging.INFO)
    LOG.addHandler(handler)
    if args.action == "daemon":
        daemon(config, state)
    elif args.action == "sync":
        results = [sync_repo(r, state, Client(config)) for r in config.get("repositories", [])]
        save_json(state / "git.json", results)
        print(json.dumps(results, ensure_ascii=False))
        return 1 if any(r["status"] in ("ERROR", "AUTH_OR_NETWORK_ERROR", "FF_FAILED", "VERIFY_FAILED") for r in results) else 0
    else:
        data = {"updates": collect_updates(state, Path(__file__).parent), "git": [], "os": platform.platform(), "agent": VERSION, "hostname": socket.gethostname()}
        save_json(state / "local.json", data)
        Client(config).request("/report", data)
        fleet = Client(config).request("/fleet")
        save_json(state / "fleet.json", fleet)
        print(fleet_line(fleet))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyboardInterrupt) as e:
        if not isinstance(e, KeyboardInterrupt):
            LOG.error("%s", e)
            print(str(e), file=sys.stderr)
        raise SystemExit(1)
