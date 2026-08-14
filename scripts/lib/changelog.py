"""Validate the repository changelog and derive stable release notes."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path


STABLE_SEMVER = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
SEMVER = (
    STABLE_SEMVER
    + r"(?:-(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
RELEASE_HEADING = re.compile(
    rf"^## \[(?P<version>{SEMVER})\] - (?P<date>[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})$"
)
CHANGELOG_CATEGORIES = {
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Migration",
}
COMPARISON_LINK = re.compile(r"^\[[^]]+\]:\s+\S+")
FENCE_OPEN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")


class ChangelogError(Exception):
    """Raised when a changelog does not satisfy the release contract."""


def _fenced_lines(lines: list[str]) -> list[bool]:
    flags: list[bool] = []
    fence_character: str | None = None
    fence_length = 0
    for line in lines:
        if fence_character is None:
            match = FENCE_OPEN.match(line)
            if match is None:
                flags.append(False)
                continue
            fence = match.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            flags.append(True)
            continue
        flags.append(True)
        if re.fullmatch(
            rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
            line,
        ):
            fence_character = None
            fence_length = 0
    return flags


def _compare_semver(left: str, right: str) -> int:
    def parts(value: str) -> tuple[tuple[int, int, int], tuple[str, ...] | None]:
        precedence = value.split("+", 1)[0]
        core, separator, prerelease = precedence.partition("-")
        major, minor, patch = core.split(".")
        numbers = (int(major), int(minor), int(patch))
        identifiers = tuple(prerelease.split(".")) if separator else None
        return numbers, identifiers

    left_core, left_prerelease = parts(left)
    right_core, right_prerelease = parts(right)
    if left_core != right_core:
        return 1 if left_core > right_core else -1
    if left_prerelease is None or right_prerelease is None:
        if left_prerelease == right_prerelease:
            return 0
        return 1 if left_prerelease is None else -1
    for left_item, right_item in zip(left_prerelease, right_prerelease):
        if left_item == right_item:
            continue
        if left_item.isdigit() and right_item.isdigit():
            return 1 if int(left_item) > int(right_item) else -1
        if left_item.isdigit() != right_item.isdigit():
            return -1 if left_item.isdigit() else 1
        return 1 if left_item > right_item else -1
    if len(left_prerelease) == len(right_prerelease):
        return 0
    return 1 if len(left_prerelease) > len(right_prerelease) else -1


def validate_changelog(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ChangelogError(f"cannot read {path.name}: {exc}") from exc

    lines = text.splitlines()
    fenced = _fenced_lines(lines)
    root_titles = [
        line
        for line_number, line in enumerate(lines)
        if not fenced[line_number] and line.startswith("# ")
    ]
    if not lines or lines[0] != "# Changelog" or root_titles != ["# Changelog"]:
        raise ChangelogError(
            "CHANGELOG.md must contain exactly one root '# Changelog' title"
        )
    if (
        sum(
            1
            for line_number, line in enumerate(lines)
            if not fenced[line_number] and line == "## [Unreleased]"
        )
        != 1
    ):
        raise ChangelogError(
            "CHANGELOG.md must contain exactly one '## [Unreleased]' section"
        )

    section_headings = [
        line
        for line_number, line in enumerate(lines)
        if not fenced[line_number] and line.startswith("## ")
    ]
    if not section_headings or section_headings[0] != "## [Unreleased]":
        raise ChangelogError(
            "changelog sections must put Unreleased first and releases newest first"
        )

    releases: list[tuple[str, date]] = []
    for line_number, line in enumerate(lines, start=1):
        if (
            fenced[line_number - 1]
            or not line.startswith("## ")
            or line == "## [Unreleased]"
        ):
            continue
        match = RELEASE_HEADING.fullmatch(line)
        if match is None:
            raise ChangelogError(
                f"line {line_number}: invalid level-two section heading: {line!r}"
            )
        try:
            release_date = date.fromisoformat(match.group("date"))
        except ValueError as exc:
            raise ChangelogError(
                f"line {line_number}: invalid level-two section heading: {line!r}"
            ) from exc
        releases.append((match.group("version"), release_date))

    for previous, current in zip(releases, releases[1:]):
        previous_version, previous_date = previous
        current_version, current_date = current
        if (
            _compare_semver(previous_version, current_version) <= 0
            or previous_date < current_date
        ):
            raise ChangelogError(
                "changelog releases must be unique and ordered newest first "
                "by semantic version and release date"
            )

    seen_categories: set[str] = set()
    inside_section = False
    current_category: str | None = None
    current_category_has_content = False

    def finish_category() -> None:
        if current_category is not None and not current_category_has_content:
            raise ChangelogError(
                f"empty changelog category '### {current_category}' must be omitted"
            )

    for line_number, line in enumerate(lines, start=1):
        structural = not fenced[line_number - 1]
        if structural and line.startswith("## "):
            finish_category()
            seen_categories = set()
            inside_section = True
            current_category = None
            current_category_has_content = False
            continue
        if structural and line.startswith("### "):
            finish_category()
            category = line.removeprefix("### ")
            if not inside_section:
                raise ChangelogError(
                    f"line {line_number}: changelog category {category!r} "
                    "must be inside Unreleased or a release section"
                )
            if category not in CHANGELOG_CATEGORIES:
                allowed = ", ".join(sorted(CHANGELOG_CATEGORIES))
                raise ChangelogError(
                    f"line {line_number}: unknown changelog category {category!r}; "
                    f"use one of: {allowed}"
                )
            if category in seen_categories:
                raise ChangelogError(
                    f"line {line_number}: duplicate changelog category {category!r}"
                )
            seen_categories.add(category)
            current_category = category
            current_category_has_content = False
            continue
        if (
            inside_section
            and current_category is None
            and line.strip()
            and COMPARISON_LINK.fullmatch(line) is None
        ):
            raise ChangelogError(
                f"line {line_number}: changelog category required before section content"
            )
        if (
            current_category is not None
            and line.strip()
            and COMPARISON_LINK.fullmatch(line) is None
        ):
            current_category_has_content = True
    finish_category()
    return text


def release_notes(repository: Path, tag: str) -> str:
    stable_tag = re.fullmatch(rf"v{STABLE_SEMVER}", tag)
    if stable_tag is None:
        raise ChangelogError(
            f"release tag must be a stable semantic version in vMAJOR.MINOR.PATCH form: {tag!r}"
        )
    version = tag.removeprefix("v")

    version_path = repository / "VERSION"
    try:
        source_version = version_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ChangelogError(f"cannot read VERSION: {exc}") from exc
    if source_version != version:
        raise ChangelogError(
            f"release tag {tag} disagrees with source VERSION {source_version!r}"
        )

    text = validate_changelog(repository / "CHANGELOG.md")
    lines = text.splitlines(keepends=True)
    fenced = _fenced_lines([line.rstrip("\r\n") for line in lines])
    heading_pattern = re.compile(
        rf"^## \[{re.escape(version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}\n?$"
    )
    start = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if not fenced[index] and heading_pattern.fullmatch(line)
        ),
        None,
    )
    if start is None:
        raise ChangelogError(
            f"release tag {tag} and source VERSION agree, but CHANGELOG.md has no matching release"
        )
    end = next(
        (
            index
            for index in range(start, len(lines))
            if not fenced[index] and lines[index].startswith("## ")
        ),
        len(lines),
    )
    section_lines = lines[start:end]
    while section_lines and (
        not section_lines[-1].strip()
        or COMPARISON_LINK.fullmatch(section_lines[-1].rstrip("\r\n")) is not None
    ):
        section_lines.pop()
    notes = "".join(section_lines).strip("\n")
    if not notes:
        raise ChangelogError(f"CHANGELOG.md release {version} has no release notes")
    return f"{notes}\n"
