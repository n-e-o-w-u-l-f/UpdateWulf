# UpdateWulf manual

[Overview](../Readme.md) · [Installation](installation.md) · [Configuration](configuration.md) · [Troubleshooting](troubleshooting.md)

This manual describes the public 2.1.0 implementation. The repository commit identifies the exact source revision; the version string alone does not identify every documentation or maintenance change.

## How it works

An enrolled worker scans its native package manager, sends a report to an HTTPS hub and saves a local copy of the fleet. The hub keeps device identity, scan freshness and a durable request queue. An operator asks the hub to refresh a device or install its available native updates. The device claims its own request and runs the existing OS-authorized helper.

Shell status reads cached files. It does not scan packages or contact the network at every prompt. A short `.local` name in a command is resolved against enrolled/reported hostnames in the authenticated fleet; it is not an instruction to run arbitrary commands on a DNS host.

The hub and worker can run in the same process: a configuration containing `hub` starts the HTTPS server as well as that computer's worker. Each computer needs its own identity/token, configuration and state directory. Read-only, member and operator tokens serve different purposes; see [configuration](configuration.md).

## Command syntax

After installation:

```sh
updatewulf [ACTION] [TARGET] [OPTIONS]
updatewulf TARGET ACTION [OPTIONS]
```

From the source checkout, replace `updatewulf` with `python3 pc_mesh.py` (Windows: your actual Python executable or `py -3`). Calling `updatewulf` without arguments selects `status`.

### Every action

| Action | Purpose | Network / changes |
| :--- | :--- | :--- |
| `status [TARGET]` | Display the cached fleet or one matching device. | Reads local `fleet.json`; no scan or network call. |
| `line` | Print the compact cached status line. | Local read. |
| `prompt` | Print cached announcements/status and `PC_MESH_SEQ=N`. | Local read; accepts `--since`. |
| `watch` | Observe cached output once per second. Stop with Ctrl+C. | Local reads; does not make the worker run. |
| `diagnose` | Check each configured HTTPS hub with `GET /fleet`. | Read-only authenticated network calls. |
| `refresh [TARGET]` | Request a new native package scan. | Queues work; the worker updates metadata/cache and reports results. |
| `update [TARGET]` | Request native package installation. | Queues a state-changing update; requires `allow_install` and OS privilege. |
| `tui` | Open the interactive device/action menu. | Fetches fleet; selected operations may enqueue updates. |
| `once` | Run one local scan, report it, fetch and save the fleet. | Network and state writes; requires worker configuration. |
| `daemon` | Run scans, reporting, cache monitoring and configured control workers. | Persistent process; normally managed by the installer. |
| `--self update` | Update the local UpdateWulf application. | Downloads/stages source; may activate a new user release. |
| `self-update` | Alternate application-updater action. | See bootstrap distinction below. |
| `sync TARGET` | Request legacy configured Git synchronization on a target. | Can fast-forward a configured repository; legacy compatibility only. |
| `sync` without a target | Run local configured repository synchronization. | May change configured worktrees; not needed for package status. |

`TARGET` is an exact member ID, enrolled/reported hostname or `all`. Host aliases are case-insensitive and can use the `.local` suffix. Friendly display names are not a substitute for an enrolled hostname. Unknown or ambiguous targets are rejected. If an operator action omits its target, the configuration's `id` supplies the default.

### Every option

| Option | Default | Meaning |
| :--- | :--- | :--- |
| `-h`, `--help` | — | Show parser help and exit. |
| `--version` | — | Print the application version and exit. |
| `--config PATH` | `~/.config/pc-mesh/config.json` | Configuration file; operator precedence is explained below. |
| `--state PATH` | `~/.local/state/pc-mesh` | Local state/cache directory. |
| `--since N` | `0` | Announcement/event cursor for prompt/watch output. |
| `--json` | off | Raw JSON for `status`; does not turn every command into a JSON API. |
| `--color auto\|always\|never` | `auto` | CLI status colors. `auto` requires a TTY, no `NO_COLOR` and `TERM` other than `dumb`. |
| `--no-color` | off | Set CLI color mode to `never`. |
| `--wait N` | `600` for `update`; `0` for other operator actions | Wait for queued job completion. Clamped to 0–600 seconds. |
| `--self` | off | Together with `update`, operate on the local application; a target is invalid. |
| `--check` | off | Read the application branch without activation. Use with a self-update action. |
| `--bootstrap` | off | Explicit initial migration that skips the installed-release ancestry comparison. |
| `--branch NAME` | `main` | Public application branch for self-update. Not a package-manager channel. |

