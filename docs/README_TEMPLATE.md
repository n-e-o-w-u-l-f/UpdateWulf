# Global multilingual README template

**Template revision:** 2026-11-12

**Purpose:** a consistent, accessible entry point for software projects, derived
from the ten first-party references documented in `readme-design-research.md`.

## Authoring and maintenance rules

1. Copy the scaffold below to the repository root and replace every angle-bracket
   placeholder with verified project information. Placeholder commands are text,
   not executable instructions. Use the correct shell language once commands are
   real and checked.
2. Keep exactly these root entry filenames: `Readme.md` (English), `Readme.de.md`
   (German), `Readme.fr.md` (French), `Readme.ru.md` (Russian), `Readme.es.md`
   (Spanish), `Readme.pl.md` (Polish) and `Readme.pt.md` (Portuguese). Avoid a second
   English entry point differing only by case.
3. Preserve the native-language selector in every translation. Translate all
   user-facing explanations, section names and example comments. Keep actual
   commands, option names, configuration keys and paths unchanged.
4. Keep the same section order and technical meaning across all seven READMEs.
   The language of linked reference pages must be stated where it differs from
   the README. Record the reviewed source revision and translation status in a
   documentation-status file.
5. Use repository-relative links. The scaffold assumes it will live at the root;
   its `docs/` links must point to real pages. When adding or renaming a page,
   update navigation and check links and anchors with case sensitivity.
6. Add a logo, screenshot, animation or badge only if it is useful, appropriately
   licensed and accurate. Supply alternate text. Verify light/dark readability;
   keep essential instructions in text. Do not invent a release, passing build,
   support guarantee, benchmark, license or package-manager entry.
7. Separate implemented functionality, verified behaviour, known defects and
   planned work. Never turn an unexecuted test into a passing result. Describe
   installation scope separately from runtime privileges.
8. Check documented commands and configuration against the source whenever either
   changes. Update defaults, examples, manual pages and translations together.
   Match download links to actual artifacts and preserve existing user data when
   describing upgrades or removal.

## Root README scaffold

The four-backtick fence makes the entire scaffold copyable, including its inner
command blocks. Replace all placeholders before publishing. Create the linked
manual pages or change the links to the project's actual documentation.

````markdown
# <PROJECT>

<One sentence explaining what the software does and who it helps.>

[English](Readme.md) · [Deutsch](Readme.de.md) · [Français](Readme.fr.md) ·
[Русский](Readme.ru.md) · [Español](Readme.es.md) · [Polski](Readme.pl.md) ·
[Português](Readme.pt.md)

