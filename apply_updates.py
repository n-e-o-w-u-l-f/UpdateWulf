#!/usr/bin/env python3
"""Explicit fixed native update operation. Never elevates or restarts a PC."""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from update_control import can_install


def native_plan():
    if os.name == "nt":
        ps = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
        return [[ps, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).with_name("apply_windows.ps1"))]]
    if platform.system() == "NetBSD":
        pkgin = shutil.which("pkgin") or "/usr/pkg/bin/pkgin"
        return [[pkgin, "-y", "update"], [pkgin, "-y", "upgrade"]]
    if shutil.which("pacman"):
        return [[shutil.which("pacman"), "-Syu", "--noconfirm"]]
    if shutil.which("apt-get"):
        apt = shutil.which("apt-get")
        return [[apt, "update"], [apt, "-y", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold", "--with-new-pkgs", "upgrade"]]
    raise RuntimeError("no supported native package manager")


def main():
    if not can_install():
        print("NEEDS_ADMIN: use a native owner-installed administrator/root service", flush=True)
        return 3
    environment = os.environ.copy()
    environment["DEBIAN_FRONTEND"] = "noninteractive"
    for args in native_plan():
        print(json.dumps({"phase": "RUNNING", "command": args}), flush=True)
        result = subprocess.run(args, stdin=subprocess.DEVNULL, env=environment)
        if result.returncode:
            print(json.dumps({"phase": "FAILED", "exit": result.returncode}), flush=True)
            return result.returncode
    print(json.dumps({"phase": "SUCCEEDED", "reboot": "never initiated by PC-Mesh"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
