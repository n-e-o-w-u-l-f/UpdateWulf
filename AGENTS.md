# UpdateWulf public release instructions

Scope: only the public UpdateWulf application. Canonical source:
`n-e-o-w-u-l-f/UpdateWulf`, branch `main`. Historical integration code
lives in the private `.UpdateWulf-Service` project source; do not publish
that repository's Git history or internal host documentation.

Preserve config, secrets, per-host enrollment, state, shell profiles and
all unrecognized local files. Existing installations may be activated
only through native host-authorized runbooks with rollback. No host-to-host
Git authority or destructive Git reset/clean/force operations. No automatic
OS package installations or reboots without explicit operator intent.

Required tests: Python compile, test_update_announce.py, full public
unittest discovery, Windows PowerShell parser, Unix Bash syntax, then native
owner host verification of CLI, service and prompt. A successful GitHub
push is not a deployment receipt. Files under the application release root
are immutable between updates; old releases can be pruned only under
self_update.py's strict marker and path gates.

Documentation follows `docs/README_TEMPLATE.md`. Keep the seven root files
`Readme.md`, `Readme.de.md`, `Readme.fr.md`, `Readme.ru.md`, `Readme.es.md`,
`Readme.pl.md` and `Readme.pt.md` in the same section order and technical
scope. Update the handbook, examples, `SUMMARY.md` and verification record
with relevant source changes. Run `python3 scripts/check_docs.py`; do not
claim unexecuted native tests, nonexistent release assets or a license.