Options are action-specific. `--json` only affects `status`; self-update's check command already emits JSON. Do not assume unused flags change another action's behavior. The CLI currently has no `--language`, `--dry-run`, `--install`, `--uninstall` or general rollback option.

### Configuration selection

For `diagnose`, `refresh`, `update`, `tui` and remote `sync`, the CLI uses `~/.config/pc-mesh/control.json` when that file exists and the parser is using its default configuration path. An explicitly supplied **different** `--config` path selects that file. Supplying the same default path still permits `control.json` precedence.

`daemon`, `once` and local `sync` use `--config` directly. Cache-only commands do not require a configuration file. Generated Unix wrappers pin `--state` but do not pin a custom `--config`; use the default paths for the standard installation recipe.

## Practical workflows

### Check before asking for an update

```sh
updatewulf --version
updatewulf diagnose
updatewulf workstation.local refresh --wait 60
updatewulf workstation.local status
```

`refresh` completion and the local status cache are separate observations: the background worker still needs to receive and save the latest fleet snapshot. Inspect timestamps with `status --json` if the displayed count has not changed yet.

### Install native package updates

```sh
updatewulf workstation.local update --wait 600
```

This is an explicit request to run the target's native updater with its implemented noninteractive options. It may download/install many packages; Windows Update can accept the selected updates' EULAs in its adapter. The native account/service must already be authorized, and the member must have `allow_install: true`. UpdateWulf does not prompt for administrator credentials or elevate the process itself.

| Native target | Implemented installer behavior |
| :--- | :--- |
| APT | Refresh lists, then `upgrade` with `--with-new-pkgs`, `--force-confdef` and `--force-confold`. |
| pacman | `pacman -Syu --noconfirm`. AUR helpers are not invoked. |
| NetBSD | `pkgin -y update`, then `pkgin -y upgrade`. |
| Windows | Windows Update Agent download/install adapter; input-requiring or exclusive updates need separate attention. |
| Termux | The app account may update its APT-managed packages; this does not update Android itself. |

An APT scan simulates `dist-upgrade`, whereas installation uses `upgrade --with-new-pkgs`. A successful job can therefore leave pending updates. Re-scan and inspect the native manager; a completed command never implies a zero count or a completed OS release upgrade.

### Work asynchronously

```sh
updatewulf workstation.local update --wait 0
updatewulf status --json
```

The first command prints a job identifier and queued status. Use the `commands` array in subsequent fleet snapshots to inspect completion. A wait timeout leaves a running package manager alone. Do not immediately enqueue duplicates because the CLI stopped waiting.

### Operate on the whole enrolled fleet

```sh
updatewulf all refresh --wait 60
updatewulf all update --wait 600
```

Each line is independent. The second requests actual installation on all resolved targets. The hub validates the batch before queueing it. One active request per device is allowed; a queue conflict must be inspected rather than treated as a reason to run a second updater manually.

### Plain output and automation

```sh
updatewulf status --no-color
updatewulf status --json > updatewulf-status.json
```

