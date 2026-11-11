#!/usr/bin/env bash
# Deliberately non-destructive: installation ownership differs by platform.
set -euo pipefail

printf '%s\n' \
  'UpdateWulf does not provide an automatic uninstaller.' \
  'Follow docs/installation.md#uninstall for the installed user or machine service.' \
  'No services, files, configuration, credentials or GitSyncWulf data were changed.'

if [ "$#" -eq 1 ] && { [ "$1" = '--help' ] || [ "$1" = '-h' ]; }; then
  exit 0
fi
exit 2
