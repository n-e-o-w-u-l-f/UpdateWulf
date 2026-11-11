# Configuration reference

[Overview](../Readme.md) · [Installation](installation.md) · [Manual](manual.md) · [Troubleshooting](troubleshooting.md)

UpdateWulf uses JSON files outside its program directory. It does not create a working hub enrollment automatically. The provided [client](../examples/config.client.json), [hub](../examples/config.hub.json) and [operator](../examples/control.json) examples contain clearly marked placeholders and disabled package-install permission. Replace them with your own local settings before starting a service.

## First setup

### 1. Choose the hub and identities

Choose a machine that can remain reachable, an HTTPS name and a listening port (default 9797). Decide a stable member ID and display name for each computer. IDs use the application's conservative identifier format: a letter/digit followed by up to 63 letters, digits, dots, underscores or hyphens. Use different tokens for every member, for read-only access and for operator control.

The [hub example](../examples/config.hub.json) initially binds only to `127.0.0.1` and allows only loopback. That provides a local setup example, not a ready-to-use LAN endpoint. For a LAN deployment, set `hub.bind` to an intended interface address, explicitly list the required client CIDRs in `hub.allowed_networks`, and allow that port in your existing host firewall. Do not expose it as an unauthenticated public service.

### 2. Prepare TLS

The hub needs a PEM certificate and its private key. Every client needs a trusted certificate/CA file that validates the hub, and the URL hostname/IP must match the certificate's subject alternative names. The client verifies TLS and enforces TLS 1.2 or newer.

Use your existing internal certificate authority where available. For a **local demonstration on a Unix host**, OpenSSL 3 can create a self-signed certificate as follows. Run this in a new private configuration directory, not the source checkout; do not overwrite an existing certificate/key:

```sh
umask 077
mkdir -p "$HOME/.config/pc-mesh"
cd "$HOME/.config/pc-mesh"
test ! -e hub.key && test ! -e hub.crt && \
openssl req -x509 -newkey rsa:3072 -sha256 -days 365 -noenc \
  -keyout hub.key -out hub.crt -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

This certificate covers only the local demonstration. For LAN use, issue a certificate with the actual hub DNS name/IP. Copy only the public trust certificate to clients and verify its fingerprint through your trusted administration channel. The private key remains on the hub; it is unencrypted in this example because the daemon has no passphrase prompt, so protect its directory and permissions. See the primary [OpenSSL req reference](https://docs.openssl.org/3.2/man1/openssl-req/) for these options.

### 3. Generate distinct tokens

For each required token, run locally:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Store each generated value only in its intended private configuration. A member's client token must match that member's `hub.members[].token`; the hub worker's top-level token must match its own member entry. The operator configuration uses `hub.operator_token`. Do not commit completed configuration files or use the literal placeholder strings as tokens.

### 4. Write the hub configuration

Copy [config.hub.json](../examples/config.hub.json) to the hub owner's `~/.config/pc-mesh/config.json` only if there is no existing file. Edit every `REPLACE_WITH_…` value and both certificate paths. JSON strings containing Windows backslashes must escape them (`C:\\Users\\operator\\…`); forward slashes are often simpler. Use absolute paths, not literal `~` or `$HOME` inside JSON.

For the local example, leave the URL `https://localhost:9797`, `bind: 127.0.0.1`, and loopback-only allowlist. The hub configuration contains both a top-level worker identity and the nested server block. Set each member's `allow_install` to `false` while testing connection and status.

Validate JSON without starting the daemon:

```sh
python3 -m json.tool "$HOME/.config/pc-mesh/config.json" > /dev/null
chmod 600 "$HOME/.config/pc-mesh/config.json" "$HOME/.config/pc-mesh/hub.key"
```

The JSON parser checks syntax, not the full operational meaning of every field. Keep the certificate path readable by the execution account. On Windows apply the corresponding user-only ACL instead of running `chmod`.

### 5. Start and verify the hub

From the source directory, run `python3 pc_mesh.py daemon` in a foreground terminal to inspect the first setup. This starts the configured worker and scans; it is not a cache-only command. In a second terminal, run `python3 pc_mesh.py diagnose` and then `python3 pc_mesh.py status`. Inspect `service.log` if the hub or scan fails. Stop the foreground daemon with Ctrl+C before installing a persistent worker with the [installation guide](installation.md).

