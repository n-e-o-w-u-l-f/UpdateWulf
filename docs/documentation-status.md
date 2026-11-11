# Documentation and verification status

[Overview](../Readme.md) · [Changes](changes.md) · [Design research](readme-design-research.md)

**Reviewed:** 2026-11-12 (Europe/Paris).

**Source baseline:** public commit `040270d3fe3f9bd8e2a8b6ece344557ad520b503`, runtime version `2.1.0`.

**Scope:** public source, documentation and the narrow installer maintenance described in [changes](changes.md).

## Language coverage

| Language | Entry file | Coverage |
| :--- | :--- | :--- |
| English | [Readme.md](../Readme.md) | Complete source entry page. |
| German | [Readme.de.md](../Readme.de.md) | Same onboarding, platform, installation, operations and limitations. |
| French | [Readme.fr.md](../Readme.fr.md) | Same scope. |
| Russian | [Readme.ru.md](../Readme.ru.md) | Same scope. |
| Spanish | [Readme.es.md](../Readme.es.md) | Same scope. |
| Polish | [Readme.pl.md](../Readme.pl.md) | Same scope. |
| Portuguese | [Readme.pt.md](../Readme.pt.md) | Same scope. |

The detailed handbook is maintained in English and this is disclosed in every README. Technical commands, option names, keys and paths retain their original spelling. Translations were checked for content/command/link parity; no independent native-speaker certification is claimed. Runtime text is still only partially localized.

## Verification record

The tests below run against the source checkout with isolated fixtures. They are not deployment receipts.

| Check | Result | Meaning |
| :--- | :--- | :--- |
| Existing announcement suite | PASS — 29 tests | Portable collector/status/control regressions. |
| Full public `unittest` discovery | PASS — 31 tests | Includes nine new installer entry-point/preflight tests. |
| Test input fingerprint before/after | MATCH | Tested Python and shell files did not change during the suite. |
| Python compilation and Python 3.9 grammar | PASS — 24 Python files | Syntax only; no service activation. |
| Bash installer syntax | PASS — both shell entry points | Syntax only; no installation. |
| Offline documentation links/anchors/examples | PASS — 16 Markdown files, 395 local links, 3 JSON examples | Run `python3 scripts/check_docs.py`. |
| Terminal illustration | PASS — generated SVG parsed and raster preview inspected | Real formatter, explicitly fictional demonstration data; not a live fleet screenshot. |
| Full README desktop/mobile browser rendering | NOT RUN — local browser launch restricted | No browser-layout acceptance claim. |
| Windows PowerShell parser | NOT RUN in this Linux workspace | No PowerShell executable available here; PowerShell source was not modified. |
| Native Windows/NetBSD/Termux service acceptance | NOT RUN | Requires the actual corresponding OS/account. |
| Fleet installation, package upgrades, reboot | NOT RUN | Outside this documentation maintenance task. |
| Hosted CI | NOT DISPATCHED by this task | Local results do not claim a passing hosted workflow. |

The source tests are intentionally separate from host acceptance. A running service, fresh heartbeat, correct source commit, live prompt and native update behavior must be verified on each intended host before declaring a fleet deployment complete.

## Maintaining parity

Use [the reusable template](README_TEMPLATE.md) for the same section coverage. When commands, configuration or installer behavior change, update the English source entry, all translations, examples and the relevant handbook pages together. Then run the offline documentation checker and the tests appropriate to the changed behavior. Keep this record and [known issues](troubleshooting.md#known-issues) truthful.

## GitBook

The repository includes [SUMMARY.md](../SUMMARY.md) and [.gitbook.yaml](../.gitbook.yaml) with `Readme.md` as the entry point. These files prepare the content for GitBook; they do not themselves establish an authenticated Git Sync connection. Git Sync wiring is an explicit GitBook UI operation. Select this public repository and `main`, using GitHub → GitBook for the initial import. See the primary [GitBook content-configuration documentation](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration).

GitHub remains the source of the exact Markdown revisions. A separate GitBook content import is a publication snapshot unless an actual Git Sync connection has been configured and verified.
