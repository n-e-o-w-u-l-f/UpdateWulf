# Installation and operations

[Overview](../Readme.md) · [Configuration](configuration.md) · [Manual](manual.md) · [Troubleshooting](troubleshooting.md)

Choose a user installation for your own command line and a worker in your account. Choose a systemwide installation when the worker must start with the machine and use a deliberately provisioned native package-update helper. Installing a system worker does not configure every account's shell.

These instructions describe the supplied installers. They are not a claim that a deployment has been performed or tested on your computer. See the [verification record](documentation-status.md) for the checks actually completed.

## Before installation

1. Use the account that will own the installation. For a machine service, prepare its service account and filesystem permissions using your operating system's normal administration tools. The installer does not create that account.
2. Check the [platform requirements](../Readme.md#requirements). The core requires Python 3.9+. Application self-update additionally requires Git. Arch scanning needs `pacman`, `pacman-conf`, `vercmp` and a configured HTTPS mirror. Windows requires a real Python executable, Windows PowerShell, Windows Update Agent and Task Scheduler.
3. Complete [hub, certificate and member setup](configuration.md#first-setup). Each worker needs its own member identity/token and a trusted HTTPS endpoint. The example JSON files contain placeholders, not a functioning enrollment.
4. Keep `auto_self_update: false` and the member's `allow_install: false` during first setup. Enable package installation only after verifying the intended native helper and permissions.
5. Preserve existing configuration, state, shell profiles, scheduler definitions and the previous source version. Check whether a worker is already running; do not start a second scheduler for the same installation.
6. Stop a temporary foreground setup daemon before installing persistence. Finish any running package update before a service migration, rollback or removal. A CLI wait timeout does not mean the package manager has stopped.

Use the default configuration/state paths for a new user installation:

| Item | Unix | Windows |
| :--- | :--- | :--- |
| Configuration | `~/.config/pc-mesh/config.json` | `%USERPROFILE%\.config\pc-mesh\config.json` |
| Optional operator configuration | `~/.config/pc-mesh/control.json` | `%USERPROFILE%\.config\pc-mesh\control.json` |
| State | `~/.local/state/pc-mesh/` | `%USERPROFILE%\.local\state\pc-mesh\` |
| Commands | `~/.local/bin/` | `%USERPROFILE%\.local\bin\` |
| Installation record | `~/.config/pc-mesh/installation.json` | `%USERPROFILE%\.config\pc-mesh\installation.json` |

The historical `pc-mesh` directory name is intentional. JSON path values must be absolute paths; a literal `~` or `$HOME` inside JSON is not generally expanded. Configuration files contain credentials and belong outside the source checkout. The hub's private TLS key stays on the hub; clients need only the public trust material.

**Custom-path limitation:** the CLI accepts `--config` and `--state`, but application self-update does not consistently forward custom configuration paths and drops the custom state path on Unix activation. Installer-created command wrappers also do not embed a custom configuration path. Use explicit CLI `--config` where necessary, disable automatic application updates for such deployments, and perform a reviewed native handover. Do not assume that a successful custom-path install makes self-update safe for that layout.

## Obtain and retain the source

Use the [public repository](https://github.com/n-e-o-w-u-l-f/UpdateWulf) or its [source ZIP](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip). At this documentation baseline there are no published tagged release assets or native installer packages. A branch ZIP changes as `main` advances.

For a new Unix user checkout, choose a permanent directory that does not already contain another installation:

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git "$HOME/.local/share/updatewulf/source"
cd "$HOME/.local/share/updatewulf/source"
git rev-parse HEAD
python3 -c "import sys; assert sys.version_info >= (3, 9)"
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

Do not replace an existing checkout with this command. Inspect its local changes and remote history before updating it. Record the commit used for installation. The Unix installer references the source directory directly instead of copying the full program elsewhere; moving or deleting it breaks the wrappers and service. Keep configuration and state separate so they survive source replacement.

For a machine service, use a complete source tree at a permanent administrator-controlled location, such as a version-specific directory under `/opt/updatewulf/` or a protected Windows directory. In the examples below, paths containing `COMMIT`, `SERVICE_ACCOUNT` or `OPERATOR` are placeholders to replace with your actual values. Do not run them unchanged.

## Unix user installation

Run from the source directory as the actual user, without elevating to root:

```sh
python3 install.py
```

The shell entry point delegates to the same installer and forwards its arguments:

```sh
bash scripts/install.sh
```

To select a different Python executable for that wrapper, set `UPDATEWULF_PYTHON` to its executable name or absolute path. Do not include interpreter arguments in that value. For example:

```sh
UPDATEWULF_PYTHON=/usr/pkg/bin/python3 bash scripts/install.sh
```

The Python installer accepts these parameters:

| Parameter | Default / behavior |
| :--- | :--- |
| `--source PATH` | Directory containing `install.py`; must contain the required program files and Bash hook. |
| `--config PATH` | `~/.config/pc-mesh/config.json`; a readable JSON object is required for service installation. |
| `--state PATH` | `~/.local/state/pc-mesh`; must be writable by the user. |
| `--prompt-only` | Installs wrappers and shell integration without starting a worker. |

The current Unix installer checks required source files and the configuration's JSON syntax/type before changing profiles. This is not complete operational validation of certificates, tokens or connectivity. Follow the configuration guide first.

### What it installs

- Command wrappers `UpdateWulf`, `updatewulf`, `pc-mesh` and `pc-mesh-watch` in `~/.local/bin/`.
- Hook files under `~/.config/pc-mesh/`: `prompt.bash`, `prompt.sh`, `prompt.zsh`, `prompt.fish`, `prompt.tcsh`.
- Managed `# BEGIN PC-MESH` / `# END PC-MESH` blocks in `.bashrc`, `.zshrc`, `.config/fish/config.fish`, `.shrc`, `.kshrc`, `.tcshrc` and the selected login profile. The login profile is the first existing `.bash_profile`, `.bash_login` or `.profile`, otherwise `.profile`.
- A `.pc-mesh-backup-TIMESTAMP` copy before changing an existing profile. Unrelated profile content is preserved by the managed-block editor.
- An installation record at `~/.config/pc-mesh/installation.json`.

Interactive Bash receives a cached prompt header. Zsh, Fish and Tcsh use passive startup text. The shared `prompt.sh` currently includes a Bash guard, so sh/ksh do not receive equivalent dynamic prompt behavior. Bash color handling has a [known limitation](troubleshooting.md#known-issues).

### User service or cron fallback

When the systemd user manager is available, the installer creates `~/.config/systemd/user/updatewulf.service`, reloads the user manager and enables/starts `updatewulf.service`. This is a user-manager service; a systemwide boot guarantee without a user session depends on the machine's user-session policy, which this installer does not configure.

```sh
systemctl --user status updatewulf.service
systemctl --user show updatewulf.service -p ActiveState -p MainPID -p ExecStart
journalctl --user -u updatewulf.service -n 50 --no-pager
```

If the user manager cannot be used, the installer requires `crontab`, writes one managed `@reboot` entry and launches a detached worker immediately. It does not create a periodic supervisor. Inspect `crontab -l`, the recorded scheduler and `heartbeat.json`; a cron entry by itself does not prove that a reboot start works. `launcher.log` and `service.log` are in the selected state directory.

For shell integration alone:

```sh
python3 install.py --prompt-only
```

This mode does not collect status. It needs a cache supplied by an existing worker. Open a new terminal after installation. Bash and Zsh profiles add `~/.local/bin` to `PATH`; other shells may require the corresponding user-bin setup. You can always test the exact wrapper path, `"$HOME/.local/bin/updatewulf" --version`.

## Windows user installation

Use a normal PowerShell console in the account that will run UpdateWulf. Prepare `%USERPROFILE%\.config\pc-mesh\config.json` first. Confirm that `python.exe` resolves to a real interpreter rather than a WindowsApps/Store alias:

```powershell
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
& $Python .\pc_mesh.py --version
.\install_windows.ps1 -Python $Python
```

If command discovery selects an alias, set `$Python` to your actual installed interpreter path before continuing. Run scripts under your existing approved execution policy; this guide does not require a systemwide policy change.

| Parameter | Default / behavior |
| :--- | :--- |
| `-Source PATH` | Script directory. Keep the full source there. |
| `-Python PATH` | A real Python executable; the installer validates Python 3.9+. |
| `-Config PATH` | `%USERPROFILE%\.config\pc-mesh\config.json`. |
| `-State PATH` | Reuses `installation.json`'s state when present; otherwise `%USERPROFILE%\.local\state\pc-mesh`. |
| `-PromptOnly` | Installs profiles/wrappers only; no worker task is started. |
| `-Clink` | Accepted by the current script but not used to configure Clink. |

The installer creates `.cmd` wrappers in `%USERPROFILE%\.local\bin` and adds that directory to the user `PATH`. It adds managed blocks to the current Documents folder's `WindowsPowerShell` and `PowerShell` profiles: `profile.ps1`, `Microsoft.PowerShell_profile.ps1` and `Microsoft.VSCode_profile.ps1`. Existing changed profiles receive `.pc-mesh-backup-TIMESTAMP` copies. Configured folder redirection can place Documents outside `%USERPROFILE%\Documents`.

The persistent worker is the **`UpdateWulf-User`** scheduled task, triggered at the user's logon. It normally runs with limited privileges. Reinstallation preserves an existing explicitly elevated task and requires an elevated owner console when necessary. The script prefers the interpreter's adjacent `pythonw.exe` for the worker to avoid tying it to a console window; CLI wrappers still use the console interpreter.

```powershell
Get-ScheduledTask -TaskName 'UpdateWulf-User' | Select-Object TaskName, State
(Get-ScheduledTask -TaskName 'UpdateWulf-User').Actions
Get-Content -LiteralPath "$env:USERPROFILE\.local\state\pc-mesh\heartbeat.json"
```

The installer checks for a fresh worker heartbeat and attempts to restore previous task definitions if activation fails. Check the actual result rather than treating task registration as success. The Windows installer can modify profiles/wrappers before discovering a missing configuration; this remains a [known issue](troubleshooting.md#known-issues).

## Linux systemwide

This route requires an actual root session, live systemd, `/usr/bin/python3` 3.9+, `systemd-analyze`, `crontab`, a working polkit setup, an existing service account and that account's enrolled configuration. The helper does not invoke `sudo`, create the user or install these prerequisites.

The long-running announce service runs as the selected service account. A separate root-owned oneshot runs the fixed package-update code. A polkit rule grants that account the ability to start only that fixed service. The hub member's `allow_install` is a separate gate.

### Migrate an existing user installation first

The Linux helper retires managed user cron entries; it **does not disable an existing systemd user service**. Before a systemwide handover, finish all active update jobs, save the current unit/configuration and, in the actual user session:

```sh
systemctl --user disable updatewulf.service
touch "$HOME/.local/state/pc-mesh/stop.request"
```

Wait until the verified worker PID exits. Confirm that no package-update process remains, then stop the unit through its manager:

```sh
systemctl --user stop updatewulf.service
systemctl --user is-active updatewulf.service
```

Use the actual custom state path instead if applicable. If the worker does not exit or the update is still running, inspect the logs and postpone migration; do not force-kill the worker or package manager. Preserve the old unit for rollback. Skip these user-unit commands when that unit does not exist. Managed cron migration is handled by the native helper after successful activation.

### Install the native services

In the root session, replace the example values with the prepared account and paths:

```sh
/usr/bin/python3 /opt/updatewulf/COMMIT/enable_machine_updates.py \
  --user SERVICE_ACCOUNT \
  --source /opt/updatewulf/COMMIT \
  --config /home/SERVICE_ACCOUNT/.config/pc-mesh/config.json \
  --state /home/SERVICE_ACCOUNT/.local/state/pc-mesh
```

The service account must be able to read the source, configuration and certificate and write the state directory. Root's fixed installer code must remain administrator-controlled. If the configuration uses `announce_only: true`, set `machine_control: true` so the worker accepts refresh/install requests. The helper sets `native_installer: true`; it does not add the hub's `allow_install` permission.

| Installed item | Location / identity |
| :--- | :--- |
| Persistent worker | `/etc/systemd/system/pc-mesh-announce.service`, runs as `--user` |
| Fixed privileged installer | `/etc/systemd/system/pc-mesh-install.service`, root oneshot |
| Protected installer source | `/usr/local/lib/pc-mesh-installer/` |
| Installer state/log | `/var/lib/pc-mesh-installer/status.json`, `installation.log` |
| Narrow polkit rule | `/etc/polkit-1/rules.d/49-pc-mesh-installer.rules` |
| Previous managed cron backup, when needed | `/var/lib/pc-mesh-installer/previous-user-crontab.txt` |

```sh
systemctl status pc-mesh-announce.service
systemctl show pc-mesh-announce.service -p ActiveState -p MainPID -p ExecStart
journalctl -u pc-mesh-announce.service -n 50 --no-pager
```

The installation starts the announce worker and verifies a fresh heartbeat; it does not start package upgrades. Do not start `pc-mesh-install.service` merely as an installation check: that service performs real package updates. For an operator in another account, configure that operator's own credentials and explicitly select a readable machine state cache when needed; installing the machine service does not grant another account a working shell profile or copy credentials into it.

## Windows systemwide

Use an elevated console of the enrolled owner. Prepare a complete, trusted source tree, a real Python installation and a working owner configuration. This script copies the Python runtime and program code into protected `%ProgramData%\PC-Mesh-Installer`; it requires administrator rights and does not request elevation itself.

```powershell
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$UpdateWulfSource = 'C:\Program Files\UpdateWulf\COMMIT'
$UpdateWulfOwner = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& (Join-Path $UpdateWulfSource 'enable_machine_updates_windows.ps1') `
  -Source $UpdateWulfSource `
  -Python $Python `
  -Config "$env:USERPROFILE\.config\pc-mesh\config.json" `
  -Owner $UpdateWulfOwner
```

`-Python` is required. `-Source` defaults to the script directory, `-Config` to the current owner's standard configuration and `-Owner` to the current Windows identity. Running as a different administrator changes `%USERPROFILE%`; do not silently substitute that account for the enrolled owner.

| Item | Name / location |
| :--- | :--- |
| Boot worker task | `PC-Mesh-Announce-System`, SYSTEM, at startup |
| Fixed update task | `PC-Mesh-Install`, SYSTEM, on request |
| Protected code/runtime | `%ProgramData%\PC-Mesh-Installer\code`, `python` |
| Machine configuration/trust | `%ProgramData%\PC-Mesh-Installer\config.json`, `hub.crt` |
| Machine worker state | `%ProgramData%\PC-Mesh-Installer\announce-state` |
| Package installer status/log | `%ProgramData%\PC-Mesh-Installer\status.json`, `installation.log` |

The generated machine configuration sets `announce_only`, `machine_control` and `native_installer` to `true`, clears `repositories` and removes the `hub` block. This setup creates a client worker, not a Windows SYSTEM-hosted hub. If an SSH tunnel is configured, it provisions a separate SYSTEM transport key using the existing authenticated owner route; it does not reuse the user's private SSH key.

The script requests a cooperative stop of the previous owner worker, starts the machine task and checks a fresh machine heartbeat before retiring recognized user tasks. Keep existing task definitions/configuration for recovery. No package update is started during this setup.

```powershell
Get-ScheduledTask -TaskName 'PC-Mesh-Announce-System','PC-Mesh-Install' |
  Select-Object TaskName, State
Get-Content -LiteralPath "$env:ProgramData\PC-Mesh-Installer\announce-state\heartbeat.json"
```

Existing user wrappers may still read their old user state directory. In the actual operator account, point the shell integration at the readable machine cache **without starting another worker**:

```powershell
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$UpdateWulfSource = "$env:ProgramData\PC-Mesh-Installer\code"
& (Join-Path $UpdateWulfSource 'install_windows.ps1') `
  -Source $UpdateWulfSource `
  -Python $Python `
  -State "$env:ProgramData\PC-Mesh-Installer\announce-state" `
  -PromptOnly
```

Use the operator's own `control.json` for control requests. A machine cache is not a substitute for authorization. Do not run the ordinary user installer or user self-update against this machine-managed worker as a workaround for a handover failure.

## NetBSD systemwide

This installer requires actual NetBSD and a root session, a readable complete source tree, the chosen Python interpreter, enrolled configuration, `crontab`, `rcorder` and the native rc framework. It installs a **root-owned worker**. Use root-controlled source/configuration paths because the worker can execute package updates directly.

```sh
/usr/pkg/bin/python3 /opt/updatewulf/COMMIT/enable_machine_updates_netbsd.py \
  --source /opt/updatewulf/COMMIT \
  --config /root/.config/pc-mesh/config.json \
  --state /root/.local/state/pc-mesh \
  --python /usr/pkg/bin/python3
```

`--config` and `--state` are required. `--source` defaults to the script directory and `--python` to the running interpreter. Use the interpreter that actually exists on your NetBSD installation; the example path is not an installation command for Python.

The root worker can use the direct native `pkgin` route. Leave `native_installer: false` for this path: the alternate native-helper flag currently routes Unix requests to the Linux systemd helper. With `announce_only: true`, set `machine_control: true` to enable its request worker. Keep automatic application self-update disabled and use native handovers for this root deployment.

| Item | Location |
| :--- | :--- |
| rc.d service | `/etc/rc.d/updatewulf` |
| Service settings | `/etc/rc.conf.d/updatewulf` |
| PID file | `/var/run/updatewulf.pid` |
| Existing rc/cron backups | `/var/backups/updatewulf/` |

The installer validates rc ordering, requests cooperative shutdown of the previous worker, starts the service, verifies its heartbeat and only then removes recognized root cron supervision. It does not retire a different account's worker: stop such an older deployment separately before handing over the same member identity.

```sh
/etc/rc.d/updatewulf status
```

### Optional NetBSD operator CLI for root

If an enrolled non-root operator already has `~/.local/bin/updatewulf`, the separate helper can install `/usr/local/bin/UpdateWulf` and `/usr/local/bin/updatewulf`. These shims drop root privileges before executing that operator's wrapper; they do not copy credentials or install a second daemon.

```sh
/usr/pkg/bin/python3 install_netbsd_root_cli.py \
  --operator OPERATOR \
  --bin-dir /usr/local/bin \
  --python /usr/pkg/bin/python3 \
  --dry-run
```

After inspecting a successful dry run, repeat without `--dry-run` to create the shims. Always supply `--operator` explicitly. The helper's historical default account may not exist on your system. The target directory must already exist, and the operator wrapper must have the correct owner and executable permissions.

## Termux user installation

Run inside the actual Termux app session, with the source retained in app-owned storage and the enrolled configuration already present:

```sh
python install_termux.py
```

Options are `--source`, `--config` and `--state`, with the normal user defaults. The helper validates a Termux `PREFIX`, installs shell integration, creates `~/.termux/boot/50-updatewulf.sh` and starts a worker if the state lock is not already held. It uses `termux-wake-lock` when available.

Install Termux:Boot and open it once if you want startup after a device reboot. Android background restrictions can still affect availability. The source does not establish a completed physical Android reboot test. UpdateWulf manages Termux packages in this mode, not Android system updates.

**Use a manual Termux application handover and keep `auto_self_update: false`.** The generic application updater currently invokes the Unix `install.py`, not `install_termux.py`. It therefore does not update the Termux boot hook and can fail when systemd/cron are absent. To change the program version, retain the previous source, finish active package work, stop the old worker cooperatively, and run the new version's `install_termux.py` with the existing `--config` and `--state` paths. Verify the boot hook's source path and fresh heartbeat before retiring the old source. Do not use `updatewulf --self update` as the supported Termux activation path.

## Verify the installation

Open a new terminal in the intended operator account:

```sh
updatewulf --version
updatewulf diagnose
updatewulf status --json
```

Also inspect the selected native service/task and the actual state directory's `heartbeat.json`. Verify the worker's process identity, the scheduled source path and a fresh report for the enrolled member. A wrapper version alone does not prove the background worker uses the same source. A cached `status` result or a zero command exit alone does not prove successful connectivity or a completed package scan.

When the member's request worker is enabled, `updatewulf workstation.local refresh --wait 60` requests a new scan without installing packages. Replace the hostname with your enrolled target. Verify its timestamp and result; a scan may legitimately be `CACHED`, `ERROR` or `UNSUPPORTED`. Do not use a real package upgrade as a harmless smoke test.

## Rollback

Preserve the last working source, configuration, installation record, managed profile backups and scheduler definition before a handover. Rollback changes which program version runs; it does not undo packages already upgraded by the OS package manager.

1. Stop issuing new update requests and let native package work finish. Inspect both hub job state and native installer status/logs.
2. Disable the installed worker's future startup and request its cooperative stop using the actual state directory. Confirm the process has exited before switching source paths. Systemd machine workers have `Restart=always`; a `stop.request` alone is not a durable stop. Stop the unit through systemd once native package work has finished.
3. Restore the previous verified source path with the matching native installer/runbook. For a Unix user installation, invoke the previous `install.py` with the correct `--source`, `--config` and `--state`; for Windows user setup, use its previous `install_windows.ps1` with `-Source`, `-Python`, `-Config` and `-State`. Keep credentials and state intact.
4. For a machine installation, restore its known previous service/task definition, protected runtime and native helper together. Do not replace a system worker with the user installer. The NetBSD helper preserves older rc/cron files under `/var/backups/updatewulf/`; review their contents before restoring them.
5. Start only the chosen worker and repeat the version, process, heartbeat, connection and fresh-scan checks. Keep a failed candidate for diagnosis until you know which files are safe to remove.

Public self-update retains the immediately previous release and attempts an automatic installer rollback on Windows. Unix does not implement an equivalent automatic rollback. An origin marker is useful provenance, not a substitute for verifying the actual running process. See [self-update behavior](manual.md#application-self-update).

When restoring shell configuration, compare the `.pc-mesh-backup-TIMESTAMP` file with the current profile. Restoring a whole old profile can erase unrelated changes made since installation; remove or restore only the managed block unless you have explicitly reviewed the complete replacement.

## Uninstall

There is no automatic cross-platform uninstaller. `bash scripts/uninstall.sh --help` prints guidance and changes nothing; invoking the script without a help flag returns exit 2 without removal. It no longer removes unrelated GitSync files or services.

### Stop work and disable the correct persistence

First stop submitting new package-update requests, ensure no active package manager remains, and identify the service owner, state directory and source from the installed definitions. Keep configuration, certificates, keys, logs and job history by default. Do not use `kill`, `taskkill` or task termination to resolve a package-update timeout.

| Installation | Controlled shutdown |
| :--- | :--- |
| systemd user | In the owner session, disable `updatewulf.service`, create `stop.request` in its state directory, wait for the verified worker PID to exit, then stop that user unit. |
| Unix cron fallback | With `crontab -e`, remove only the recognized `BEGIN UPDATEWULF` or `BEGIN PC-MESH` block; create `stop.request` in its state directory and wait for that worker to exit. Preserve all unrelated cron entries. |
| Linux machine | Disable `pc-mesh-announce.service`; request cooperative stop and stop the unit through systemd after native package work finishes. Its automatic restart policy means a stop-request file alone is insufficient. Do not stop an active `pc-mesh-install.service`. |
| Windows user | Disable the verified `UpdateWulf-User` task, create `stop.request` in the selected state directory and wait for its actual worker process to exit. |
| Windows machine | Disable `PC-Mesh-Announce-System` to prevent another boot start, create `stop.request` under its `announce-state` directory and wait for the actual worker to exit. Keep `PC-Mesh-Install` untouched while it is running. |
| NetBSD machine | Set `updatewulf=NO` in the verified `/etc/rc.conf.d/updatewulf`; as root, run `/etc/rc.d/updatewulf onestop` and verify that the worker exits. The `one` prefix permits cooperative shutdown despite the disabled startup flag and preserves the other checks in [rc.subr(8)](https://man.netbsd.org/rc.subr.8). If shutdown fails, investigate instead of forcing termination. |
| Termux | Move only the marker-verified `50-updatewulf.sh` outside `~/.termux/boot/` so Termux:Boot cannot execute it; request cooperative stop in the worker state and wait for exit. |

For a default Unix user installation, the stop request is:

```sh
touch "$HOME/.local/state/pc-mesh/stop.request"
```

For a default Windows user installation, after disabling its confirmed task:

```powershell
Disable-ScheduledTask -TaskName 'UpdateWulf-User'
New-Item -ItemType File -Path "$env:USERPROFILE\.local\state\pc-mesh\stop.request" -Force
```

Use the machine state's actual path for system installations. Check the real process and package-manager state before proceeding; do not rely on an old PID number alone. If a worker will not stop, retain the installation and resolve the blocker before removing its files.

### Remove only verified UpdateWulf components

After the worker and any native installer are confirmed stopped:

- Remove only UpdateWulf's `BEGIN PC-MESH` / `END PC-MESH` blocks from the affected profiles. Preserve unrelated content and retain the backups until the shell starts correctly.
- Remove individual `UpdateWulf`, `updatewulf`, `pc-mesh` and `pc-mesh-watch` wrappers only after their contents match this installation's source/interpreter. Windows uses `.cmd` wrappers. Names alone do not prove ownership.
- Remove generated `prompt.*` files only after verifying their managed content; retain the rest of `~/.config/pc-mesh/`. Do not recursively delete this directory because it also stores credentials and configuration.
- For systemd, remove only the verified UpdateWulf unit files and, when applicable, its exact polkit rule and protected helper files. Reload the appropriate system or user manager with `systemctl daemon-reload` or `systemctl --user daemon-reload`. Keep state and logs.
- For Windows, inspect the task actions/principals before unregistering the stopped UpdateWulf tasks. Remove the user-bin `PATH` entry only if no other programs use that directory. Do not delete the whole user-bin directory or all PowerShell profiles.
- For NetBSD, remove only the verified rc.d/config entries and optional shims identified by their managed marker. Preserve backups and user data; do not remove unrelated files in `/usr/local/bin`.
- Retire an obsolete source/release directory only after confirming that no service, task, wrapper or other user references it and that it contains no unrecognized data. There is no blanket recursive deletion command in this procedure.

Reopen the affected shells and verify that no managed header remains, no UpdateWulf worker restarts, and unrelated shell functions still work. Remove the member or operator authorization from the hub separately only if that identity is also being retired; controlled hub restart is required for configuration changes.

## Implementation references

| Source | Responsibility |
| :--- | :--- |
| [install.py](../install.py) | Unix preflight, managed profiles, wrappers, systemd user service and cron fallback. |
| [scripts/install.sh](../scripts/install.sh) / [scripts/uninstall.sh](../scripts/uninstall.sh) | User installer wrapper / deliberately non-destructive removal guidance. |
| [install_windows.ps1](../install_windows.ps1) | Windows profiles, wrappers, user task and activation checks. |
| [enable_machine_updates.py](../enable_machine_updates.py) | Linux machine worker and fixed privileged installer. |
| [enable_machine_updates_windows.ps1](../enable_machine_updates_windows.ps1) | Protected Windows runtime, SYSTEM tasks and owner handover. |
| [enable_machine_updates_netbsd.py](../enable_machine_updates_netbsd.py) | Native NetBSD rc.d worker. |
| [install_netbsd_root_cli.py](../install_netbsd_root_cli.py) | Privilege-dropping NetBSD root operator shims. |
| [install_termux.py](../install_termux.py) | Termux app-owned worker and boot hook. |
| [self_update.py](../self_update.py) | Staging, activation, rollback attempt and conservative release retention. |

The [manual](manual.md) describes command behavior, return codes, logging and self-update. The [configuration reference](configuration.md) owns the full setting/default table, enrollment procedure and credential precedence.