For a remote client, first configure the actual hub interface/CIDR/certificate and verify that the endpoint is reachable from that client. Then adapt [config.client.json](../examples/config.client.json) to the member ID, member token, HTTPS hub URL and local trust-certificate path. Start its worker and confirm a new report in the hub snapshot. Updating the hub's member list requires a controlled hub restart; it is read at process startup.

### 6. Add operator access when needed

Write [control.json](../examples/control.json) in the operator's `~/.config/pc-mesh/` directory, with the operator token and trusted endpoint. This lets the operator request work for enrolled targets; it does not grant root or Administrator rights on those targets. Only enable a member's `allow_install` after preparing its native update helper and deciding that operator-triggered package updates are intended.

`announce_only: true` with `machine_control: true` enables refresh/install handling without the legacy Git worker. With both `announce_only: true` and `machine_control: false`, the worker only reports; queued refresh/install requests will not be handled by that worker.

## Files and precedence

| File | Default location | Role |
| :--- | :--- | :--- |
| Worker configuration | `~/.config/pc-mesh/config.json` | Member identity, hub URLs, certificate and worker settings. |
| Operator configuration | `~/.config/pc-mesh/control.json` | Optional, more privileged operator connection. |
| Installation record | `~/.config/pc-mesh/installation.json` | Generated installation metadata; not a general configuration input. |
| State | `~/.local/state/pc-mesh/` | Snapshots, logs, heartbeat, queue and worker locks. |
| User releases | `~/.local/share/updatewulf/releases/` | Program source and public origin markers. |

`~` in this table means the **execution account's home directory**. On Windows that is normally `%USERPROFILE%`. Machine services can use different state/configuration paths: consult their generated service/task definitions.

Operator commands (`diagnose`, `refresh`, `update`, `tui`, remote `sync`) prefer `control.json` when `--config` has its default path. Supplying a different `--config PATH` selects that file. `status` only reads the selected state directory. No environment-wide `UPDATEWULF_CONFIG` variable or automatic TOML/YAML configuration parser is implemented.

## Worker configuration keys

| Key | Type / code default | Purpose |
| :--- | :--- | :--- |
| `id` | string; no default | Stable member ID/default command target. Keep it consistent with hub enrollment. |
| `hubs` | nonempty list of HTTPS URLs; required | Trusted hub endpoints in preferred/fallback order. |
| `token` | string; required | Member credential for worker reports or operator/read credential for appropriate CLI use. |
| `certificate` | absolute file path; required | Trust material passed to `ssl.create_default_context`. |
| `scan_interval` | number; `1800` | Seconds between native update scans. |
| `report_interval` | number; `20` | Seconds between heartbeat/data reports. |
| `announce_only` | boolean; `false` | Suppress legacy Git worker/report content. |
| `machine_control` | boolean; `false` | With announce-only mode, enable refresh/install request handling. |
| `native_installer` | boolean; `false` | Invoke an already installed Linux/Windows machine updater helper. |
| `auto_self_update` | boolean; `true` | Enable background application updates when the worker's platform/mode permits. |
| `self_update_branch` | string; `main` | Public UpdateWulf application branch. |
| `self_update_interval` | integer; `21600` | Seconds after each attempt, clamped to `3600..86400`. Initial delay is 300 seconds. |
| `repositories` | list; `[]` | Legacy repository sync definitions. Leave empty for normal UpdateWulf use. |
| `git_interval` | number; `300` | Seconds between legacy Git worker cycles when enabled. |
| `hub` | object; absent | Start an HTTPS hub in the same daemon. |
| `ssh_tunnel` | object; absent | Optional authenticated local forwarding transport. |

Use positive, practical interval values. Apart from the application updater's clamping, this is not a complete schema-validated settings API; invalid types or zero/negative intervals can fail or create excessive work. There is no `language` setting: changing the README language does not change runtime messages.

The shipped examples intentionally use `auto_self_update: false` while setup is being verified. That differs from the code default. For a normal enrolled user worker, enabling automatic application updates also requires the worker mode to allow them and a successful initial public migration. Machine services use their native handover instead.

## Hub block

