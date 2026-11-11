# UpdateWulf

Public cross-platform update status and operator-controlled update service.

## Application self-update

From a **previously installed public release**:

```sh
updatewulf --self update
```

This checks the maintained public GitHub `main` branch, verifies the Git
object database and commit ancestry, tests the staged source, and activates
a commit-named program release. Config, secrets, host enrollment, task state,
and shell customization live outside the program release and are preserved.
At least the immediate previous release is retained for rollback. Only
unreferenced, marker-verified old public program releases may be removed;
unrecognized files and package-manager databases are never deleted.

A one-time migration from an older private-source installation requires
an explicitly operator-invoked bootstrap via its native installer.
The command `updatewulf --self update` on the new version recognizes
legacy origin markers and uses that migration path only once.

```sh
updatewulf --self update --check
updatewulf --version
updatewulf status
```

**Important:** `updatewulf update HOST` requests native OS package updates
via an enrolled, authenticated host and is unrelated to application self-update.
No automatic unattended OS upgrade or reboot is performed by this command.
Machine-managed services must use their existing authorized privileged
handover; an unprivileged account is not allowed to create duplicate workers.

The project supplies Python 3.9+ portable code, Windows PowerShell adapters,
Linux systemd/user adapters, NetBSD and Termux integration. Windows WUA
support and other platform managers have different acceptance levels;
unsupported managers are reported, not silently counted as zero.

Git repository synchronization is a compatibility feature during the
migration to GitSyncWulf and is not an authority to overwrite local Git
changes or to use another host as a Git remote.

## Source verification

```sh
python3 -m py_compile pc_mesh.py update_control.py self_update.py tui.py owner_profiles.py
python3 test_update_announce.py
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh scripts/uninstall.sh
```

Installer actions require the appropriate actual OS account and
a saved rollback. Public source availability does not grant administrator
privileges. No project secrets or host-specific configs are shipped.
