"""Resolve, audit, and synchronize repository-standard managed files."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .changelog import ChangelogError, SEMVER, validate_changelog
from .repository_contract import (
    ContractError,
    RepositoryBoundary,
    RepositoryContract,
    resolve_repository_contract,
)


SUPPORTED_STANDARDS_VERSION = 5
MANIFEST_NAMES = (
    ".repository-standards.json",
    ".repository-standards.yml",
    ".repository-standards.yaml",
)
VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
SEMVER_PATTERN = re.compile(rf"^{SEMVER}$")
MARKDOWN_H1_PATTERN = re.compile(r"^#(?!#)\s+(.+?)\s*$", re.MULTILINE)
CENTERED_WRAPPER_PATTERN = re.compile(
    r"<(?:div|p)\b[^>]*\balign\s*=\s*[\"']?center[\"']?[^>]*>",
    re.IGNORECASE,
)
HTML_H1_PATTERN = re.compile(r"<h1(?:\s[^>]*)?>.*?</h1>", re.IGNORECASE | re.DOTALL)
BADGE_PATTERN = re.compile(r"(?:img\.shields\.io|/badge\.svg(?:[?#)]|$))", re.IGNORECASE)
DOCS_LINK_PATTERN = re.compile(
    r"\]\((?:\./)?docs/README\.md(?:#[^ )]+)?(?:\s+[\"'][^\"']*[\"'])?\)"
)
DIATAXIS_CATEGORIES = (
    "tutorials",
    "how-to",
    "reference",
    "explanation",
    "adr",
)
DEPENDENCY_ECOSYSTEMS = {"github-actions", "maven", "npm"}
DEPENDENCY_INTERVALS = {"daily", "weekly", "monthly"}


class StandardsError(Exception):
    """Raised for an invalid manifest, profile, or managed plan."""


@dataclass(frozen=True)
class Source:
    mode: str
    path: Path | None
    target: str
    order: int
    profile: str
    profile_index: int


@dataclass(frozen=True)
class PlannedFile:
    target: str
    mode: str
    content: bytes
    origins: tuple[str, ...]


@dataclass(frozen=True)
class PlanBuildBlocker:
    target: str
    message: str


@dataclass(frozen=True)
class Result:
    target: str
    status: str
    mode: str
    expected: bytes
    actual: bytes | None
    origins: tuple[str, ...]


@dataclass(frozen=True)
class BoundaryResult:
    path: str
    boundary_type: str
    status: str
    messages: tuple[str, ...]


@dataclass(frozen=True)
class DocumentResult:
    path: str
    status: str
    messages: tuple[str, ...]


def standards_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _relative_path(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value == ".":
        raise StandardsError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise StandardsError(f"{field} must stay within the repository: {value!r}")
    normalized = path.as_posix()
    if value != normalized:
        raise StandardsError(f"{field} must be a normalized relative path: {value!r}")
    return normalized


def _boundary_path(value: Any, field: str) -> str:
    if value == ".":
        return "."
    if isinstance(value, str) and value != PurePosixPath(value).as_posix():
        raise StandardsError(
            f"{field} must be a normalized concrete directory: {value!r}"
        )
    normalized = _relative_path(value, field)
    if value != normalized or any(character in normalized for character in "*?["):
        raise StandardsError(f"{field} must be a normalized concrete directory: {value!r}")
    return normalized


def _read_data(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StandardsError(f"cannot read {path}: {exc}") from exc

    if path.suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StandardsError(f"invalid JSON in {path}: {exc}") from exc
    else:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise StandardsError(
                f"{path.name} requires PyYAML; use .repository-standards.json "
                "for dependency-free operation"
            ) from exc
        try:
            value = yaml.safe_load(text)
        except yaml.YAMLError as exc:  # type: ignore[attr-defined]
            raise StandardsError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise StandardsError(f"{path} must contain an object")
    return value


def _find_manifest(repository: Path, requested: str | None = None) -> Path:
    if requested:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = repository / candidate
        if not candidate.is_file():
            raise StandardsError(f"manifest not found: {candidate}")
        return candidate.resolve()

    found = [repository / name for name in MANIFEST_NAMES if (repository / name).is_file()]
    if not found:
        names = ", ".join(MANIFEST_NAMES)
        raise StandardsError(f"no repository standards manifest found ({names})")
    if len(found) > 1:
        raise StandardsError(f"multiple manifests found: {', '.join(str(path) for path in found)}")
    return found[0].resolve()


def _load_manifest(repository: Path, requested: str | None = None) -> tuple[Path, dict[str, Any]]:
    path = _find_manifest(repository, requested)
    manifest = _read_data(path)
    allowed = {
        "$schema",
        "standards-version",
        "standards-release",
        "profiles",
        "boundaries",
        "dependency-updates",
        "github",
        "variables",
        "local-fragments",
        "repository-owned",
    }
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        raise StandardsError(f"unknown manifest fields: {', '.join(unknown)}")
    if "$schema" in manifest and not isinstance(manifest["$schema"], str):
        raise StandardsError("$schema must be a string")

    if manifest.get("standards-version") != SUPPORTED_STANDARDS_VERSION:
        raise StandardsError(
            "standards-version must be " f"{SUPPORTED_STANDARDS_VERSION}"
        )

    standards_release = manifest.get("standards-release")
    if not isinstance(standards_release, str) or not SEMVER_PATTERN.fullmatch(
        standards_release
    ):
        raise StandardsError("standards-release must be a semantic version such as 1.0.0")

    profiles = manifest.get("profiles")
    if not isinstance(profiles, list) or not profiles or not all(
        isinstance(item, str) and item for item in profiles
    ):
        raise StandardsError("profiles must be a non-empty list of names")
    if len(profiles) != len(set(profiles)):
        raise StandardsError("profiles must not contain duplicates")

    boundaries = manifest.get("boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        raise StandardsError("boundaries must be a non-empty list")
    normalized_boundaries: list[dict[str, str]] = []
    boundary_declarations: set[tuple[str, str, str]] = set()
    for index, boundary in enumerate(boundaries):
        field = f"boundaries[{index}]"
        if not isinstance(boundary, dict):
            raise StandardsError(f"{field} must be an object")
        unknown_boundary_fields = sorted(set(boundary) - {"path", "type", "title"})
        if unknown_boundary_fields:
            raise StandardsError(
                f"{field} has unknown fields: {', '.join(unknown_boundary_fields)}"
            )
        path_value = _boundary_path(boundary.get("path"), f"{field}.path")
        boundary_type = boundary.get("type")
        if boundary_type not in {"repository", "collection", "project"}:
            raise StandardsError(
                f"{field}.type must be repository, collection, or project"
            )
        title = boundary.get("title")
        if not isinstance(title, str) or not title.strip():
            raise StandardsError(f"{field}.title must be a non-empty string")
        declaration = (path_value, boundary_type, title)
        if declaration in boundary_declarations:
            raise StandardsError("boundaries must not contain duplicate declarations")
        boundary_declarations.add(declaration)
        normalized_boundaries.append(
            {"path": path_value, "type": boundary_type, "title": title}
        )

    repository_boundaries = [
        boundary
        for boundary in normalized_boundaries
        if boundary["type"] == "repository"
    ]
    if len(repository_boundaries) != 1 or repository_boundaries[0]["path"] != ".":
        raise StandardsError(
            "boundaries must contain exactly one repository boundary at '.'"
        )
    if "common" not in profiles:
        raise StandardsError(
            "standards-version 5 workflow requires the common profile"
        )
    if "documentation" not in profiles:
        raise StandardsError("standards-version 5 boundaries require the documentation profile")

    dependency_updates = manifest.get("dependency-updates")
    if not isinstance(dependency_updates, list) or not dependency_updates:
        raise StandardsError("dependency-updates must be a non-empty list")
    normalized_updates: list[dict[str, str]] = []
    update_declarations: set[tuple[str, str, str]] = set()
    for index, update in enumerate(dependency_updates):
        field = f"dependency-updates[{index}]"
        if not isinstance(update, dict):
            raise StandardsError(f"{field} must be an object")
        unknown_update_fields = sorted(
            set(update) - {"ecosystem", "directory", "schedule"}
        )
        if unknown_update_fields:
            raise StandardsError(
                f"{field} has unknown fields: {', '.join(unknown_update_fields)}"
            )
        ecosystem = update.get("ecosystem")
        if ecosystem not in DEPENDENCY_ECOSYSTEMS:
            raise StandardsError(
                f"{field}.ecosystem must be github-actions, maven, or npm"
            )
        directory = update.get("directory")
        if not isinstance(directory, str) or not re.fullmatch(
            r"/(?:[^/]+(?:/[^/]+)*)?", directory
        ):
            raise StandardsError(
                f"{field}.directory must be an absolute repository directory"
            )
        if any(part in {".", ".."} for part in directory.removeprefix("/").split("/")):
            raise StandardsError(f"{field}.directory must not contain dot segments")
        schedule = update.get("schedule")
        if schedule not in DEPENDENCY_INTERVALS:
            raise StandardsError(f"{field}.schedule must be daily, weekly, or monthly")
        declaration = (ecosystem, directory, schedule)
        if declaration in update_declarations:
            raise StandardsError(
                "dependency-updates must not contain duplicate declarations"
            )
        update_declarations.add(declaration)
        normalized_updates.append(
            {"ecosystem": ecosystem, "directory": directory, "schedule": schedule}
        )

    github = manifest.get("github")
    if github is None:
        raise StandardsError("standards-version 5 github contract is required")
    if github is not None:
        if not isinstance(github, dict):
            raise StandardsError("github must be an object")
        required_github_fields = {
            "repository",
            "default-branch",
            "settings",
            "ruleset",
        }
        if set(github) != required_github_fields:
            raise StandardsError(
                "github must define repository, default-branch, settings, and ruleset"
            )
        repository_name = github.get("repository")
        if not isinstance(repository_name, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository_name
        ):
            raise StandardsError("github.repository must be an owner/repository name")
        default_branch = github.get("default-branch")
        if not isinstance(default_branch, str) or not default_branch:
            raise StandardsError("github.default-branch must be a non-empty string")
        settings = github.get("settings")
        required_settings = {
            "delete-branch-on-merge",
            "allow-squash-merge",
            "allow-merge-commit",
            "allow-rebase-merge",
        }
        if not isinstance(settings, dict) or set(settings) != required_settings:
            raise StandardsError(
                "github.settings must define delete-branch-on-merge, "
                "allow-squash-merge, allow-merge-commit, and allow-rebase-merge"
            )
        if not all(isinstance(value, bool) for value in settings.values()):
            raise StandardsError("github.settings values must be booleans")
        ruleset = github.get("ruleset")
        if ruleset is not None:
            required_ruleset = {
                "name",
                "required-status-checks",
                "require-current-branch",
                "required-approvals",
                "allowed-merge-methods",
                "prevent-deletion",
                "prevent-force-push",
                "allow-bypass-actors",
            }
            if not isinstance(ruleset, dict) or set(ruleset) != required_ruleset:
                raise StandardsError(
                    "github.ruleset must define the complete branch-protection contract"
                )
            if not isinstance(ruleset["name"], str) or not ruleset["name"]:
                raise StandardsError("github.ruleset.name must be a non-empty string")
            checks = ruleset["required-status-checks"]
            if (
                not isinstance(checks, list)
                or not checks
                or not all(isinstance(check, str) and check for check in checks)
                or len(checks) != len(set(checks))
            ):
                raise StandardsError(
                    "github.ruleset.required-status-checks must be a non-empty unique list"
                )
            approvals = ruleset["required-approvals"]
            if not isinstance(approvals, int) or isinstance(approvals, bool) or approvals < 0:
                raise StandardsError(
                    "github.ruleset.required-approvals must be a non-negative integer"
                )
            merge_methods = ruleset["allowed-merge-methods"]
            if (
                not isinstance(merge_methods, list)
                or not merge_methods
                or not all(
                    method in {"merge", "rebase", "squash"}
                    for method in merge_methods
                )
                or len(merge_methods) != len(set(merge_methods))
            ):
                raise StandardsError(
                    "github.ruleset.allowed-merge-methods must be a non-empty unique list"
                )
            boolean_rules = {
                "require-current-branch",
                "prevent-deletion",
                "prevent-force-push",
                "allow-bypass-actors",
            }
            if not all(isinstance(ruleset[key], bool) for key in boolean_rules):
                raise StandardsError("github.ruleset boolean fields must be booleans")
            if ruleset["allow-bypass-actors"]:
                raise StandardsError(
                    "standards-version 5 does not support bypass actors; "
                    "set allow-bypass-actors to false before adopting this contract"
                )

    variables = manifest.get("variables", {})
    if not isinstance(variables, dict) or not all(
        isinstance(key, str) and isinstance(value, (str, int, float, bool))
        for key, value in variables.items()
    ):
        raise StandardsError("variables must map names to scalar values")

    local_fragments = manifest.get("local-fragments", {})
    if not isinstance(local_fragments, dict):
        raise StandardsError("local-fragments must be an object")
    normalized_fragments: dict[str, list[str]] = {}
    for raw_target, raw_sources in local_fragments.items():
        target = _relative_path(raw_target, "local-fragments target")
        if not isinstance(raw_sources, list) or not all(
            isinstance(item, str) for item in raw_sources
        ):
            raise StandardsError(f"local-fragments[{target!r}] must be a list")
        if len(raw_sources) != len(set(raw_sources)):
            raise StandardsError(
                f"local-fragments[{target!r}] must not contain duplicates"
            )
        normalized_fragments[target] = [
            _relative_path(item, f"local-fragments[{target!r}]") for item in raw_sources
        ]

    repository_owned = manifest.get("repository-owned")
    if not isinstance(repository_owned, list) or not all(
        isinstance(item, str) and item for item in repository_owned
    ):
        raise StandardsError("repository-owned must be a list of path patterns")
    if len(repository_owned) != len(set(repository_owned)):
        raise StandardsError("repository-owned must not contain duplicates")
    for pattern in repository_owned:
        _relative_path(pattern, "repository-owned pattern")

    manifest["local-fragments"] = normalized_fragments
    manifest["variables"] = variables
    manifest["boundaries"] = normalized_boundaries
    manifest["dependency-updates"] = normalized_updates
    return path, manifest


def _load_profile(
    root: Path,
    name: str,
    ordered: list[tuple[str, dict[str, Any], Path]],
    loaded: set[str],
    visiting: set[str],
) -> None:
    if name in loaded:
        return
    if name in visiting:
        raise StandardsError(f"profile inheritance cycle at {name!r}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise StandardsError(f"invalid profile name: {name!r}")

    profile_dir = root / "profiles" / name
    path = profile_dir / "profile.json"
    if not path.is_file():
        raise StandardsError(f"unknown profile: {name!r}")
    data = _read_data(path)
    if data.get("name") != name:
        raise StandardsError(f"{path}: name must be {name!r}")
    unknown = sorted(
        set(data)
        - {"name", "description", "extends", "applicability", "files", "github"}
    )
    if unknown:
        raise StandardsError(f"{path}: unknown fields: {', '.join(unknown)}")
    parents = data.get("extends", [])
    if not isinstance(parents, list) or not all(isinstance(item, str) for item in parents):
        raise StandardsError(f"{path}: extends must be a list")
    if len(parents) != len(set(parents)):
        raise StandardsError(f"{path}: extends must not contain duplicates")
    applicability = data.get("applicability")
    if applicability is not None and not isinstance(applicability, dict):
        raise StandardsError(f"{path}: applicability must be an object")
    github = data.get("github", {})
    if not isinstance(github, dict) or set(github) - {"required-labels"}:
        raise StandardsError(
            f"{path}: github must contain only required-labels"
        )
    required_labels = github.get("required-labels", [])
    if (
        not isinstance(required_labels, list)
        or not all(isinstance(label, str) and label for label in required_labels)
        or len(required_labels) != len(set(required_labels))
    ):
        raise StandardsError(
            f"{path}: github.required-labels must be a unique list of names"
        )

    visiting.add(name)
    for parent in parents:
        _load_profile(root, parent, ordered, loaded, visiting)
    visiting.remove(name)
    loaded.add(name)
    ordered.append((name, data, profile_dir))


def _load_profiles(root: Path, selected: Iterable[str]) -> list[tuple[str, dict[str, Any], Path]]:
    ordered: list[tuple[str, dict[str, Any], Path]] = []
    loaded: set[str] = set()
    for name in selected:
        _load_profile(root, name, ordered, loaded, set())
    return ordered


def _collect_required_labels(
    profiles: Iterable[tuple[str, dict[str, Any], Path]],
) -> tuple[str, ...]:
    labels = {
        label
        for _, data, _ in profiles
        for label in data.get("github", {}).get("required-labels", [])
    }
    return tuple(sorted(labels))


def _collect_sources(
    profiles: list[tuple[str, dict[str, Any], Path]]
) -> dict[str, list[Source]]:
    targets: dict[str, list[Source]] = {}
    for profile_index, (name, data, profile_dir) in enumerate(profiles):
        files = data.get("files", [])
        if not isinstance(files, list):
            raise StandardsError(f"profile {name!r}: files must be a list")
        for item in files:
            if not isinstance(item, dict):
                raise StandardsError(f"profile {name!r}: file declarations must be objects")
            unknown = sorted(set(item) - {"mode", "source", "target", "order"})
            if unknown:
                raise StandardsError(
                    f"profile {name!r}: unknown file fields: {', '.join(unknown)}"
                )
            mode = item.get("mode")
            if mode not in {"exact", "template", "compose", "absent", "tree"}:
                raise StandardsError(f"profile {name!r}: invalid file mode {mode!r}")
            target = _relative_path(item.get("target"), f"profile {name} target")
            order = item.get("order", 0)
            if not isinstance(order, int):
                raise StandardsError(f"profile {name!r}: order must be an integer")
            if mode == "absent":
                if "source" in item or "order" in item:
                    raise StandardsError(
                        f"profile {name!r}: absent files define only mode and target"
                    )
                source = None
            else:
                source_value = _relative_path(
                    item.get("source"), f"profile {name} source"
                )
                source_candidate = profile_dir
                if mode == "tree":
                    for part in PurePosixPath(source_value).parts:
                        source_candidate /= part
                        if source_candidate.is_symlink():
                            raise StandardsError(
                                f"profile {name!r}: tree source must not be a symlink: "
                                f"{source_value}"
                            )
                else:
                    source_candidate /= source_value
                source = source_candidate.resolve()
                try:
                    source.relative_to(profile_dir.resolve())
                except ValueError as exc:
                    raise StandardsError(
                        f"profile {name!r}: source escapes profile"
                    ) from exc
                if mode == "tree":
                    if "order" in item:
                        raise StandardsError(
                            f"profile {name!r}: tree files define only mode, source, and target"
                        )
                    if not source.is_dir():
                        raise StandardsError(
                            f"profile {name!r}: tree source not found: {source_value}"
                        )
                    tree_entries = sorted(source.rglob("*"))
                    if not tree_entries:
                        raise StandardsError(
                            f"profile {name!r}: tree source is empty: {source_value}"
                        )
                    managed_files = 0
                    for tree_file in tree_entries:
                        if tree_file.is_symlink():
                            raise StandardsError(
                                f"profile {name!r}: tree source contains a symlink: "
                                f"{tree_file.relative_to(source).as_posix()}"
                            )
                        if tree_file.is_dir():
                            continue
                        if not tree_file.is_file():
                            raise StandardsError(
                                f"profile {name!r}: tree source contains a non-file: "
                                f"{tree_file.relative_to(source).as_posix()}"
                            )
                        relative = tree_file.relative_to(source).as_posix()
                        tree_target = (PurePosixPath(target) / relative).as_posix()
                        targets.setdefault(tree_target, []).append(
                            Source(
                                "exact",
                                tree_file,
                                tree_target,
                                0,
                                name,
                                profile_index,
                            )
                        )
                        managed_files += 1
                    if not managed_files:
                        raise StandardsError(
                            f"profile {name!r}: tree source has no files: {source_value}"
                        )
                    continue
                if not source.is_file():
                    raise StandardsError(
                        f"profile {name!r}: source not found: {source_value}"
                    )
            targets.setdefault(target, []).append(
                Source(mode, source, target, order, name, profile_index)
            )

    for target, sources in targets.items():
        modes = {source.mode for source in sources}
        if modes == {"compose"}:
            continue
        if len(sources) > 1 or len(modes) > 1:
            origins = ", ".join(source.profile for source in sources)
            raise StandardsError(f"conflicting managed target {target!r}: {origins}")
    return targets


def _render_template(source: Source, variables: dict[str, Any]) -> bytes:
    if source.path is None:
        raise StandardsError("absent files cannot be rendered as templates")
    try:
        template = source.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise StandardsError(f"cannot read template {source.path}: {exc}") from exc
    missing = sorted(set(VARIABLE_PATTERN.findall(template)) - set(variables))
    if missing:
        raise StandardsError(
            f"template {source.path} is missing variables: {', '.join(missing)}"
        )
    rendered = VARIABLE_PATTERN.sub(lambda match: str(variables[match.group(1)]), template)
    remaining = VARIABLE_PATTERN.findall(rendered)
    if remaining:
        raise StandardsError(f"unresolved variables in {source.path}")
    return rendered.encode("utf-8")


def _join_fragments(parts: list[bytes], target: str) -> bytes:
    decoded: list[str] = []
    for part in parts:
        try:
            decoded.append(part.decode("utf-8").strip("\n"))
        except UnicodeDecodeError as exc:
            raise StandardsError(f"compose target {target!r} must use UTF-8 fragments") from exc
    return ("\n\n".join(value for value in decoded if value) + "\n").encode("utf-8")


def _matches_owned(target: str, patterns: Iterable[str]) -> str | None:
    for pattern in patterns:
        if fnmatch.fnmatchcase(target, pattern):
            return pattern
    return None


def _render_dependabot(updates: list[dict[str, str]]) -> bytes:
    lines = ["version: 2", "updates:"]
    for update in updates:
        lines.extend(
            [
                f"  - package-ecosystem: {update['ecosystem']}",
                f"    directory: {update['directory']}",
                "    schedule:",
                f"      interval: {update['schedule']}",
                "    commit-message:",
                "      prefix: chore",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _build_plan_with_blockers(
    root: Path,
    repository: Path,
    manifest: dict[str, Any],
    *,
    resolved_profiles: list[tuple[str, dict[str, Any], Path]] | None = None,
) -> tuple[list[PlannedFile], list[PlanBuildBlocker]]:
    root = root.resolve()
    repository = repository.resolve()
    version_path = root / "VERSION"
    try:
        source_release = version_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise StandardsError(f"cannot read standards release from {version_path}: {exc}") from exc
    if manifest["standards-release"] != source_release:
        raise StandardsError(
            f"manifest requires standards release {manifest['standards-release']}, "
            f"but this checkout is {source_release}; check out tag "
            f"v{manifest['standards-release']} or update the manifest deliberately"
        )
    profiles = (
        resolved_profiles
        if resolved_profiles is not None
        else _load_profiles(root, manifest["profiles"])
    )
    sources_by_target = _collect_sources(profiles)
    local_fragments: dict[str, list[str]] = manifest["local-fragments"]

    compose_targets = {
        target
        for target, sources in sources_by_target.items()
        if sources[0].mode == "compose"
    }
    unknown_fragment_targets = sorted(set(local_fragments) - compose_targets)
    blockers = [
        PlanBuildBlocker(
            target,
            "local fragments require a managed compose target",
        )
        for target in unknown_fragment_targets
    ]

    planned: list[PlannedFile] = []
    for target in sorted(sources_by_target):
        owned_pattern = _matches_owned(target, manifest["repository-owned"])
        if owned_pattern:
            blockers.append(
                PlanBuildBlocker(
                    target,
                    f"managed target conflicts with repository-owned pattern "
                    f"{owned_pattern!r}",
                )
            )
        sources = sources_by_target[target]
        origins = [
            f"{source.profile}:{source.path.name if source.path else 'absence'}"
            for source in sources
        ]
        content = b""
        try:
            if sources[0].mode == "absent":
                pass
            elif sources[0].mode == "exact":
                assert sources[0].path is not None
                content = sources[0].path.read_bytes()
            elif sources[0].mode == "template":
                content = _render_template(sources[0], manifest["variables"])
            else:
                sources = sorted(
                    sources, key=lambda item: (item.order, item.profile_index)
                )
                assert all(source.path is not None for source in sources)
                parts = [source.path.read_bytes() for source in sources]
                origins = [
                    f"{source.profile}:{source.path.name}"
                    for source in sources
                    if source.path is not None
                ]
                for local_value in local_fragments.get(target, []):
                    local_path = (repository / local_value).resolve()
                    try:
                        local_path.relative_to(repository)
                    except ValueError as exc:
                        raise StandardsError(
                            f"local fragment escapes repository: {local_value}"
                        ) from exc
                    if not local_path.is_file():
                        raise StandardsError(f"local fragment not found: {local_value}")
                    parts.append(local_path.read_bytes())
                    origins.append(f"repository:{local_value}")
                content = _join_fragments(parts, target)
        except (OSError, StandardsError) as exc:
            blockers.append(PlanBuildBlocker(target, str(exc)))
        planned.append(
            PlannedFile(target, sources[0].mode, content, tuple(origins))
        )
    dependabot_target = ".github/dependabot.yml"
    if dependabot_target in sources_by_target:
        blockers.append(
            PlanBuildBlocker(
                dependabot_target,
                "profiles must not manage this generated dependency-update target",
            )
        )
    owned_pattern = _matches_owned(dependabot_target, manifest["repository-owned"])
    if owned_pattern:
        blockers.append(
            PlanBuildBlocker(
                dependabot_target,
                f"managed target conflicts with repository-owned pattern "
                f"{owned_pattern!r}",
            )
        )
    planned.append(
        PlannedFile(
            dependabot_target,
            "generated",
            _render_dependabot(manifest["dependency-updates"]),
            ("manifest:dependency-updates",),
        )
    )
    return (
        sorted(planned, key=lambda item: item.target),
        sorted(blockers, key=lambda item: (item.target, item.message)),
    )


def _validate_managed_target(repository: Path, target: Path, relative: str) -> None:
    ancestor = repository
    for part in target.relative_to(repository).parts[:-1]:
        ancestor /= part
        if ancestor.is_symlink():
            raise StandardsError(
                f"managed target ancestor must not be a symlink: {relative}"
            )
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(repository)
    except ValueError as exc:
        raise StandardsError(
            f"managed target escapes through a symlink: {relative}"
        ) from exc
    if target.is_symlink():
        raise StandardsError(f"managed target must not be a symlink: {relative}")


def inspect(repository: Path, plan: Iterable[PlannedFile]) -> list[Result]:
    repository = repository.resolve()
    results: list[Result] = []
    for item in plan:
        target = repository / item.target
        _validate_managed_target(repository, target, item.target)
        if item.mode == "absent":
            if not target.exists():
                results.append(
                    Result(item.target, "ok", item.mode, b"", None, item.origins)
                )
            elif not target.is_file():
                results.append(
                    Result(
                        item.target,
                        "not-file",
                        item.mode,
                        b"",
                        None,
                        item.origins,
                    )
                )
            else:
                try:
                    actual = target.read_bytes()
                except OSError as exc:
                    raise StandardsError(
                        f"cannot read managed target {item.target}: {exc}"
                    ) from exc
                results.append(
                    Result(
                        item.target,
                        "present",
                        item.mode,
                        b"",
                        actual,
                        item.origins,
                    )
                )
        elif not target.exists():
            results.append(
                Result(
                    item.target,
                    "missing",
                    item.mode,
                    item.content,
                    None,
                    item.origins,
                )
            )
        elif not target.is_file():
            results.append(
                Result(
                    item.target,
                    "not-file",
                    item.mode,
                    item.content,
                    None,
                    item.origins,
                )
            )
        else:
            try:
                actual = target.read_bytes()
            except OSError as exc:
                raise StandardsError(f"cannot read managed target {item.target}: {exc}") from exc
            status = "ok" if actual == item.content else "drift"
            results.append(
                Result(
                    item.target,
                    status,
                    item.mode,
                    item.content,
                    actual,
                    item.origins,
                )
            )
    return results


def _boundary_target(boundary_path: str, child: str) -> str:
    if boundary_path == ".":
        return child
    return (PurePosixPath(boundary_path) / child).as_posix()


def _read_boundary_text(repository: Path, relative_path: str) -> tuple[str | None, str | None]:
    target = repository / relative_path
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(repository)
    except ValueError:
        return None, f"{relative_path} escapes the repository through a symlink"
    if target.is_symlink():
        return None, f"{relative_path} must not be a symlink"
    if not target.exists():
        return None, f"{relative_path} is missing"
    if not target.is_file():
        return None, f"{relative_path} is not a regular file"
    try:
        return target.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        return None, f"{relative_path} is not valid UTF-8"
    except OSError as exc:
        return None, f"cannot read {relative_path}: {exc}"


def _check_root_readme(text: str, title: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0] != '<div align="center">':
        errors.append('README.md must begin with <div align="center">')
    closing_index = text.find("</div>")
    if closing_index < 0:
        errors.append("README.md centered header must end with </div>")
        header = text
    else:
        header = text[:closing_index]
    expected_h1 = f"<h1>{html.escape(title, quote=False)}</h1>"
    expected_h1_line = f"  {expected_h1}"
    html_h1s = HTML_H1_PATTERN.findall(text)
    if (
        html_h1s != [expected_h1]
        or expected_h1_line not in header.splitlines()
    ):
        errors.append(
            f"README.md must contain exactly one canonical centered header title: "
            f"{expected_h1_line}"
        )
    return errors


def _check_internal_readme(text: str, relative_path: str, title: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    expected_h1 = f"# {title}"
    if not lines or lines[0] != expected_h1:
        errors.append(f"{relative_path} must begin with {expected_h1!r}")
    markdown_h1s = MARKDOWN_H1_PATTERN.findall(text)
    if markdown_h1s != [title]:
        errors.append(f"{relative_path} must contain exactly one Markdown H1: {expected_h1}")
    if CENTERED_WRAPPER_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain a centered wrapper")
    if HTML_H1_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain an HTML H1")
    if BADGE_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain badges")
    return errors


def _check_docs_readme(text: str, relative_path: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0] != "# Documentation":
        errors.append(f"{relative_path} must begin with '# Documentation'")
    markdown_h1s = MARKDOWN_H1_PATTERN.findall(text)
    if markdown_h1s != ["Documentation"]:
        errors.append(
            f"{relative_path} must contain exactly one Markdown H1: # Documentation"
        )
    if CENTERED_WRAPPER_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain a centered wrapper")
    if HTML_H1_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain an HTML H1")
    if BADGE_PATTERN.search(text):
        errors.append(f"{relative_path} must not contain badges")
    return errors


def _check_empty_documentation_categories(
    repository: Path, boundary_path: str
) -> list[str]:
    errors: list[str] = []
    docs_root = repository / _boundary_target(boundary_path, "docs")
    for category in DIATAXIS_CATEGORIES:
        category_path = docs_root / category
        if not category_path.is_dir():
            continue
        authored_files = [
            candidate
            for candidate in category_path.rglob("*")
            if candidate.is_file()
            and candidate.relative_to(category_path).as_posix() != "README.md"
        ]
        if not authored_files:
            relative_category = category_path.relative_to(repository).as_posix()
            errors.append(
                f"{relative_category} has no authored content; remove it until needed"
            )
    return errors


def inspect_boundaries(
    repository: Path, boundaries: Iterable[dict[str, str] | RepositoryBoundary]
) -> list[BoundaryResult]:
    repository = repository.resolve()
    results: list[BoundaryResult] = []
    for boundary in boundaries:
        if isinstance(boundary, RepositoryBoundary):
            boundary_path = boundary.path
            boundary_type = boundary.boundary_type
            title = boundary.title
        else:
            boundary_path = boundary["path"]
            boundary_type = boundary["type"]
            title = boundary["title"]
        messages: list[str] = []

        readme_path = _boundary_target(boundary_path, "README.md")
        readme_text, readme_error = _read_boundary_text(repository, readme_path)
        if readme_error:
            messages.append(readme_error)
        elif boundary_type == "repository":
            messages.extend(_check_root_readme(readme_text or "", title))
        else:
            messages.extend(_check_internal_readme(readme_text or "", readme_path, title))

        if boundary_type in {"repository", "project"}:
            docs_path = _boundary_target(boundary_path, "docs/README.md")
            docs_text, docs_error = _read_boundary_text(repository, docs_path)
            if docs_error:
                messages.append(docs_error)
            else:
                messages.extend(_check_docs_readme(docs_text or "", docs_path))
            if readme_text is not None and not DOCS_LINK_PATTERN.search(readme_text):
                messages.append(f"{readme_path} must link to docs/README.md")
            messages.extend(
                _check_empty_documentation_categories(repository, boundary_path)
            )

        if boundary_type == "project":
            templates_path = _boundary_target(boundary_path, "docs/_templates")
            if (repository / templates_path).exists() or (repository / templates_path).is_symlink():
                messages.append(
                    f"{templates_path} must not exist; templates are managed only at docs/_templates"
                )

        results.append(
            BoundaryResult(
                boundary_path,
                boundary_type,
                "invalid" if messages else "ok",
                tuple(messages),
            )
        )
    return results


def inspect_repository_owned_documents(
    repository: Path, repository_owned: Iterable[str]
) -> list[DocumentResult]:
    if "CHANGELOG.md" not in repository_owned:
        return []
    try:
        validate_changelog(repository / "CHANGELOG.md")
    except ChangelogError as exc:
        return [DocumentResult("CHANGELOG.md", "invalid", (str(exc),))]
    return [DocumentResult("CHANGELOG.md", "ok", ())]


def _preview_text(result: Result) -> str:
    if result.mode == "absent":
        if result.status == "not-file":
            return (
                f"BLOCKED  {result.target} "
                "(managed absence requires a regular file)\n"
            )
        deletion = f"DELETE   {result.target}\n"
        if not result.actual:
            return deletion
        try:
            actual_text = result.actual.decode("utf-8")
        except UnicodeDecodeError:
            return deletion
        return deletion + "".join(
            difflib.unified_diff(
                actual_text.splitlines(keepends=True),
                [],
                fromfile=f"a/{result.target}",
                tofile=f"b/{result.target}",
            )
        )

    if result.actual is None:
        actual_text = ""
    else:
        try:
            actual_text = result.actual.decode("utf-8")
        except UnicodeDecodeError:
            return f"Binary content differs for {result.target}\n"
    try:
        expected_text = result.expected.decode("utf-8")
    except UnicodeDecodeError:
        return f"Binary content differs for {result.target}\n"
    return "".join(
        difflib.unified_diff(
            actual_text.splitlines(keepends=True),
            expected_text.splitlines(keepends=True),
            fromfile=f"a/{result.target}",
            tofile=f"b/{result.target}",
        )
    )


def write(repository: Path, results: Iterable[Result]) -> int:
    repository = repository.resolve()
    changed = 0
    for result in results:
        if result.status == "ok":
            continue
        target = repository / result.target
        _validate_managed_target(repository, target, result.target)
        if target.exists() and not target.is_file():
            raise StandardsError(f"managed target is not a file: {result.target}")
        try:
            if result.mode == "absent":
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(result.expected)
        except OSError as exc:
            raise StandardsError(f"cannot write managed target {result.target}: {exc}") from exc
        changed += 1
    return changed


def _resolve(
    repository_value: str, manifest_value: str | None
) -> tuple[RepositoryContract, list[Result]]:
    repository = Path(repository_value).expanduser().resolve()
    contract = resolve_repository_contract(
        repository,
        standards_root=standards_root(),
        manifest=manifest_value,
    )
    return contract, inspect(repository, contract.managed_files)


def audit_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit managed repository standards")
    parser.add_argument("repository", help="repository to audit")
    parser.add_argument("--manifest", help="manifest path, relative to repository")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        contract, results = _resolve(args.repository, args.manifest)
    except (StandardsError, ContractError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    repository = contract.repository
    drift = [result for result in results if result.status != "ok"]
    boundary_results = inspect_boundaries(repository, contract.boundaries)
    invalid_boundaries = [
        result for result in boundary_results if result.status != "ok"
    ]
    document_results = inspect_repository_owned_documents(
        repository, contract.repository_owned
    )
    invalid_documents = [
        result for result in document_results if result.status != "ok"
    ]
    if args.json_output:
        print(
            json.dumps(
                {
                    "repository": str(repository),
                    "standards-version": contract.protocol,
                    "standards-release": contract.release,
                    "profiles": list(contract.selected_profiles),
                    "clean": not drift and not invalid_boundaries and not invalid_documents,
                    "files": [
                        {
                            "path": result.target,
                            "status": result.status,
                            "mode": result.mode,
                            "origins": list(result.origins),
                        }
                        for result in results
                    ],
                    "boundaries": [
                        {
                            "path": result.path,
                            "type": result.boundary_type,
                            "status": result.status,
                            "messages": list(result.messages),
                        }
                        for result in boundary_results
                    ],
                    "documents": [
                        {
                            "path": result.path,
                            "status": result.status,
                            "messages": list(result.messages),
                        }
                        for result in document_results
                    ],
                },
                indent=2,
            )
        )
    else:
        for result in results:
            marker = "OK" if result.status == "ok" else result.status.upper()
            print(f"{marker:8} {result.target}")
        print(f"\n{len(results) - len(drift)} clean, {len(drift)} requiring synchronization")
        print()
        for result in boundary_results:
            marker = "OK" if result.status == "ok" else result.status.upper()
            print(f"{marker:8} boundary {result.path} ({result.boundary_type})")
            for message in result.messages:
                print(f"         - {message}")
        print(
            f"\n{len(boundary_results) - len(invalid_boundaries)} conforming, "
            f"{len(invalid_boundaries)} invalid boundaries"
        )
        if document_results:
            print()
            for result in document_results:
                marker = "OK" if result.status == "ok" else result.status.upper()
                print(f"{marker:8} document {result.path}")
                for message in result.messages:
                    print(f"         - {message}")
            print(
                f"\n{len(document_results) - len(invalid_documents)} conforming, "
                f"{len(invalid_documents)} invalid repository-owned documents"
            )
    return 1 if drift or invalid_boundaries or invalid_documents else 0


def sync_main(argv: list[str] | None = None) -> int:
    from .offline_sync import (
        apply_synchronization_plan,
        plan_synchronization,
        render_synchronization_preview,
    )

    parser = argparse.ArgumentParser(description="Preview or write managed repository standards")
    parser.add_argument("repository", help="repository to synchronize")
    parser.add_argument("--manifest", help="manifest path, relative to repository")
    parser.add_argument("--write", action="store_true", help="write managed targets")
    args = parser.parse_args(argv)
    try:
        contract = resolve_repository_contract(
            Path(args.repository),
            standards_root=standards_root(),
            manifest=args.manifest,
            retain_plan_blockers=True,
        )
        repository = contract.repository
        plan = plan_synchronization(contract)
        preview = render_synchronization_preview(plan)
        changes = plan.changes
        if args.write:
            if plan.blockers:
                print(preview, end="")
                print(
                    f"\nPreflight blocked: {len(plan.blockers)} managed path(s) "
                    "require attention. No target was mutated."
                )
                return 2
            report = apply_synchronization_plan(plan)
            if not report.succeeded:
                assert report.failed is not None
                print(
                    f"error: application failed at {report.failed.target}: "
                    f"{report.failed.message}",
                    file=sys.stderr,
                )
                print(
                    "Completed: " + (", ".join(report.completed) or "none"),
                    file=sys.stderr,
                )
                print(f"Failed: {report.failed.target}", file=sys.stderr)
                print(
                    "Remaining: " + (", ".join(report.remaining) or "none"),
                    file=sys.stderr,
                )
                return 2
            print(f"Synchronized {len(report.completed)} managed file(s) in {repository}")
            return 0
        if not changes and not plan.blockers:
            print(f"All managed files are current in {repository}")
            return 0
        print(preview, end="")
        if plan.blockers:
            if changes:
                print(
                    f"\nPreview: {len(changes)} managed file(s) would change; "
                    f"{len(plan.blockers)} blocked path(s) require attention."
                )
            else:
                print(
                    f"\nPreview blocked: {len(plan.blockers)} managed path(s) "
                    "require attention."
                )
            return 2
        print(f"\nPreview: {len(changes)} managed file(s) would change. Re-run with --write.")
        return 1
    except (StandardsError, ContractError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
