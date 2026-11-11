<div align="center">

# UpdateWulf

### Your updates. Your systems. Your decision.

**See pending updates across your computers. Start native package updates when you choose.**

[Download](#download) · [Get started](#quick-start) · [Install](#installation) · [Manual](docs/manual.md) · [Troubleshooting](docs/troubleshooting.md)

**English** · [Deutsch](Readme.de.md) · [Français](Readme.fr.md) · [Русский](Readme.ru.md) · [Español](Readme.es.md) · [Polski](Readme.pl.md) · [Português](Readme.pt.md)

</div>

![UpdateWulf terminal preview with illustrative fleet data](docs/assets/terminal-preview.svg)

---

| One view | Explicit control | A separate application update |
| :--- | :--- | :--- |
| Cached status for enrolled computers, including stale and offline states. | An authenticated request starts the target's native package updater. | UpdateWulf updates its own program files from its public GitHub repository. |

## At a glance

UpdateWulf is a Python service and command-line tool for a small, trusted computer fleet. An HTTPS hub receives update reports; each enrolled computer runs a worker. Shell integration displays cached results without contacting the network at every prompt.

The public source currently reports **version 2.1.0**. It includes adapters for **APT, pacman, NetBSD pkgin and Windows Update Agent**. Platform adapters and native acceptance tests have different coverage; see [requirements](#requirements) and the [verification record](docs/documentation-status.md). The seven README translations do **not** imply seven fully translated program interfaces: some runtime messages remain German.

### Where it fits

- A home lab or small fleet whose update status you want to see in one terminal.
- Linux, Windows and NetBSD machines with their existing native package managers.
- SSH sessions where a compact status line is more useful than a dashboard.
- Operators who want to choose when package updates run and retain the existing OS privilege boundary.

UpdateWulf is not a backup system or a general software deployment platform. It does not implement winget, Flatpak, Snap, Homebrew or automatic reboot management. Repository synchronization remains a legacy compatibility feature; new Git synchronization belongs in GitSyncWulf.

## Quick start

**Just explore the program:** use Python 3.9+ and Git for the clone below, or download and extract the source ZIP first. No service or configuration is needed.

```sh
git clone https://github.com/n-e-o-w-u-l-f/UpdateWulf.git
cd UpdateWulf
python3 pc_mesh.py --version
python3 pc_mesh.py --help
```

On Windows, use `py -3` instead of `python3` if that is your Python launcher.

**Already installed and enrolled?** Open a new terminal:

```sh
updatewulf status
updatewulf status --json
updatewulf diagnose
updatewulf --self update --check
```

`status` reads a local snapshot. `diagnose` checks the configured HTTPS hub. `--self update --check` reads the public release branch without installing it. An empty snapshot is not proof that all computers are up to date.

## Requirements

| Platform | Runtime and native adapter | Installation route | Current limits |
| :--- | :--- | :--- | :--- |
| Debian / Raspberry Pi OS | Python 3.9+, `apt-get` | User service; systemd machine service | Fresh scans use a separate metadata cache. |
| Arch Linux | Python 3.9+, `pacman`, `vercmp` | User service; systemd machine service | Repository metadata and package updates need network access. |
| Windows | Python 3.9+ with a real `python.exe`; Windows PowerShell and Windows Update Agent | User scheduled task; elevated machine tasks | No winget adapter; native Windows tests were not run in this documentation session. |
| NetBSD | Python 3.9+, `pkgin` | User cron fallback; native `rc.d` service | Non-root scans can use cached pkgin metadata. |
| Android / Termux | Python 3.9+, APT, actual Termux account | Termux boot hook | Requires Termux:Boot for reboot startup; not an Android OS updater. |
| Other platforms | Python may run the CLI | No complete native installation recipe | Unsupported collectors report `UNSUPPORTED`, not zero updates. |

All networked workers need an enrolled configuration, an HTTPS hub, its trusted certificate, a unique member token and writable state storage. **Git is required for application self-update.** Unix user installation needs a working systemd user manager or `crontab`; Bash is required for `scripts/install.sh`. Optional legacy enrollment helpers use Paramiko; the core service uses Python's standard library.

## Download

- [Download the current source ZIP](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip).
- [Browse the source](https://github.com/n-e-o-w-u-l-f/UpdateWulf).
- [Check published releases](https://github.com/n-e-o-w-u-l-f/UpdateWulf/releases).

At the documentation baseline, no tagged release assets, MSI, EXE, DEB or PKG installers were published. The ZIP follows the moving `main` branch. For a reproducible installation, record the downloaded commit with `git rev-parse HEAD` when using a clone. Do not treat the ZIP as a signed native installer.

## Installation

### Choose the scope

| You need… | Choose… | What changes |
| :--- | :--- | :--- |
| Commands and a shell status line for your account | User installation | Your wrappers, managed shell-profile blocks and an optional user worker. |
| A worker that starts with the computer and can run authorized OS updates | Systemwide service | OS-native service/task, protected package-update helper and explicit owner configuration. |
| Only to inspect the tool | Source checkout | Run `pc_mesh.py --help` / `--version`; no installation required. |

**First configure enrollment:** follow [hub and member setup](docs/configuration.md#first-setup). The examples in [examples/](examples/) contain placeholders, not usable credentials. Store your completed configuration outside the source tree, normally at `~/.config/pc-mesh/config.json` (`%USERPROFILE%\.config\pc-mesh\config.json` on Windows). Keep the downloaded program directory in a permanent location: installers point to it.

### Install for your user

Run from the downloaded source directory as the account that will use UpdateWulf:

```sh
# Unix: install wrappers, shell integration and a persistent user worker.
python3 install.py
```

```powershell
# Windows PowerShell: use the actual Python executable, not a Store alias.
$Python = (Get-Command python.exe -ErrorAction Stop).Source
& $Python -c "import sys; assert sys.version_info >= (3, 9)"
.\install_windows.ps1 -Python $Python
```

For shell integration only, use `python3 install.py --prompt-only` or `.\install_windows.ps1 -Python $Python -PromptOnly`. This does not collect fresh status; it needs an existing worker's cache. Termux uses `python install_termux.py` in the actual Termux session. Termux application upgrades currently require a manual native handover; keep `auto_self_update: false` because the general updater does not update its boot hook.

Open a new terminal and run `updatewulf --version`, `updatewulf diagnose` and `updatewulf status`. The [installation guide](docs/installation.md) explains paths, startup, verification and rollback.

### Install systemwide

Systemwide means a native machine worker and controlled package-update privilege; it does not automatically configure every user's shell. Prepare a dedicated service account and its enrolled configuration first. Use a permanent, administrator-controlled source path and follow the platform-specific handover steps:

- [Linux / systemd](docs/installation.md#linux-systemwide): `enable_machine_updates.py --user … --config … --state … --source …`, from an actual root session.
- [Windows](docs/installation.md#windows-systemwide): `enable_machine_updates_windows.ps1 -Python … -Config … -Owner …`, from an elevated owner console.
- [NetBSD](docs/installation.md#netbsd-systemwide): `enable_machine_updates_netbsd.py --config … --state … --python …`, from an actual root session.

These installers do not elevate themselves. A machine-managed installation uses its native release handover, not the user-level self-update installer.

## Everyday examples

Replace `workstation.local` with a reported/enrolled hostname, or use the exact member ID. Host-first and action-first forms are both accepted.

| Goal | Command | Effect |
| :--- | :--- | :--- |
| Read cached fleet status | `updatewulf status` | Local read. |
| Read one computer | `updatewulf workstation.local status` | Local filtered snapshot. |
| Export status | `updatewulf status --json` | Raw snapshot, including timestamps. |
| Disable CLI colors | `updatewulf status --no-color` | Plain text. |
| Diagnose the connection | `updatewulf diagnose` | Authenticated `GET /fleet`; no update job. |
| Request a fresh scan | `updatewulf workstation.local refresh --wait 60` | Enqueues a scan and waits up to 60 seconds. |
| Install OS package updates | `updatewulf workstation.local update --wait 600` | Explicit native update request; requires enrollment and target privilege. |
| Queue without waiting | `updatewulf workstation.local update --wait 0` | Prints the queued job; does not prove completion. |
| Open the menu | `updatewulf tui` | Interactive operator menu; see known empty-fleet issue. |
| Check UpdateWulf itself | `updatewulf --self update --check` | Reads the public application branch. |
| Update UpdateWulf itself | `updatewulf --self update` | Stages, checks and activates application source for a supported user installation. |

`updatewulf all update` requests updates for **all enrolled targets**. Use it only when that is your intended scope. A CLI timeout does not cancel a package manager already running. The complete action/option reference and exit codes are in the [manual](docs/manual.md).

## Configuration

Configuration is JSON. Start with [client](examples/config.client.json), [hub](examples/config.hub.json) or [operator](examples/control.json), then follow the [complete configuration reference](docs/configuration.md). JSON paths are literal: use absolute paths; `~` and environment variables are not generally expanded inside JSON strings.

| Setting | Code default | Meaning |
| :--- | :--- | :--- |
| `scan_interval` | `1800` seconds | Time between package scans. |
| `report_interval` | `20` seconds | Time between hub reports. |
| `auto_self_update` | `true` | Enables the application updater where the worker mode allows it. |
| `self_update_interval` | `21600` seconds | Application check interval; clamped to 1–24 hours, after an initial 5-minute wait. |
| `self_update_branch` | `main` | Public application branch. |
| `announce_only` | `false` | Disables legacy Git work; with `machine_control: false`, also disables the request worker. |
| `machine_control` | `false` | Enables refresh/install requests in announce-only mode. |
| `native_installer` | `false` | Routes installs through a previously provisioned native helper. |

The examples deliberately set `auto_self_update: false` so the first setup is predictable. Enable it after verifying a public user installation. For operator commands, a default-path `control.json` takes precedence over `config.json`; an explicit non-default `--config` selects that file. Custom configuration/state paths have self-update limitations described in [known issues](docs/troubleshooting.md#known-issues).

## Services, status and self-update

The user service is `updatewulf.service` on systemd or `UpdateWulf-User` in Windows Task Scheduler. Machine service names differ; the [installation guide](docs/installation.md) lists each one. Logs and snapshots normally live under `~/.local/state/pc-mesh/`, including `service.log`, `heartbeat.json`, `fleet.json` and `executed-commands.json`.

Status can be `OK`, `CACHED`, `CHECKING`, `UNKNOWN`, `ERROR` or `UNSUPPORTED`. Cached and offline data remain visible without being represented as a fresh successful scan. Jobs have their own states, including `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_ADMIN`, `EXPIRED` and `INTERRUPTED`.

Application self-update verifies repository identity, Git object integrity and ancestry, runs the staged checks and keeps the current and previous release. Git verification is not a release-signature scheme. A first migration requires an explicit operator command. Existing configuration and enrollment live outside the release directory. Rollback and conservative cleanup limits are explained in the [manual](docs/manual.md#application-self-update).

## Known issues and troubleshooting

The [issue guide](docs/troubleshooting.md#known-issues) records concrete limitations and workarounds. Currently:

- No complete cross-platform uninstaller; follow the [manual removal procedure](docs/installation.md#uninstall).
- User self-update does not reliably carry custom Unix state/configuration paths forward; use default paths or a manual native handover.
- The TUI can fail when navigating an empty fleet; use `status` and `diagnose` until a member is enrolled.
- Bash prompt integration does not fully honor `NO_COLOR`; use `status --no-color` for guaranteed plain CLI output.
- Unknown release contents, including additional documentation directories, conservatively prevent automatic pruning.
- macOS/Homebrew, winget, Flatpak and Snap adapters and complete runtime translation are not implemented.

For a missing command, open a new shell and check your user bin directory. For `NEEDS_ADMIN`, verify the native helper and member's `allow_install` permission. For TLS or authentication errors, verify the certificate, hostname and enrollment. Do not replace a failed check with an assumed zero-update count.

## Manual and project information

| Documentation | Contents |
| :--- | :--- |
| [Installation](docs/installation.md) | User/system setup, services, verification, rollback and uninstall. |
| [Manual](docs/manual.md) | Every CLI action and option, examples, statuses, logs and self-update. |
| [Configuration](docs/configuration.md) | Hub/member/operator setup, keys, defaults, paths and precedence. |
| [Troubleshooting](docs/troubleshooting.md) | Symptoms, known bugs, practical workarounds and FAQ. |
| [Verification](docs/documentation-status.md) | What was checked and what still needs a native platform test. |
| [README template](docs/README_TEMPLATE.md) | Reusable seven-language project presentation contract. |
| [Design research](docs/readme-design-research.md) | Ten primary-source README references and the adopted design decisions. |

The detailed technical handbook is currently maintained in English; each of the seven READMEs provides the same localized onboarding and operational overview.

**Contribute / get help:** [open an issue](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues) with the OS, Python version, UpdateWulf commit, exact command and sanitized output. Never attach tokens, private keys or live configuration files. See [contributor checks](docs/manual.md#contributing).

**License:** the repository currently contains no license file. This documentation does not select or grant a license; ask the maintainer about permitted reuse.

---

<div align="center">

[Back to top](#updatewulf) · [Download source](https://github.com/n-e-o-w-u-l-f/UpdateWulf/archive/refs/heads/main.zip) · [Read the manual](docs/manual.md)

</div>
