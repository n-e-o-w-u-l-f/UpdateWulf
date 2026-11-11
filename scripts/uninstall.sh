#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root." >&2
  exit 1
fi

PURGE_CONFIG=0
PURGE_STATE=0
for arg in "$@"; do
  case "$arg" in
    --purge-config) PURGE_CONFIG=1 ;;
    --purge-state) PURGE_STATE=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

systemctl disable --now github-sync.timer 2>/dev/null || true
systemctl stop github-sync.service 2>/dev/null || true
rm -f /etc/systemd/system/github-sync.service /etc/systemd/system/github-sync.timer
rm -f /usr/local/bin/github-sync
rm -rf /usr/local/lib/github-sync
systemctl daemon-reload
systemctl reset-failed github-sync.service 2>/dev/null || true

if [ "$PURGE_CONFIG" -eq 1 ]; then
  rm -rf /etc/github-sync
fi
if [ "$PURGE_STATE" -eq 1 ]; then
  rm -rf /var/lib/github-sync
fi

# /home/andreas/Projekte is deliberately never removed or modified here.
echo "UpdateWulf-Service removed. Repository working copies were preserved."
