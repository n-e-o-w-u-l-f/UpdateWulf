# Changes

[Overview](../Readme.md) · [Verification](documentation-status.md)

## Unreleased — documentation and installer maintenance, 2026-11-12

### Added

- Seven complete localized entry pages: English, German, French, Russian, Spanish, Polish and Portuguese, using the exact `Readme*.md` filename convention.
- English technical handbook covering installation scopes, every CLI action/option, configuration, hub enrollment, self-update, logs, known issues, rollback and manual removal.
- Client, hub and operator JSON examples with explicit placeholders, no live credentials and conservative initial defaults.
- A reusable README template and a documented selection of ten first-party GitHub design references.
- GitBook content configuration and navigation, plus an offline documentation/link checker.
- Reproducible terminal illustration generated from the real formatter and clearly labelled fictional data.
- Nine installer regression tests.

### Fixed

- `scripts/install.sh` now dispatches to the UpdateWulf Unix user installer and preserves argument boundaries. It no longer attempts to install the unrelated historical Git synchronization component.
- `scripts/uninstall.sh` no longer touches Git synchronization services or directories. It explicitly explains the manual UpdateWulf removal route and returns a non-success code when no removal was performed.
- Unix user installation checks source prerequisites and readable JSON configuration before modifying shell profiles. Prompt-only installation still does not need a worker configuration.

### Documentation corrections

- Cached status is distinguished from fresh scans and completed package updates.
- Platform adapters are distinguished from native end-to-end test coverage.
- Seven documentation languages are distinguished from the currently partial runtime localization.
- Download links describe the actual source archive; no native installer assets or license are invented.
- Custom-path self-update, conservative release retention, empty-fleet TUI and shell-specific limitations are documented.

This maintenance change keeps the existing `2.1.0` runtime version. It does not create a release tag or install software on the user's computers. Identify the precise revision by its Git commit.

## Public source baseline — 2.1.0

The documentation was prepared from public commit `040270d3fe3f9bd8e2a8b6ece344557ad520b503`. That baseline includes native update status/control, per-platform installer helpers and public-repository application self-update. No tagged release assets were present when the documentation was prepared.