**[Download](#download) · [Install](#installation) ·
[Manual](docs/manual.md) · [Configure](docs/configuration.md) ·
[Troubleshoot](docs/troubleshooting.md)**

## Status

<Current maturity and the scope of this documentation, based on verified facts.>

| Item | Current information |
| --- | --- |
| Documented version or revision | <VERIFIED_VERSION_OR_REVISION> |
| Documentation reviewed | <YYYY-MM-DD> |
| Reference manual language | <LANGUAGE> |
| Important limitation | <ACTUAL_LIMITATION_OR_LINK> |

## What you can do

- <A concrete implemented capability and its benefit.>
- <Another implemented capability and its benefit.>
- <A third capability, only when useful and supported.>

### Use cases

| Goal | How the project helps |
| --- | --- |
| <USER_GOAL> | <IMPLEMENTED_WORKFLOW> |
| <ANOTHER_USER_GOAL> | <IMPLEMENTED_WORKFLOW> |

<Explain important scope boundaries or unsupported uses relevant to a decision.>

## Requirements and supported systems

<State mandatory dependencies, required runtime versions and relevant network
requirements. Identify optional dependencies separately.>

| System | Prerequisites | Available installation scope | Verification status |
| --- | --- | --- | --- |
| <OS_AND_VERSION> | <RUNTIME_AND_DEPENDENCIES> | <USER_SYSTEM_OR_BOTH> | <RECORDED_RESULT_OR_UNVERIFIED> |

<Explain any privilege requirement for installation and normal operation.>

## Download

<State whether the project currently provides source, packaged releases,
installers or some combination. Identify the recommended available option.>

| Download | Intended use | Verification |
| --- | --- | --- |
| [<ACTUAL_ARTIFACT_NAME>](<VERIFIED_DOWNLOAD_URL>) | <OS_ARCHITECTURE_OR_SOURCE_USE> | <ACTUAL_CHECKSUM_SIGNATURE_OR_LIMITATION> |

<If no packaged release exists, say so and provide a real source-download or
clone route. Do not present a source archive as a prebuilt application.>

## Installation

Choose the installation scope that matches your needs. See the
[complete installation guide](docs/installation.md) for additional platforms.

| Choice | Application location | Who can use it | Installation privileges |
| --- | --- | --- | --- |
| Current user | <USER_APPLICATION_PATH> | <ACTUAL_SCOPE> | <ACTUAL_REQUIREMENT> |
| System-wide | <SYSTEM_APPLICATION_PATH> | <ACTUAL_SCOPE> | <ACTUAL_REQUIREMENT> |

### Install for the current user

<Explain prerequisites for this route, which shell to use, and the working
directory from which the command should be executed.>

```text
<VERIFIED_USER_INSTALL_COMMAND>
```

<Explain PATH handling and whether a new terminal session is needed.>

### Install system-wide

<Explain the required administrator/root context, target paths and any service
account involved. State whether this route actually installs or enables a service.>

```text
<VERIFIED_SYSTEM_INSTALL_COMMAND>
```

<Document unavailable installation scopes honestly instead of fabricating a
command. Keep a separate subsection for each supported operating-system route.>

## First run

Verify the installation:

```text
<VERIFIED_VERSION_OR_HELP_COMMAND>
```

Then run the smallest useful example:

```text
<VERIFIED_FIRST_RUN_COMMAND>
```

**Expected result:** <Describe the result and how to recognise success.>

<Explain whether this action changes the system, requires credentials or needs
operator confirmation. Prefer an informational first run when available.>

## Examples

### <COMMON_TASK_TITLE>

<Explain the goal and prerequisites in one or two sentences.>

```text
<VERIFIED_COMMAND>
```

**Result:** <Expected behaviour, output or file.>

### <SECOND_COMMON_TASK_TITLE>

```text
<VERIFIED_COMMAND>
```

**Result:** <Expected behaviour and any relevant limitation.>

## Full manual

| Topic | Documentation |
| --- | --- |
| Commands, options and behaviour | [Manual](docs/manual.md) |
| Prerequisites, installation and upgrades | [Installation guide](docs/installation.md) |
| Configuration keys, defaults and precedence | [Configuration reference](docs/configuration.md) |
| Logs, diagnostics and failure recovery | [Troubleshooting](docs/troubleshooting.md) |

<State the language of these pages. Every supported command and configuration
key must be covered by the manual or reference, even when omitted from this overview.>

### Command overview

| Command or action | Purpose | Relevant effect or privilege |
| --- | --- | --- |
| `<ACTUAL_COMMAND>` | <PURPOSE> | <EFFECT_OR_PRIVILEGE> |

## Configuration

<Describe the actual format and how configuration is created or selected.>

| Item | User installation | System installation |
| --- | --- | --- |
| Configuration | <ACTUAL_PATH> | <ACTUAL_PATH> |
| Persistent state | <ACTUAL_PATH> | <ACTUAL_PATH> |
| Logs | <ACTUAL_PATH_OR_LOG_SYSTEM> | <ACTUAL_PATH_OR_LOG_SYSTEM> |

**Precedence:** <List the implemented order of CLI flags, environment variables,
configuration files and defaults, or explain the actual selection mechanism.>

```text
<VALID_MINIMAL_CONFIGURATION_WITH_NON_SECRET_EXAMPLE_VALUES>
```

| Setting | Default | Accepted values | Effect |
| --- | --- | --- | --- |
| `<ACTUAL_KEY>` | `<ACTUAL_DEFAULT>` | <VALUES> | <EFFECT> |

<Link to a complete example file and document how credentials are supplied
without including real secrets. Explain when configuration changes take effect.>

## Services and automation

<Describe implemented service/timer/scheduler support. State explicitly if the
project only supports manual operation. Do not invent background-service commands.>

| Task | Verified procedure |
| --- | --- |
| Enable unattended operation | <ACTUAL_COMMAND_OR_UNSUPPORTED> |
| Inspect status | <ACTUAL_COMMAND> |
| Read logs | <ACTUAL_COMMAND_OR_LOCATION> |
| Stop or disable automation | <ACTUAL_COMMAND> |

<Explain the runtime account, schedule, privilege model and any interaction
required by the underlying operation.>

## Update the application

<Distinguish updating this application's code from the work the application
performs. Describe the actual supported update mechanism and what it preserves.>

```text
<VERIFIED_APPLICATION_UPDATE_COMMAND_OR_PROCEDURE>
```

<Describe verification after updating, and an available recovery or rollback
procedure. If self-update is unavailable, document the supported manual procedure.>

## Logs and exit behaviour

<Explain where diagnostics are written and what users should inspect first.>

| Code or status | Meaning | Recommended response |
| --- | --- | --- |
| `<ACTUAL_CODE_OR_STATUS>` | <ACTUAL_MEANING> | <ACTION> |

<Mention whether output can be machine-readable or colour-free only when the
implementation supports it. Link to the complete troubleshooting reference.>

## Known issues and troubleshooting

**Last reviewed:** <YYYY-MM-DD>

| Issue or symptom | Affected behaviour | Verified workaround or next step | Status |
| --- | --- | --- | --- |
| <ACTUAL_ISSUE> | <SCOPE> | <WORKAROUND_OR_NONE_KNOWN> | <VERIFIED_STATUS> |

<If no defects are currently recorded, say that without promising bug-free
software. List unverified environments separately from reproducible bugs.>

See [Troubleshooting](docs/troubleshooting.md) for diagnosis and recovery. When
reporting a problem, provide <ACTUAL_USEFUL_DIAGNOSTICS>, remove credentials and
personal data, and include the exact command and result.

## Uninstall

<Explain how to stop any installed automation before removing application files.>

```text
<VERIFIED_UNINSTALL_COMMAND_OR_MANUAL_PROCEDURE>
```

<List exactly what is removed and which configuration, state and logs remain.
Document any optional data-removal step separately, with its precise effect.>

## FAQ

### <FREQUENT_USER_QUESTION>

<A concise answer based on current behaviour, with a relevant documentation link.>

### <SECOND_FREQUENT_USER_QUESTION>

<A concise answer.>

## Support and contributing

<Link to real support channels and contribution instructions. Describe how to
report bugs, suggest features and improve translations. Identify a verified
private reporting route for security issues when one exists.>

## Changes and roadmap

<Link to the actual changelog or release history. Clearly label planned work;
do not present roadmap items as already available.>

## License

<State the actual license and link to its file. If no license is declared,
say so explicitly rather than assigning one.>
````
