#!/usr/bin/env python3
"""Validate the public documentation offline using only Python's standard library.

Run from any directory: python scripts/check_docs.py
No network requests, installers, services or native platform commands are run.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


README_FILES = (
    "Readme.md", "Readme.de.md", "Readme.fr.md", "Readme.ru.md",
    "Readme.es.md", "Readme.pl.md", "Readme.pt.md",
)
REQUIRED_DOCS = (
    *README_FILES, "SUMMARY.md", "docs/manual.md", "docs/installation.md",
    "docs/configuration.md", "docs/troubleshooting.md",
    "docs/documentation-status.md", "docs/readme-design-research.md",
    "docs/README_TEMPLATE.md",
)
REQUIRED_EXAMPLES = (
    "examples/config.client.json", "examples/config.hub.json", "examples/control.json",
)
MAX_DOC_BYTES = 32 * 1024
PRIVATE_REPOSITORIES = {".updatewulf-service", "agent-governance"}
URL_PATTERN = re.compile(r"(?:https?://|sandbox:|file://)[^\s<>\"']+", re.I)
LINK_PATTERN = re.compile(
    r"!?\[(?P<label>(?:[^\[\]\\]|\\.|\[[^\]]*\])*)\]"
    r"\((?P<target>(?:[^()\\]|\\.|\([^()]*\))*)\)"
)
REFERENCE_PATTERN = re.compile(r"!?\[([^\]\n]+)\](?:\[([^\]\n]*)\])?")
DEFINITION_PATTERN = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(.+)$", re.M)


@dataclass
class Document:
    path: Path
    text: str
    anchors: set[str]
    links: list[tuple[str, int]]


def reference_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def link_target(value: str) -> str:
    """Remove an optional link title and unwrap an angle-bracket destination."""
    value = value.strip()
    if value.startswith("<"):
        end = value.find(">")
        value = value[1:end] if end >= 0 else value[1:]
    else:
        value = re.split(r"\s", value, maxsplit=1)[0] if value else ""
    return html.unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", value))


def visible_markdown(text: str) -> str:
    """Blank fenced blocks and comments while preserving diagnostic line numbers."""
    result: list[str] = []
    fence_character = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        # A fence inside a blockquote is still a fenced code block.
        candidate = re.sub(r"^(?: {0,3}>[ \t]?)+", "", line)
        match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", candidate)
        if fence_character:
            if (match and match[1][0] == fence_character
                    and len(match[1]) >= fence_length and not match[2].strip()):
                fence_character = ""
            result.append("\n" if line.endswith("\n") else "")
        elif match:
            fence_character, fence_length = match[1][0], len(match[1])
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(line)
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m[0].count("\n"),
                  "".join(result), flags=re.S)


def without_inline_code(text: str) -> str:
    return re.sub(r"(`+)(.+?)\1", lambda m: " " * len(m[0]), text)


def heading_slug(heading: str) -> str:
    """GFM-style heading identifier, retaining Unicode letters, '-' and '_'."""
    heading = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", heading)
    heading = re.sub(r"!?\[([^\]]+)\]\[[^\]]*\]", r"\1", heading)
    heading = re.sub(r"<[^>]*>", "", heading)
    heading = re.sub(r"(?<!\w)(\*{1,3}|_{1,3})(.+?)\1(?!\w)", r"\2", heading)
    heading = html.unescape(heading).replace("`", "").strip().lower()
    heading = "".join(char for char in heading
                      if char in "-_" or unicodedata.category(char)[0] not in "PSC")
    return re.sub(r"\s", "-", heading)


class HtmlReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: set[str] = set()
        self.links: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in (("id", "name") if tag == "a" else ("id",)):
            if values.get(key):
                self.anchors.add(values[key] or "")
        for key in ("href", "src"):
            if values.get(key):
                self.links.append((values[key] or "", self.getpos()[0]))

    handle_startendtag = handle_starttag


def parse_document(path: Path, text: str) -> Document:
    visible = visible_markdown(text)
    links: list[tuple[str, int]] = []
    parsed = HtmlReferences()
    parsed.feed(without_inline_code(visible))
    anchors = set(parsed.anchors)
    links.extend(parsed.links)

    # Duplicate headings follow GitHub's suffix convention: title, title-1, ...
    heading_ids: set[str] = set()
    previous = ""
    for line in visible.splitlines():
        match = re.match(r"^ {0,3}#{1,6}[ \t]+(.*)$", line)
        heading = re.sub(r"[ \t]+#+[ \t]*$", "", match[1]) if match else None
        if (heading is None and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", line)
                and previous.strip() and not re.match(r"^\s*(?:#|>|[-*+]\s)", previous)):
            heading = previous.strip()
        if heading is not None:
            base = heading_slug(heading)
            slug, suffix = base, 0
            while slug in heading_ids:
                suffix += 1
                slug = f"{base}-{suffix}"
            heading_ids.add(slug)
        previous = line
    anchors.update(heading_ids)

    searchable = without_inline_code(visible)
    definitions = {
        reference_key(match[1]): link_target(match[2])
        for match in DEFINITION_PATTERN.finditer(searchable)
    }
    for match in LINK_PATTERN.finditer(searchable):
        links.append((link_target(match["target"]), searchable.count("\n", 0, match.start()) + 1))
    # Blank inline links and definitions before checking reference-style links.
    references = LINK_PATTERN.sub(lambda m: " " * len(m[0]), searchable)
    references = DEFINITION_PATTERN.sub(lambda m: " " * len(m[0]), references)
    for match in REFERENCE_PATTERN.finditer(references):
        key = reference_key(match[2] or match[1])
        if key in definitions:
            links.append((definitions[key], references.count("\n", 0, match.start()) + 1))
    return Document(path, text, anchors, links)


def exact_path(root: Path, relative: Path) -> bool:
    """Check each filename literally, including on case-insensitive filesystems."""
    current = root
    for part in relative.parts:
        if not current.is_dir():
            return False
        if part not in {entry.name for entry in current.iterdir()}:
            return False
        current = current / part
    return current.exists()


def check_private_urls(text: str) -> list[str]:
    problems: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = html.unescape(match[0]).rstrip(").,;")
        try:
            parsed = urlsplit(url)
        except ValueError:
            problems.append(f"malformed URL: {url}")
            continue
        if parsed.scheme.lower() in {"sandbox", "file"}:
            problems.append(f"non-public local URL: {url}")
            continue
        host = (parsed.hostname or "").lower()
        parts = [unquote(part).lower().removesuffix(".git")
                 for part in parsed.path.split("/") if part]
        if host == "git.chatgpt-team.site":
            problems.append(f"internal Git transport URL: {url}")
        if host in {"github.com", "www.github.com", "raw.githubusercontent.com", "api.github.com"}:
            if "n-e-o-w-u-l-f" in parts:
                index = parts.index("n-e-o-w-u-l-f") + 1
                if index < len(parts) and parts[index] in PRIVATE_REPOSITORIES:
                    problems.append(f"private source URL: {url}")
    if re.search(r"git@github\.com:n-e-o-w-u-l-f/(?:\.UpdateWulf-Service|Agent-Governance)(?:\.git)?(?:\s|$)", text, re.I):
        problems.append("private source SSH URL")
    return problems


def reject_non_json_constant(value: str) -> None:
    raise ValueError(f"not a JSON constant: {value}")


def validate(root: Path) -> int:
    errors: list[str] = []
    if not root.is_dir():
        print(f"FAIL: repository directory does not exist: {root}", file=sys.stderr)
        return 1
    for relative in (*REQUIRED_DOCS, *REQUIRED_EXAMPLES):
        if not exact_path(root, Path(relative)) or not (root / relative).is_file():
            errors.append(f"missing required file or incorrect filename case: {relative}")
    for expected in README_FILES:
        for entry in root.iterdir():
            if entry.name.casefold() == expected.casefold() and entry.name != expected:
                errors.append(f"README filename must be exactly {expected}, found {entry.name}")

    paths = {path for path in root.iterdir()
             if path.is_file() and path.name.lower().startswith("readme") and path.suffix.lower() == ".md"}
    paths.update((root / "docs").rglob("*.md"))
    if (root / "SUMMARY.md").is_file():
        paths.add(root / "SUMMARY.md")
    documents: dict[Path, Document] = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size > MAX_DOC_BYTES:
            errors.append(f"{relative}: {path.stat().st_size} bytes exceeds 32 KiB")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: cannot read UTF-8: {exc}")
            continue
        documents[path] = parse_document(path, text)
        errors.extend(f"{relative}: {problem}" for problem in check_private_urls(text))

    checked_links = 0
    for path, document in documents.items():
        relative = path.relative_to(root).as_posix()
        language_links: set[str] = set()
        for target, line in document.links:
            try:
                parsed = urlsplit(target)
            except ValueError:
                errors.append(f"{relative}:{line}: malformed link: {target}")
                continue
            if parsed.scheme or parsed.netloc:
                continue
            local_name = unquote(parsed.path)
            fragment = unquote(parsed.fragment)
            if local_name.startswith("/"):
                errors.append(f"{relative}:{line}: use a repository-relative link: {target}")
                continue
            # abspath removes '..' without correcting case on Windows; resolve
            # is used separately to reject symlink escapes from the repository.
            destination = Path(os.path.abspath(path.parent / local_name)) if local_name else path
            if not destination.is_relative_to(root) or not destination.resolve().is_relative_to(root):
                errors.append(f"{relative}:{line}: link leaves the repository: {target}")
                continue
            if not exact_path(root, destination.relative_to(root)):
                errors.append(f"{relative}:{line}: missing local link or incorrect case: {target}")
                continue
            checked_links += 1
            if destination.parent == root and destination.name in README_FILES:
                language_links.add(destination.name)
            if fragment and destination.suffix.lower() == ".md":
                linked = documents.get(destination)
                if linked is None:
                    try:
                        linked = parse_document(destination, destination.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError) as exc:
                        errors.append(f"{relative}:{line}: cannot read linked document: {exc}")
                        continue
                if fragment not in linked.anchors:
                    errors.append(f"{relative}:{line}: missing fragment anchor: {target}")
        if path.parent == root and path.name in README_FILES:
            for missing in sorted(set(README_FILES) - language_links):
                errors.append(f"{relative}: missing language-selector link to {missing}")

    examples = sorted((root / "examples").glob("*.json"))
    for path in examples:
        try:
            json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_non_json_constant)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: invalid JSON: {exc}")
    if errors:
        print(f"FAIL: {len(errors)} documentation problem(s)", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"PASS: {len(documents)} Markdown files, {checked_links} local links, "
          f"{len(examples)} JSON examples; seven locales; offline validation only")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1],
                        help="repository root (defaults to this script's parent repository)")
    args = parser.parse_args()
    return validate(args.root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
