# Troubleshooting and known issues

[Overview](../Readme.md) · [Installation](installation.md) · [Manual](manual.md) · [Configuration](configuration.md)

Start with the observed command, the actual execution account and the selected state directory. UpdateWulf distinguishes cached information, connection problems and completed jobs; an empty cache or unsuccessful scan is not evidence of zero pending updates.

## First checks

From a new terminal in the intended operator account:

```sh
updatewulf --version
updatewulf status --json
updatewulf diagnose
```

These commands do not install packages. `status` reads the local cache; `diagnose` makes authenticated `GET /fleet` requests to the configured hubs. Inspect `generated_at`, member `received_at` and update `checked_at` in the snapshot, together with their status fields. Inspect the installed service/task and a fresh `heartbeat.json` in its actual state directory. The wrapper and the background worker can point to different program versions after an incomplete handover.

If the command is unavailable, run the source entry point with its real interpreter, for example `python3 pc_mesh.py --help`, from the source directory. On Windows, use your verified `python.exe` or `py -3`. Do not reinstall repeatedly until the first failure and any existing worker are understood.

## Symptoms and next steps

| Symptom | What to check | Practical next step |
| :--- | :--- | :--- |
| `updatewulf` is not found | User bin directory and whether the shell was opened after installation. | Unix: try `"$HOME/.local/bin/updatewulf" --version`. Windows: check `%USERPROFILE%\.local\bin\updatewulf.cmd`. Use a fresh shell or the exact wrapper; do not replace an unrelated command. |
| Wrapper exists but cannot find Python or `pc_mesh.py` | Recorded interpreter and permanent source path. | Restore the verified path or reinstall from the retained source using the same account/configuration/state. Do not delete a source directory still referenced by a service. |
| Windows rejects Python | `Get-Command python.exe` resolves to a Store/WindowsApps alias or an absent runtime. | Pass the actual Python 3.9+ executable with `-Python`; validate its version first. |
| Configuration is missing or JSON is invalid | Correct account, absolute file path, JSON syntax and UTF-8 content. | Correct the file outside the source tree. A syntactically valid JSON object still needs real certificates, tokens and hub enrollment. |
| `LAN control configuration is required` | Whether `control.json` or the selected `--config` exists for this operator. | Complete [operator setup](configuration.md#first-setup); do not borrow another account's token. |
| `status` is empty | Local `fleet.json`, worker startup and hub connectivity. | Check the actual state path and `diagnose`. An empty cache does not mean the fleet is up to date. |
| `status` stays old although the service is running | Cache directory selected by the wrapper versus the service's `--state`. | Read the correct cache. After Windows machine migration, use the documented `-PromptOnly -State` step to point the shell at `announce-state`. |
| `Hub [stale]` or old counts remain visible | Last successful fleet fetch versus worker heartbeat. | Inspect `heartbeat.txt`, `fleet.json` and hub errors. A live worker can still have stale hub data. |
| A device is offline | Member's last report and that device's actual worker/network. | Restore that member's service or connection. Cached counts remain historical until a new report. |
| `unknown hostname` or an ambiguous hostname | Enrolled member IDs, reported hostnames and aliases. | Use the exact member ID from the fleet. Display names are not identities. Resolve duplicate aliases in enrollment rather than guessing. |
| `hub unreachable` | HTTPS URL, port, network path, certificate trust and optional SSH tunnel. | Follow the [connection checks](#connection-and-enrollment). Verify access from the actual service account. |
| HTTP 401 | Network allowlist, supplied token and endpoint. | Verify the configured client address is permitted and the token matches its intended role. An application rejection is not a transport outage. |
| HTTP 403 on control | Operator versus member token and target `allow_install`. | Member tokens control their own device; another device needs operator authority. Installation additionally requires the member's explicit install permission. |
| HTTP error says a host already has an active request | Current job and native updater state. | Inspect the existing job instead of submitting another update. Resolve its underlying condition first. |
| A request remains `QUEUED` and then expires | Target online status, valid member credentials and whether its request worker is enabled. | With `announce_only: true`, set `machine_control: true` when control is intended. Restart through the native owner workflow after changing configuration. |
| `NEEDS_ADMIN` | The native helper, its owner, configured `native_installer` route and member permission. | Follow the platform's [systemwide installation](installation.md). The program does not elevate itself. |
| Update command returns after waiting 600 seconds | The job may still be running. | Check hub/native status and logs. Do not retry blindly or terminate the package manager. |
| Job is `INTERRUPTED` after a restart | `executed-commands.json`, `installer.json` or the native helper's `status.json`, plus package-manager history. | Determine whether native work finished before deciding on a new request. Interrupted requests are deliberately not replayed automatically. |
| `UNSUPPORTED` | Selected operating system/package manager. | Check the [implemented adapters](../Readme.md#requirements). There is no automatic fallback to winget, Flatpak, Snap or Homebrew. |
| Another process holds the daemon lock | Actual live worker and its state directory. | Keep the intended worker; disable the duplicate startup route. A leftover lock filename alone is not evidence of a live lock. |

## Connection and enrollment

`diagnose` tests every configured hub and exits successfully when at least one responds with a valid fleet. It does not prove that all hubs or all members are healthy. For operator actions, the default-path `control.json` takes precedence over the default `config.json`; an explicit non-default `--config` selects another file. Check which file is in use without pasting its secret contents into a report.

For TLS errors, verify the HTTPS URL, the certificate's subject alternative names, its validity period and the public trust certificate selected by `certificate`. JSON paths are literal: a path containing `~` can fail even when that file would exist after shell expansion. Keep certificate verification enabled; changing to HTTP or accepting an unrelated certificate does not repair enrollment.

The shipped hub example binds to loopback and allows loopback only. For a LAN installation, configure the actual listening interface and the required client CIDRs, and allow the chosen port in the host's existing firewall policy. Do not assume that an example allowing local access is reachable from another computer.

For token errors, check the intended role:

- The worker's top-level `token` must match its own `hub.members[].token`.
- A read-only token is for reads, not reports or control requests.
- The operator token enables cross-device control, but does not override target `allow_install` or OS-level privileges.

A changed hub member list/token is read at process startup. Apply the configuration change with a controlled restart, after checking for active work. Do not rotate or remove credentials just to make a transient connection failure disappear.

If using `ssh_tunnel`, verify the selected SSH executable, the account's own private key and its `known_hosts` file. The tunnel uses strict host-key checking and forwards to the hub's fixed target port 9797. Windows SYSTEM uses a separately enrolled machine key, so success in an interactive user session does not by itself prove pre-login connectivity. The HTTPS certificate must still validate the name used in the tunnel URL.

## Scan and package-update differences

**APT:** scanning refreshes metadata in the worker's own cache and simulates `dist-upgrade`; package installation uses `upgrade --with-new-pkgs` with the fixed configuration-file policy in [apply_updates.py](../apply_updates.py). The two operations can legitimately leave different sets of packages outstanding. A successful job does not guarantee a zero count. Inspect the actual APT output and the new scan rather than forcing a zero.

**Arch Linux:** the collector needs `pacman-conf`, `vercmp` and at least one working configured HTTPS mirror for each enabled repository. It reads installed versions and remote metadata; it does not include a separate AUR updater. A broken or HTTP-only mirror configuration can prevent a fresh scan. Fix the native repository configuration through the normal administrator workflow.

**NetBSD:** an unprivileged scan uses existing pkgin metadata and can report `CACHED`. A root scan refreshes metadata. Unrecognized pkgin output produces an unknown/error result rather than a guessed count. The root rc.d worker uses the direct installer route; setting `native_installer: true` incorrectly selects the Linux systemd helper on Unix and is not the NetBSD setup recipe.

**Windows:** the adapter uses Windows Update Agent for software updates. Updates requiring user interaction or exclusive installation are skipped by the fixed updater and reported for follow-up; a partial result can be `FAILED` even when some updates installed. Review Windows Update history and complete the remaining steps through Windows. The code reports a reboot requirement but never reboots the computer automatically. winget applications are outside this adapter's scope.

**Termux:** native APT manages packages belonging to the Android app account. This does not upgrade Android itself. Background process restrictions and Termux:Boot setup affect availability independently of the package adapter.

## Logs and evidence

| Installation / artifact | Where to look |
| :--- | :--- |
| Normal worker log | Selected state directory: `service.log`, with up to three rotated backups. |
| Worker process/age | `heartbeat.json`; verify its PID against the actual running command. |
| Successful hub-fetch age | `heartbeat.txt` and `fleet.json`. |
| Direct updater | State directory: `installer.json`, `update-install.log`. |
| Linux privileged helper | `/var/lib/pc-mesh-installer/status.json`, `installation.log`. |
| Windows privileged helper | `%ProgramData%\PC-Mesh-Installer\status.json`, `installation.log`. |
| Windows SYSTEM worker | `%ProgramData%\PC-Mesh-Installer\announce-state\`. |
| Hub jobs / member execution history | Hub `commands.json`; member `executed-commands.json`. |
| Startup definitions | Actual systemd user/system unit, Windows task actions/principal, NetBSD rc files or managed cron/Termux boot hook. |

Job records and snapshots can contain hostnames, package lists and other operational details. Review and redact logs before sharing them. Never attach complete live configuration, bearer tokens, private keys or authentication helper output.

## Application update recovery

For a supported user installation, `updatewulf --self update --check` queries the public branch without activating it. `SELF_UPDATE_BLOCKED` is a refusal with an explanation, not a successful update. Check Git availability, network access to the fixed repository, installed provenance markers and the reported condition.

| Refusal / condition | Response |
| :--- | :--- |
| GitHub ref changed while staging | The source moved between checks. Inspect the current ref, then perform a fresh attempt after that change is understood. |
| Installed release is not an ancestor / branch diverged | Retain the current release and investigate provenance. Do not add `--bootstrap` merely to suppress the check. |
| First migration needs bootstrap | For an intended initial public user migration, use the explicit `--self update` path described in the [manual](manual.md#application-self-update). |
| Root or machine service requires native handover | Use the matching machine installer/runbook. Do not create a parallel user worker to bypass the refusal. |
| `.apply.lock` exists | Identify any live self-update process and staging work. Only a confirmed stale, empty application lock directory may be removed; do not remove release data or live worker locks. |
| Staged check failed | Keep the existing source. Read the failing test/validation evidence before changing the release. |
| Windows activation and rollback both failed | Retain the previous source and task backups; repair the native task/runtime via the [rollback procedure](installation.md#rollback). |
| Old releases remain after success | Conservative pruning can preserve unknown files/directories. Retention beyond two releases is expected for the new documentation tree; do not delete unfamiliar files to satisfy the cleanup gate. |

Custom configuration/state layouts and Termux currently require manual native application handovers. Keep `auto_self_update: false` for those deployments. For Termux, the generic updater invokes `install.py` instead of `install_termux.py`, so it does not refresh the boot hook and can fail without systemd/cron. The [Termux instructions](installation.md#termux-user-installation) describe the appropriate route.

## Known issues

This table separates behavior established by source inspection from platform acceptance that has not been performed. It does not claim that every listed condition has been reproduced on physical hardware. Source references point to the code in this repository; consult the [verification record](documentation-status.md) for executed checks.

| Issue / limitation | Evidence and consequence | Workaround / current handling |
| :--- | :--- | :--- |
| Custom configuration and Unix state paths are not preserved by generic self-update activation | Confirmed in [self_update.py](../self_update.py), `install()`: Unix calls `install.py` without forwarding the supplied state, and activation does not pass a custom config path. | Use default paths for ordinary user installations, or disable automatic application updates and use a manual native handover. |
| Generic Termux self-update uses the wrong installer | Confirmed in [self_update.py](../self_update.py), `install()`: the non-Windows branch calls the Unix installer rather than [install_termux.py](../install_termux.py). Boot-hook refresh is absent and systemd/cron may be unavailable. | Keep `auto_self_update: false`; stop cooperatively and invoke the new Termux installer with the existing config/state. |
| Empty-fleet TUI navigation can fail | Source-demonstrated path in [tui.py](../tui.py), `menu()`: arrow navigation calculates a remainder with `len(nodes)`, which can be zero. Not reproduced in a native interactive session during this documentation work. | Use `status` and `diagnose` until a member is enrolled; avoid opening/navigating an empty TUI. |
| Bash prompt does not fully honor `NO_COLOR` | Confirmed in [hooks/updatewulf.bash.in](../hooks/updatewulf.bash.in): it selects the colored Bash cache without a `NO_COLOR` check. | Use `updatewulf status --no-color` for guaranteed plain CLI output; CLI behavior does not fix the separate prompt hook. |
| Windows configuration preflight occurs after profile changes | Confirmed in [install_windows.ps1](../install_windows.ps1): profiles/wrappers are written before the service path checks that configuration exists. | Prepare and validate enrollment first. If setup fails, inspect the managed profile blocks/backups and task state before retrying. |
| Linux machine migration does not retire systemd user persistence | Confirmed in [enable_machine_updates.py](../enable_machine_updates.py): managed cron is handled, but existing `updatewulf.service` in the user manager is not disabled. | Follow the [explicit user-service shutdown step](installation.md#linux-systemwide) before machine activation. |
| Windows machine migration changes the worker cache location | Confirmed in [enable_machine_updates_windows.ps1](../enable_machine_updates_windows.ps1): machine state is `announce-state`; old user wrappers can still read their prior cache. | Repoint operator shell integration with `-PromptOnly -State` as documented; do not start another user worker. |
| Extra documentation prevents some old-release pruning | Confirmed in [self_update.py](../self_update.py): the conservative root-entry allowlist does not cover all new `Readme.*.md` files and documentation directories. | Preserve them; manually review retention when needed. Activation can succeed even when more releases are retained. |
| No full automatic uninstaller | [scripts/uninstall.sh](../scripts/uninstall.sh) intentionally makes no removal changes. | Follow the [controlled manual removal procedure](installation.md#uninstall), preserving configuration/state and unknown files. |
| Shell support is not equivalent across shells | [install.py](../install.py) supplies a cached Bash header and mostly passive other-shell hooks; sh/ksh hooks encounter a Bash guard. | Use the CLI for consistent status access. Do not assume live prompt parity across shells. |
| Program interface is not fully localized | German text remains in [pc_mesh.py](../pc_mesh.py) and [tui.py](../tui.py). | The seven READMEs provide translated guidance; runtime language selection is not claimed. |
| Additional package managers are not implemented | [pc_mesh.py](../pc_mesh.py) and [apply_updates.py](../apply_updates.py) select the implemented native adapters only. | Use native tooling separately for unsupported package sources. |
| Native platform/service/reboot acceptance remains incomplete | This documentation session does not constitute a live Windows, NetBSD, Termux or fleet deployment test. Portable tests do not establish those results. | Validate on the actual target and retain rollback before deployment; see the [verification record](documentation-status.md). |
| No tagged downloadable installer assets at the documentation baseline | Published-release inspection found no packaged tagged assets; the download points to source. | Record the source commit used. Do not describe a branch ZIP as a signed native installer. |
| No license file in the repository | Repository inspection; no licensing choice is made by this documentation. | Ask the maintainer about permitted reuse. |

The old `scripts/install.sh`/`scripts/uninstall.sh` GitSync mismatch has been addressed in the current source: installation now delegates to the real Unix user installer, while removal is non-destructive guidance. The Unix installer also checks required source/configuration before changing profiles. If an older checkout mentions `github-sync` or a fixed personal account, inspect its commit and update the intended source instead of supplying missing GitSync files.

## FAQ

### Does installing UpdateWulf immediately update the operating system?

The native installers start the status worker and configure persistence; they do not submit a package-update job. The worker scans and reports status. An explicit `update HOST` request invokes the target's fixed native updater only after the enrollment, member permission and OS privilege gates are satisfied. Application self-update is separate and defaults to enabled in the code where supported; the example configurations disable it for first setup.

### Is `updatewulf status` a fresh check?

No. It displays the selected local `fleet.json`. Use `diagnose` to inspect connectivity and an authorized `refresh HOST --wait 60` to request a new scan. The target must have its request worker enabled and be reachable.

### Can I use `.local` without mDNS or SSH access to that host?

The CLI resolves a hostname or `.local` alias against the authenticated fleet's reported/enrolled identities. It does not convert arbitrary host text into a remote shell command. Hub connectivity and enrollment are required; the exact member ID is the clearest alternative when aliases are ambiguous.

### Why does a successful update leave pending packages?

Successful native execution is not the same as installing every possible update. APT scan/install plans differ, Windows can require interactive follow-up, and third-party package sources may be outside the adapter's scope. Inspect the new scan and native output. UpdateWulf does not replace a remaining count with zero merely because the command exited successfully.

### Can I update every registered device at once?

`updatewulf all update` submits requests for all enrolled targets. Use it only when that is the intended scope and all targets have appropriate permissions. One active request per target is enforced. This is not a rollback transaction across computers, and a CLI timeout does not cancel submitted native work.

### Do I need administrator access for every operation?

No. Cached display, connection diagnosis and the applicable unprivileged scans do not need a privileged package installer. Native system package installation needs root/Administrator rights or the deliberately provisioned fixed helper. Termux packages belong to the Android app account. Operator tokens do not grant OS elevation.

### Can I remove the source directory after installation?

Not while a wrapper, service or task still references it. Unix user installation points directly to the selected source. Self-update creates separate commit-named program releases; machine installation has its own protected layout. Check installed definitions before removing any source, and retain the previous working version until the handover is verified.

### Why are there `pc-mesh` paths and commands?

Those names are retained for compatibility with existing installations and persistent state. `updatewulf` and `UpdateWulf` are the main user-facing command names. Do not rename live configuration/state directories without updating every dependent service, task, wrapper and hook.

### Is Git synchronization part of normal UpdateWulf setup?

Legacy compatibility code remains, but the supplied first-setup examples use no repositories and separate update announcements from Git work. New Git synchronization belongs in GitSyncWulf. Updating UpdateWulf itself fetches only its fixed public application repository.

### Are all seven manuals available in the program's language?

The seven READMEs contain equivalent localized introductions and operational overviews. The detailed technical handbook is currently English, and some program messages are still German. Neither native-language review nor complete runtime translation is implied by the README translations.

## Reporting a reproducible issue

Open an [issue](https://github.com/n-e-o-w-u-l-f/UpdateWulf/issues) with the OS/version, Python version, UpdateWulf source commit, installation scope, exact command, expected outcome, observed result and relevant sanitized log excerpt. State whether the result comes from a real native run, an automated test or source inspection. Include the selected state path in redacted form if a cache mismatch is involved.

Do not attach live credentials or complete private configuration. Keep a failed installation's source and backups available locally until the cause is understood. For an unfinished package update, report the native updater's actual state before attempting another request.