| Key | Default / requirement | Purpose |
| :--- | :--- | :--- |
| `certificate` | required | Server PEM certificate/chain. |
| `private_key` | required | Server private key readable only by the hub execution account. |
| `members` | required list | Enrolled member definitions. |
| `read_token` | required | Read-only fleet access token. |
| `operator_token` | absent | Optional cross-member request authority. |
| `bind` | `0.0.0.0` | Server listening address. The example deliberately narrows this to loopback. |
| `port` | `9797` | HTTPS listening port. |
| `allowed_networks` | existing code default contains private/loopback ranges | Source CIDR allowlist. Set your own explicit list; do not rely on a fleet-specific default. |
| `offline_after` | `150` seconds | Missing-report threshold used by consumers. |
| `stale_after` | `5400` seconds | Old scan threshold used by consumers. |
| `relay_provider` | absent | Legacy member ID permitted to publish Git bundles. |
| `relay_repositories` | `[]` | Legacy allowed repository names for bundle transport. |

Each member contains:

| Key | Requirement | Purpose |
| :--- | :--- | :--- |
| `id` | required | Unique device identity. |
| `name` | required | Human-readable display name. |
| `token` | required for an active member | Independent member credential. |
| `hostname` | optional | Enrolled host alias if no usable reported hostname is available. |
| `allow_install` | boolean; `false` | Allow that member to receive native installation requests. |

A member credential can act for itself. An operator can address other enrolled members, but package requests still require `allow_install`. Native OS authorization is an additional requirement. Keep the server's private key and operator token separate from low-privilege member configurations.

## Optional SSH tunnel

The ordinary setup uses direct HTTPS. For an already authorized SSH route, `ssh_tunnel` supports:

| Key | Default / requirement |
| :--- | :--- |
| `host`, `user` | Required remote SSH endpoint and account. |
| `key` | Required local private key file; never copy another host's private key. |
| `known_hosts` | Required trusted known-hosts file. |
| `ssh` | `ssh`; explicit executable path can be used. |
| `port` | `19897`; local forwarded listening port. |

The worker forwards local `127.0.0.1:<port>` to hub-side `127.0.0.1:9797`. Use the matching local HTTPS URL and a certificate that validates that URL name/IP. Strict SSH host-key checking and identities-only mode are enabled. An SSH tunnel does not disable HTTPS certificate checks.

Legacy `enroll_transport.py` has environment-specific server enrollment assumptions and is not a general first-run wizard. `owner_profiles.py` also belongs to optional provisioning and requires Paramiko. Use the explicit direct-HTTPS setup above for a new portable installation.

## Legacy repository settings

These remain for compatibility, not as a recommendation to configure new Git synchronization in UpdateWulf. Prefer GitSyncWulf for that separate role.

| Repository key | Behavior / default |
| :--- | :--- |
| `path` | Required worktree location; this legacy path handler does expand `~`. |
| `name` | Expected `owner/repository`; default display uses directory name. Required for bundle routes. |
| `url` | GitHub repository URL, needed for optional clone. |
| `branch` | Expected branch; optional clone/bundle default `main`. |
| `remote` | `origin`. |
| `enabled` | Anything other than explicit `false` permits processing. |
| `pinned` | Truthy value skips synchronization. |
| `clone` | Off unless explicitly enabled; permits creating a missing checkout. |
| `ssh_key`, `known_hosts`, `ssh_binary` | Optional host-owned SSH route; binary defaults to `ssh`. |
| `relay`, `relay_publish` | Off unless enabled; legacy bundle download/publication. |

Dirty worktrees, local commits, divergence, detached HEAD, wrong remotes/upstreams and active Git operations are preserved/refused rather than reset. Even this guarded compatibility operation can change worktrees, so it is not part of a status-only installation.

## Configuration changes

Back up the specific private configuration outside Git, edit it, validate JSON, and restart only the service owning it after checking that no native install is active. Confirm a fresh `heartbeat.json`, `diagnose` and the new fleet timestamps. These settings are read at startup, not live-reloaded through a central settings UI.

Implementation references: [pc_mesh.py](../pc_mesh.py) (`Client`, `start_hub`, `Hub`, `daemon`, `sync_repo`, `tunnel_worker`, `main`), [update_control.py](../update_control.py) and the [native installer sources](installation.md#implementation-references).
