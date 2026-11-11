#!/usr/bin/env python3
"""Install the NetBSD UpdateWulf CLI for root without copying user credentials.

This is independent of rc.d worker setup. Run once as root on the target.
Creates /usr/local/bin/UpdateWulf and /usr/local/bin/updatewulf;
both delegate to an enrolled operator only *after* dropping root privileges.
Never edits /etc/rc.conf, shell profiles, service state or update jobs.
"""
import argparse
import os
import platform
import pwd
import stat
import tempfile
from pathlib import Path

MAGIC = "# UpdateWulf managed NetBSD operator CLI shim v1"


def shim_source(operator, operator_cli, interpreter):
    """Generated standalone CLI. Other local users must not borrow credentials."""
    return """#!{interpreter}
{magic}
import os
import pwd
import sys

OPERATOR = {operator!r}
OPERATOR_CLI = {cli!r}
account = pwd.getpwnam(OPERATOR)
uid = os.geteuid()
if uid == 0:
    # Drop root privileges *before* executing the operator-owned wrapper.
    os.initgroups(account.pw_name, account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.environ.clear()
    os.environ.update({{
        'HOME': account.pw_dir,
        'LOGNAME': account.pw_name,
        'USER': account.pw_name,
        'PATH': '/usr/pkg/bin:/usr/local/bin:/usr/bin:/bin',
    }})
elif uid != account.pw_uid:
    print('UpdateWulf: not enrolled for this account', file=sys.stderr)
    raise SystemExit(126)
os.execv(OPERATOR_CLI, [OPERATOR_CLI, *sys.argv[1:]])
""".format(interpreter=interpreter, magic=MAGIC,
           operator=operator, cli=operator_cli)


def verify_target(path, contents):
    if path.is_symlink():
        raise RuntimeError("refusing symlinked CLI path: " + str(path))
    if path.exists():
        if not path.is_file() or MAGIC not in path.read_text(encoding="utf-8"):
            raise RuntimeError("refusing unmanaged existing CLI: " + str(path))
    if not contents.startswith("#!/"):
        raise RuntimeError("invalid generated executable")


def install(operator="andreas", bin_dir=Path("/usr/local/bin"),
            python=Path("/usr/pkg/bin/python3"), dry_run=False):
    if platform.system() != "NetBSD":
        raise RuntimeError("NetBSD target required")
    if os.geteuid() != 0:
        raise RuntimeError("run as an actual root owner; no elevation attempted")
    account = pwd.getpwnam(operator)
    operator_cli = Path(account.pw_dir) / ".local/bin/updatewulf"
    if (not operator_cli.is_file() or operator_cli.is_symlink() or
            not os.access(operator_cli, os.X_OK) or
            operator_cli.stat().st_uid != account.pw_uid):
        raise RuntimeError("verified operator CLI missing or wrong owner: " +
                           str(operator_cli))
    if not python.is_file() or not os.access(python, os.X_OK):
        raise RuntimeError("NetBSD Python interpreter not executable")
    bin_dir = bin_dir.resolve(strict=True)
    if not bin_dir.is_dir() or (bin_dir.stat().st_mode & stat.S_IWOTH):
        raise RuntimeError("CLI directory missing or writable by everybody")
    contents = shim_source(operator, str(operator_cli), str(python))
    compile(contents, str(bin_dir / "updatewulf"), "exec")
    paths = [bin_dir / name for name in ("UpdateWulf", "updatewulf")]
    for path in paths:
        verify_target(path, contents)
    if dry_run:
        print("NetBSD root operator CLI: prerequisites verified, no files changed")
        return
    for path in paths:
        fd, temporary = tempfile.mkstemp(prefix=".updatewulf-cli-", dir=bin_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(contents)
                stream.flush()
                os.fchmod(stream.fileno(), 0o755)
            # The only existing targets accepted above are our own shims.
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        if path.read_text(encoding="utf-8") != contents:
            raise RuntimeError("CLI write verification failed: " + str(path))
        print("Verified " + str(path))
    print("No update was started and no service process was restarted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator", default="andreas")
    parser.add_argument("--bin-dir", type=Path, default=Path("/usr/local/bin"))
    parser.add_argument("--python", type=Path, default=Path("/usr/pkg/bin/python3"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    install(args.operator, args.bin_dir, args.python, args.dry_run)


if __name__ == "__main__":
    main()