JSON is a local snapshot containing timestamps and possibly hostnames, package lists and job details. Check `generated_at`, `received_at`, `checked_at` and status fields. Treat exported fleet metadata as operational data when sharing a report. CLI `--color always` explicitly overrides automatic `NO_COLOR` behavior; the Bash prompt has a separate limitation in [known issues](troubleshooting.md#known-issues).

## Status, freshness and jobs

### Scan states

| State | Interpretation |
| :--- | :--- |
| `OK` | Collector completed using its fresh metadata path. |
| `CACHED` | A retained successful result or existing metadata is being used. Inspect error/freshness fields. |
| `CHECKING` | A scan result is not yet available. |
| `UNKNOWN` | No usable result has been reported. |
| `ERROR` | Scan failed without a usable successful result. |
| `UNSUPPORTED` | No supported collector is available. Count is unknown, not zero. |

The hub's default offline threshold is 150 seconds without a report; the stale scan threshold is 5,400 seconds. A stale hub snapshot and an offline individual computer are different conditions. The renderer keeps this distinction and can display a previous count with a stale/offline marker. The compact prompt hides up-to-date devices behind a `+N` summary and truncates to terminal width.

### Job states

| State | What to do |
| :--- | :--- |
| `QUEUED` | Wait for the target worker to claim it. Unstarted requests expire after 600 seconds. |
| `RUNNING` | Inspect progress/logs; do not start a parallel package manager. |
| `SUCCEEDED` | Read the result and re-scan; remaining packages are possible. |
| `FAILED` | Inspect `detail` and the native updater log. |
| `NEEDS_ADMIN` | Provision/repair the authorized native helper; no automatic elevation occurred. |
| `EXPIRED` | The worker did not claim the request in time. Verify reachability before a new request. |
| `INTERRUPTED` | The worker restarted with unfinished work recorded. Inspect native state before deciding what to run. |

Request IDs are retained to avoid replaying a claimed operation. Restarted work is not automatically retried as a new package installation. The hub retains active requests and a bounded recent terminal history.

### Exit codes

| Command/context | Code | Meaning |
| :--- | :--- | :--- |
| Waiting operator command | `0` | All observed jobs succeeded. |
| Waiting operator command | `1` | At least one terminal result was not successful. |
| Waiting operator command | `2` | Wait timed out; running work is not cancelled. |
| Asynchronous operator command | `0` | Request accepted/queued, not proof of completion. |
| `diagnose` | `0` / `2` | At least one hub answered / none answered. |
| Parser or explicit configuration validation | `2` | Correct the arguments/configuration. |
| Handled runtime failure or Ctrl+C | `1` | Command stopped without a successful result. |
| Self-update refusal | `2` | `SELF_UPDATE_BLOCKED`; existing source retained. |
| Direct `apply_updates.py` without native privilege | `3` | `NEEDS_ADMIN`. |
| `scripts/uninstall.sh` | `0` for help; `2` otherwise | No automatic removal performed. |

Some unexpected Python/OS failures can still emit a traceback. A zero exit from cache display only proves the local display command completed.

## Application self-update

```sh
updatewulf --self update --check
updatewulf --self update
```

The application repository is fixed in [self_update.py](../self_update.py): `https://github.com/n-e-o-w-u-l-f/UpdateWulf.git`. The default branch is `main`. This updater does not synchronize arbitrary project repositories or request OS package installation.

The implementation resolves the branch commit, clones into an isolated staging directory, checks the remote identity, runs `git fsck`, verifies the installed commit is an ancestor when required and rechecks that the remote did not move. It then removes `.git`, writes `DEPLOYED_COMMIT` and `SELF_UPDATE_ORIGIN.json`, checks required files, compiles the Python entry points and runs the named announcement/self-update/hostname tests. It parses selected PowerShell files on Windows and checks shell syntax when Bash is available on Unix. This is Git integrity and ancestry checking; there is no configured signed-release verification scheme.

Validated releases live at `~/.local/share/updatewulf/releases/<commit>/`. Activation rewrites the user wrappers and native user persistence through the installer, then checks the wrapper's source path and version. The previous release is retained. On Windows the installer path attempts to re-invoke the previous installer when activation fails; Unix does not implement an equivalent automatic rollback. Use the [manual rollback procedure](installation.md#rollback) when required.

### Initial migration and automatic checks

A fresh source checkout has no installed public provenance marker. The explicit `--self update` command adds the initial bootstrap flag when the local source lacks a matching public origin/commit marker. Subsequent public upgrades enforce ancestry. The alternate `self-update` action requires you to supply `--bootstrap` explicitly for an initial migration. Do not use bootstrap to dismiss an unexplained downgrade/divergence.

Worker configuration defaults `auto_self_update` to `true`. The first automatic attempt waits 300 seconds; subsequent attempts default to 21,600 seconds, clamped to one–24 hours. Unix enables the background updater only for a non-root worker without `machine_control`; Windows uses its own activation path. An automatic invocation does not perform the first bootstrap migration. The shipped example configurations turn automatic self-update off during initial setup.

### Boundaries and recovery

- Root Unix activation and an active Linux `pc-mesh-announce.service` require a native machine handover. Do not run a second user worker to circumvent this refusal.
- Custom configuration paths and custom Unix state paths are not consistently propagated into activation. Use a reviewed native handover for those installations.
- Termux has no complete self-update activation path: the generic Unix installer does not rewrite its Termux boot hook. Keep `auto_self_update: false` and follow the manual native Termux upgrade steps in the installation guide.
- An `.apply.lock` directory serializes application updates. After interruption, inspect running processes and the staged release before removing only a confirmed stale lock.
- Old release pruning is conservative: current/previous releases, unknown names/content, symlinks and invalid provenance are preserved. The current allowed-name list does not include the new documentation tree, so retention can exceed two releases. Do not remove unfamiliar data to make pruning succeed.
- Self-update tests are a staged-source check, not evidence that every native platform or hardware machine has passed end-to-end acceptance.

## Files, logs and shell integration

The historical `pc-mesh` directory name is retained for compatibility.

| Location under the default state directory | Meaning |
| :--- | :--- |
| `fleet.json` | Last retrieved hub snapshot. |
| `local.json` | This worker's scan/report data. |
| `heartbeat.json` | Worker PID, timestamp and program version. |
| `heartbeat.txt` | Successful fleet-fetch freshness for prompt consumers. |
| `service.log` | Rotating log: 1,000,000 bytes per file and three backups. |
| `launcher.log` | Unix fallback launcher output. |
| `executed-commands.json` | Local claim/completion record. |
| `commands.json`, `hub.json` | Hub queue and fleet/event state. |
| `installer.json`, `update-install.log` | Direct native package updater state/output. |
| `daemon.lock` | OS-level worker lock; a leftover filename alone is not a live lock. |
| `stop.request` | Cooperative stop signal, processed by the worker. |
| `fleet-prompt.*` | Rendered status caches for shell integrations. |

Linux machine installer logs instead use `/var/lib/pc-mesh-installer/`; Windows machine files use `%ProgramData%\PC-Mesh-Installer\`. The installation guide lists the services/tasks that own them.

Bash receives a moving pre-prompt header and preserves the existing PS1 through managed hooks. Zsh, Fish and Tcsh currently use passive startup output; the Bash-guarded hooks loaded by other shell profiles do not provide the same dynamic behavior. PowerShell integration is generated for Windows PowerShell/PowerShell profiles. Source/profile edits have separate ownership from package updates.

## Contributing

Report a reproducible issue with OS/runtime versions, the exact source commit, command, expected behavior and sanitized result. Include timestamps for stale status problems. Never post tokens, private keys or unredacted client/control configurations.

From a local checkout, without starting services:

```sh
python3 -m py_compile pc_mesh.py update_control.py self_update.py tui.py owner_profiles.py install.py
python3 test_update_announce.py
python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
bash -n scripts/install.sh scripts/uninstall.sh
```

PowerShell parsing and native install/service/prompt checks must run on an appropriate Windows environment; Linux portable tests are not a substitute. See [verification](documentation-status.md). No license file currently exists; this guide does not choose a license on the maintainer's behalf.

## Implementation references

The behavior above is grounded in [pc_mesh.py](../pc_mesh.py) (`main`, `daemon`, `Client`, `Hub`, collectors and renderers), [update_control.py](../update_control.py) (`ControlQueue`, `worker`, `run_install`), [apply_updates.py](../apply_updates.py), [apply_windows.ps1](../apply_windows.ps1) and [self_update.py](../self_update.py). Installer-specific behavior is linked from [installation](installation.md).
