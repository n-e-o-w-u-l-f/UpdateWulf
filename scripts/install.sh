#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root." >&2
  exit 1
fi
for cmd in python3 git systemctl install; do
  command -v "$cmd" >/dev/null || { echo "Missing dependency: $cmd" >&2; exit 1; }
done
id andreas >/dev/null 2>&1 || { echo "Required user 'andreas' does not exist." >&2; exit 1; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'

install -d -m 0755 /usr/local/lib/github-sync /etc/github-sync
install -m 0755 "$ROOT_DIR/src/github_sync.py" /usr/local/lib/github-sync/github_sync.py
install -m 0755 "$ROOT_DIR/src/git_askpass.py" /usr/local/lib/github-sync/git-askpass
ln -sfn /usr/local/lib/github-sync/github_sync.py /usr/local/bin/github-sync

if [ ! -e /etc/github-sync/config.toml ]; then
  install -m 0644 "$ROOT_DIR/config/config.example.toml" /etc/github-sync/config.toml
fi
if [ ! -e /etc/github-sync/credentials.json ]; then
  printf '{"tokens":{}}\n' > /etc/github-sync/credentials.json
  chmod 0600 /etc/github-sync/credentials.json
fi
chown root:root /etc/github-sync/config.toml /etc/github-sync/credentials.json
chmod 0644 /etc/github-sync/config.toml
chmod 0600 /etc/github-sync/credentials.json

install -d -o andreas -g andreas -m 0755 /home/andreas/Projekte
install -m 0644 "$ROOT_DIR/packaging/github-sync.service" /etc/systemd/system/github-sync.service
install -m 0644 "$ROOT_DIR/packaging/github-sync.timer" /etc/systemd/system/github-sync.timer
systemctl daemon-reload

/usr/local/bin/github-sync --version
systemd-analyze verify /etc/systemd/system/github-sync.service /etc/systemd/system/github-sync.timer

echo "Installed. Configure /etc/github-sync/credentials.json, run a manual service test, then enable github-sync.timer."
