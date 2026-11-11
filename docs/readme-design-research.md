# README design research

**Reviewed:** 2026-11-12

**Scope:** the public UpdateWulf README and a reusable multilingual documentation template.

## Selection method

This is a curated selection of ten well-designed GitHub project READMEs, not an
objective ranking of the ten most beautiful repositories. The selection favours
command-line software because its installation, configuration and troubleshooting
needs are relevant to UpdateWulf.

The review examined first-party README content and markup: information hierarchy,
navigation, embedded demonstrations, language access, installation choices and the
route to complete documentation. It does not claim a screenshot-based accessibility
audit or an exhaustive survey of GitHub. The observations below describe the pages
at the review date; recommendations are our own design decisions.

## The ten references

| Reference | Observed design and documentation pattern | Useful application to UpdateWulf |
| --- | --- | --- |
| [Starship](https://github.com/starship/starship) | A centred logo, compact badges, language links and direct installation/configuration links create a recognisable opening. Operating-system installation choices use expandable sections. | Put the seven language links near the top, then offer a short route to the appropriate installation instructions. |
| [bat](https://github.com/sharkdp/bat) | Its header combines a concise description, section navigation and language links. Feature examples pair terminal images with focused explanations and commands. | Explain each common task with a purpose, a verified command and its expected result. |
| [fzf](https://github.com/junegunn/fzf) | A terminal preview and short feature list lead to a detailed contents list. Installation, upgrading, usage, environment variables and advanced examples have distinct sections. | Keep self-update, normal operation and advanced configuration individually discoverable through stable navigation. |
| [Gum](https://github.com/charmbracelet/gum) | A distinctive project image and terminal demonstrations accompany a practical tutorial. The introductory demonstration links to its executable example script. | Make any demonstration reproducible using a checked-in example or documented configuration. |
| [Glow](https://github.com/charmbracelet/glow) | A graphic header and terminal preview introduce a short explanation. Installation, interactive operation, CLI use and a commented configuration example form separate sections. | Explain operation and configuration independently, with a complete example that readers can adapt. |
| [lazygit](https://github.com/jesseduffield/lazygit) | Workflow videos illustrate concrete operations. The contents list leads to task-specific features, tutorials and platform installation instructions. | Name examples after user goals and show the sequence needed to accomplish each goal. |
| [bottom](https://github.com/ClementTsang/bottom) | A terminal demonstration accompanies sections for features, support, installation, configuration and troubleshooting. Official and unofficial platform support are distinguished. | Separate implemented support, recorded verification and unverified targets in the platform matrix. |
| [zoxide](https://github.com/ajeetdsouza/zoxide) | Light and dark logo variants, a compact section menu, commented starter commands and numbered installation steps make the entry point easy to follow. | Keep the opening readable in both GitHub themes and finish installation instructions with an explicit verification step. |
| [Fastfetch](https://github.com/fastfetch-cli/fastfetch) | Multiple terminal examples link to their configuration presets. Platform-specific installation instructions lead to concise usage, help and configuration-generation examples. | Connect examples to actual configuration files and state what a reader should expect to see. |
| [Nushell](https://github.com/nushell/nushell) | A terminal example and contents list lead to an early project-status statement. The README points directly to its book, command reference, cookbook and platform-support policy. | State the current project maturity and make the complete manual accessible from the README without duplicating every reference detail. |

These are the ten primary sources for this research. Their text, logos, screenshots
and animations have not been copied into UpdateWulf. They are design references,
not dependencies or evidence of UpdateWulf functionality.

## Decisions for the UpdateWulf documentation

### Opening and navigation

Use one clear project title and a short purpose statement. Show native-language
links for English, Deutsch, Français, Русский, Español, Polski and Português before
the detailed instructions. Follow them with direct links to download, installation,
the manual, configuration and troubleshooting. Only add a status badge when its
destination and underlying claim can be verified.

### Installation and support

Give prerequisites before installation commands. Distinguish where application
files are installed from the privileges required for an operation. Explain user
and system-wide installation as separate choices, including their paths, scope and
verification commands. A system-wide installation must not be presented as proof
that every action should run as an administrator.

Use a support matrix that distinguishes implementation from testing. Identify the
available download honestly: a source archive, release package or installer is
named only when it actually exists. Document any additional setup for unattended
operation separately from a manual first run.

### Examples and the full manual

Prefer short, copyable examples whose options exist in the current source. Describe
the effect and expected output next to each command. Link configuration examples to
the corresponding reference entry. A complete manual should cover commands,
defaults, file locations, services, logs, exit behaviour, self-update and removal.

The README provides a usable entry point in every requested language. Detailed
reference pages can be shared, but their language must be identified if it differs
from the selected README. Each README must still explain installation, operation,
configuration and important limitations in its own language.

### Known issues and maintenance

Keep reproducible defects, unverified environments and planned work distinct.
For a known defect, describe the affected behaviour, any verified workaround and
its current status. Record a review date so an old limitation is not mistaken for
a permanent product property.

Preserve exact language filenames and check local links with case sensitivity.
Update commands, defaults and all translations together when behaviour changes.
Review any optional imagery in light and dark themes, provide descriptive alternate
text and keep essential instructions available as text.

The included terminal illustration is generated from UpdateWulf's actual prompt
formatter with explicitly fictional fleet data. Reproduce it offline with
`python3 scripts/render_readme_demo.py`. Its SVG has a fixed dark background,
descriptive title and text alternative; the README repeats essential operations
as selectable text. A rasterized preview was visually inspected. Full GitHub
desktop/mobile browser rendering was not verified in the restricted workspace.

## Reusable output

The accompanying `README_TEMPLATE.md` turns these decisions into a reusable
Markdown scaffold. It contains explicit placeholders and maintenance instructions;
projects must replace them with verified facts before publication.
