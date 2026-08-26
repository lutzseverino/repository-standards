"""Resolve repository declarations into one normalized repository contract."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


DEFAULT_SQUASH_MERGE_COMMIT_TITLE = "PR_TITLE"
DEFAULT_SQUASH_MERGE_COMMIT_MESSAGE = "PR_BODY"
DEFAULT_GITHUB_FEATURES = {
    "issues": True,
    "projects": False,
    "wiki": False,
}


def _default_main_ruleset() -> dict[str, Any]:
    return {
        "name": "Protect main",
        "required-status-checks": ["CI / Required"],
        "require-current-branch": True,
        "required-approvals": 0,
        "allowed-merge-methods": ["squash"],
        "prevent-deletion": True,
        "prevent-force-push": True,
        "allow-bypass-actors": False,
    }


class ContractError(Exception):
    """Raised when a repository contract cannot be validated and normalized."""


MANDATORY_INITIAL_PROFILES = ("common", "documentation")
DEFAULT_INITIAL_REPOSITORY_OWNED = (
    "README.md",
    "LICENSE",
    "CONTEXT.md",
    "docs/README.md",
    "docs/agents/domain.md",
    "docs/adr/**",
    "docs/how-to/**",
)


@dataclass(frozen=True)
class ResolvedProfile:
    name: str
    description: str
    applicability: tuple[tuple[str, Any], ...] | None


@dataclass(frozen=True)
class ManagedFile:
    target: str
    mode: str
    content: bytes
    origins: tuple[str, ...]


@dataclass(frozen=True)
class ContractBlocker:
    target: str
    message: str


@dataclass(frozen=True)
class DependencyUpdate:
    ecosystem: str
    directory: str
    schedule: str


@dataclass(frozen=True)
class RepositoryBoundary:
    path: str
    boundary_type: str
    title: str


@dataclass(frozen=True)
class CanonicalValidation:
    executable: str
    arguments: tuple[str, ...]
    working_directory: str = "."

    def as_mapping(self) -> dict[str, Any]:
        return {
            "executable": self.executable,
            "arguments": list(self.arguments),
            "working-directory": self.working_directory,
        }


@dataclass(frozen=True)
class GitHubSettings:
    delete_branch_on_merge: bool
    allow_squash_merge: bool
    allow_merge_commit: bool
    allow_rebase_merge: bool
    squash_merge_commit_title: str = DEFAULT_SQUASH_MERGE_COMMIT_TITLE
    squash_merge_commit_message: str = DEFAULT_SQUASH_MERGE_COMMIT_MESSAGE


@dataclass(frozen=True)
class GitHubFeatures:
    issues: bool = DEFAULT_GITHUB_FEATURES["issues"]
    projects: bool = DEFAULT_GITHUB_FEATURES["projects"]
    wiki: bool = DEFAULT_GITHUB_FEATURES["wiki"]


@dataclass(frozen=True)
class GitHubContract:
    repository: str
    default_branch: str
    settings: GitHubSettings
    ruleset: tuple[tuple[str, Any], ...] | None
    features: GitHubFeatures = field(default_factory=GitHubFeatures)

    def as_mapping(self) -> dict[str, Any]:
        """Return the normalized shape expected by GitHub reconciliation internals."""

        return {
            "repository": self.repository,
            "default-branch": self.default_branch,
            "settings": {
                "delete-branch-on-merge": self.settings.delete_branch_on_merge,
                "allow-squash-merge": self.settings.allow_squash_merge,
                "allow-merge-commit": self.settings.allow_merge_commit,
                "allow-rebase-merge": self.settings.allow_rebase_merge,
                "squash-merge-commit-title": (
                    self.settings.squash_merge_commit_title
                ),
                "squash-merge-commit-message": (
                    self.settings.squash_merge_commit_message
                ),
            },
            "features": {
                "issues": self.features.issues,
                "projects": self.features.projects,
                "wiki": self.features.wiki,
            },
            "ruleset": _thaw_value(self.ruleset),
        }


@dataclass(frozen=True)
class RepositoryContract:
    """Validated repository knowledge consumed by lifecycle operations."""

    repository: Path
    manifest_path: Path
    standards_root: Path
    protocol: int
    release: str
    selected_profiles: tuple[str, ...]
    profiles: tuple[ResolvedProfile, ...]
    managed_files: tuple[ManagedFile, ...]
    managed_paths: tuple[str, ...]
    managed_absences: tuple[str, ...]
    repository_owned: tuple[str, ...]
    variables: tuple[tuple[str, Any], ...]
    local_fragments: tuple[tuple[str, tuple[str, ...]], ...]
    required_labels: tuple[str, ...]
    dependency_updates: tuple[DependencyUpdate, ...]
    boundaries: tuple[RepositoryBoundary, ...]
    canonical_validation: CanonicalValidation
    github: GitHubContract
    content_blockers: tuple[ContractBlocker, ...] = ()


@dataclass(frozen=True)
class InitialProfileSelection:
    """Mandatory and explicitly selected or uniquely inferred initial profiles."""

    profiles: tuple[str, ...]
    inferred_profile: str | None


@dataclass(frozen=True)
class InitialRepositoryContract:
    """A complete validated initial repository declaration."""

    protocol: int
    release: str
    selected_profiles: tuple[str, ...]
    boundaries: tuple[RepositoryBoundary, ...]
    dependency_updates: tuple[DependencyUpdate, ...]
    canonical_validation: CanonicalValidation
    github: GitHubContract
    variables: tuple[tuple[str, Any], ...]
    local_fragments: tuple[tuple[str, tuple[str, ...]], ...]
    repository_owned: tuple[str, ...]
    inferred_profile: str | None

    def as_mapping(self) -> dict[str, Any]:
        """Return the normalized JSON manifest written by initialization."""

        return {
            "standards-version": self.protocol,
            "standards-release": self.release,
            "canonical-validation": self.canonical_validation.as_mapping(),
            "profiles": list(self.selected_profiles),
            "boundaries": [
                {
                    "path": boundary.path,
                    "type": boundary.boundary_type,
                    "title": boundary.title,
                }
                for boundary in self.boundaries
            ],
            "dependency-updates": [
                {
                    "ecosystem": update.ecosystem,
                    "directory": update.directory,
                    "schedule": update.schedule,
                }
                for update in self.dependency_updates
            ],
            "github": self.github.as_mapping(),
            "variables": {
                name: _thaw_value(value) for name, value in self.variables
            },
            "local-fragments": {
                target: list(fragments)
                for target, fragments in self.local_fragments
            },
            "repository-owned": list(self.repository_owned),
        }


def _freeze_mapping(value: dict[str, Any] | None) -> tuple[tuple[str, Any], ...] | None:
    if value is None:
        return None
    return tuple((key, _freeze_value(value[key])) for key in sorted(value))


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze_value(value[key])) for key in sorted(value))
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_value(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(
            isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
            for item in value
        ):
            return {key: _thaw_value(item) for key, item in value}
        return [_thaw_value(item) for item in value]
    return value


def select_initial_profiles(
    *,
    standards_root: Path,
    facts: dict[str, str],
    explicit_profiles: list[str] | None = None,
) -> InitialProfileSelection:
    """Select the mandatory baseline and at most one inferred ecosystem profile."""

    from . import repository_content

    standards_root = standards_root.expanduser().resolve()
    selectable: dict[str, dict[str, str]] = {}
    try:
        profile_paths = sorted((standards_root / "profiles").glob("*/profile.json"))
        for path in profile_paths:
            name = path.parent.name
            ordered: list[tuple[str, dict[str, Any], Path]] = []
            repository_content._load_profile(
                standards_root, name, ordered, set(), set()
            )
            data = next(
                profile_data
                for loaded_name, profile_data, _ in ordered
                if loaded_name == name
            )
            applicability = data.get("applicability")
            has_behavior = bool(data.get("files")) or bool(
                data.get("github", {}).get("required-labels")
            )
            if (
                name not in MANDATORY_INITIAL_PROFILES
                and isinstance(applicability, dict)
                and applicability
                and has_behavior
            ):
                selectable[name] = dict(applicability)
    except (OSError, StopIteration, repository_content.StandardsError) as exc:
        raise ContractError(str(exc)) from exc

    matches = tuple(
        name
        for name, applicability in selectable.items()
        if all(facts.get(key) == value for key, value in applicability.items())
    )
    incomplete = {
        name: tuple(key for key in applicability if key not in facts)
        for name, applicability in selectable.items()
        if all(
            key not in facts or facts[key] == value
            for key, value in applicability.items()
        )
        and any(key not in facts for key in applicability)
    }

    if incomplete:
        details = "; ".join(
            f"{name} (missing {', '.join(missing)})"
            for name, missing in sorted(incomplete.items())
        )
        raise ContractError(
            "applicability facts are incomplete; cannot prove profile selection: "
            + details
        )

    if explicit_profiles is not None:
        if (
            not explicit_profiles
            or not all(isinstance(item, str) and item for item in explicit_profiles)
            or len(explicit_profiles) != len(set(explicit_profiles))
        ):
            raise ContractError("profiles must be a non-empty unique list of names")
        unsupported = sorted(set(explicit_profiles) - set(selectable))
        if unsupported:
            raise ContractError(
                "profiles are not selectable ecosystem profiles: "
                + ", ".join(unsupported)
            )
        nonmatching = sorted(set(explicit_profiles) - set(matches))
        if nonmatching:
            raise ContractError(
                "explicit profiles do not match the supplied facts: "
                + ", ".join(nonmatching)
            )
        return InitialProfileSelection(
            tuple(
                dict.fromkeys(
                    (*MANDATORY_INITIAL_PROFILES, *explicit_profiles)
                )
            ),
            None,
        )

    if len(matches) > 1:
        raise ContractError(
            "multiple selectable ecosystem profiles match; choose explicitly: "
            + ", ".join(matches)
        )
    inferred = matches[0] if matches else None
    return InitialProfileSelection(
        (*MANDATORY_INITIAL_PROFILES, *((inferred,) if inferred else ())),
        inferred,
    )


def _initial_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return dict(value)


def build_initial_repository_contract(
    initialization: Mapping[str, Any],
    *,
    standards_root: Path,
) -> InitialRepositoryContract:
    """Build and validate one initial contract from explicit repository facts."""

    from . import repository_content

    standards_root = standards_root.expanduser().resolve()
    allowed = {
        "standards-release",
        "canonical-validation",
        "repository",
        "title",
        "facts",
        "profiles",
        "boundaries",
        "dependency-updates",
        "github",
        "variables",
        "local-fragments",
        "repository-owned",
    }
    unknown = sorted(set(initialization) - allowed)
    if unknown:
        raise ContractError(
            "unknown initialization fields: " + ", ".join(unknown)
        )

    requested_release = initialization.get("standards-release")
    if not isinstance(requested_release, str) or not requested_release:
        raise ContractError("standards-release must be an exact stable version")
    try:
        release = (standards_root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ContractError(f"cannot read selected release VERSION: {exc}") from exc
    if requested_release != release:
        raise ContractError(
            f"selected release checkout declares {release!r}, not {requested_release!r}"
        )

    repository = initialization.get("repository")
    if not isinstance(repository, str) or not repository:
        raise ContractError("repository must be an explicit owner/name")
    title = initialization.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ContractError("title must be an explicit non-empty string")
    facts = initialization.get("facts", {})
    if not isinstance(facts, dict) or not all(
        isinstance(key, str)
        and key
        and isinstance(value, str)
        and value
        for key, value in facts.items()
    ):
        raise ContractError("facts must be an object of non-empty strings")
    explicit_profiles = initialization.get("profiles")
    if explicit_profiles is not None and not isinstance(explicit_profiles, list):
        raise ContractError("profiles must be a non-empty unique list of names")
    selection = select_initial_profiles(
        standards_root=standards_root,
        facts=facts,
        explicit_profiles=explicit_profiles,
    )

    github = _initial_mapping(initialization.get("github", {}), "github")
    settings = {
        "delete-branch-on-merge": True,
        "allow-squash-merge": True,
        "allow-merge-commit": False,
        "allow-rebase-merge": False,
        "squash-merge-commit-title": DEFAULT_SQUASH_MERGE_COMMIT_TITLE,
        "squash-merge-commit-message": DEFAULT_SQUASH_MERGE_COMMIT_MESSAGE,
        **_initial_mapping(github.pop("settings", {}), "github.settings"),
    }
    features = {
        **DEFAULT_GITHUB_FEATURES,
        **_initial_mapping(github.pop("features", {}), "github.features"),
    }
    github_contract = {
        "repository": repository,
        "default-branch": "main",
        "settings": settings,
        "features": features,
        "ruleset": _default_main_ruleset(),
        **github,
    }
    github_contract["repository"] = repository
    github_contract["default-branch"] = "main"
    manifest = {
        "standards-version": repository_content.SUPPORTED_STANDARDS_VERSION,
        "standards-release": release,
        "canonical-validation": initialization.get("canonical-validation"),
        "profiles": list(selection.profiles),
        "boundaries": initialization.get(
            "boundaries",
            [{"path": ".", "type": "repository", "title": title}],
        ),
        "dependency-updates": initialization.get(
            "dependency-updates",
            [
                {
                    "ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": "weekly",
                }
            ],
        ),
        "github": github_contract,
        "variables": initialization.get("variables", {}),
        "local-fragments": initialization.get("local-fragments", {}),
        "repository-owned": initialization.get(
            "repository-owned", list(DEFAULT_INITIAL_REPOSITORY_OWNED)
        ),
    }

    try:
        with tempfile.TemporaryDirectory(
            prefix="repository-contract-initialization-"
        ) as directory:
            preview = Path(directory)
            (preview / ".repository-standards.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            _, normalized_manifest = repository_content._load_manifest(preview, None)
            for sources in normalized_manifest["local-fragments"].values():
                for source in sources:
                    if source == ".repository-standards.json":
                        raise ContractError(
                            "local fragment source conflicts with the repository "
                            "contract: .repository-standards.json"
                        )
                    placeholder = preview / source
                    placeholder.parent.mkdir(parents=True, exist_ok=True)
                    placeholder.touch(exist_ok=True)
            resolved = resolve_repository_contract(
                preview, standards_root=standards_root
            )
    except (OSError, repository_content.StandardsError) as exc:
        raise ContractError(f"cannot validate initial repository contract: {exc}") from exc

    return InitialRepositoryContract(
        protocol=resolved.protocol,
        release=resolved.release,
        selected_profiles=resolved.selected_profiles,
        boundaries=resolved.boundaries,
        dependency_updates=resolved.dependency_updates,
        canonical_validation=resolved.canonical_validation,
        github=resolved.github,
        variables=tuple(
            (name, _freeze_value(value)) for name, value in resolved.variables
        ),
        local_fragments=resolved.local_fragments,
        repository_owned=resolved.repository_owned,
        inferred_profile=selection.inferred_profile,
    )


def resolve_repository_contract(
    repository: Path,
    *,
    standards_root: Path,
    manifest: str | None = None,
    retain_content_blockers: bool = False,
) -> RepositoryContract:
    """Validate and normalize all repository contract knowledge in one call."""

    from . import repository_content

    repository = repository.expanduser().resolve()
    standards_root = standards_root.expanduser().resolve()
    if not repository.is_dir():
        raise ContractError(f"repository directory not found: {repository}")

    try:
        manifest_path, raw_manifest = repository_content._load_manifest(repository, manifest)
        raw_profiles = repository_content._load_profiles(
            standards_root, raw_manifest["profiles"]
        )
        managed_files, content_blockers = repository_content._build_content_with_blockers(
            standards_root,
            repository,
            raw_manifest,
            resolved_profiles=raw_profiles,
        )
        if content_blockers and not retain_content_blockers:
            diagnostics = "\n".join(
                f"- {blocker.target}: {blocker.message}"
                for blocker in content_blockers
            )
            raise repository_content.StandardsError(
                f"invalid managed content:\n{diagnostics}"
            )
    except repository_content.StandardsError as exc:
        raise ContractError(str(exc)) from exc

    profiles = tuple(
        ResolvedProfile(
            name=name,
            description=data.get("description", ""),
            applicability=_freeze_mapping(data.get("applicability")),
        )
        for name, data, _ in raw_profiles
    )
    github = raw_manifest["github"]
    github_settings = github["settings"]
    github_features = github.get(
        "features", DEFAULT_GITHUB_FEATURES
    )
    return RepositoryContract(
        repository=repository,
        manifest_path=manifest_path,
        standards_root=standards_root,
        protocol=raw_manifest["standards-version"],
        release=raw_manifest["standards-release"],
        selected_profiles=tuple(raw_manifest["profiles"]),
        profiles=profiles,
        managed_files=tuple(
            ManagedFile(
                target=item.target,
                mode=item.mode,
                content=item.content,
                origins=item.origins,
            )
            for item in managed_files
        ),
        managed_paths=tuple(item.target for item in managed_files),
        managed_absences=tuple(
            item.target for item in managed_files if item.mode == "absent"
        ),
        repository_owned=tuple(raw_manifest["repository-owned"]),
        variables=tuple(
            (name, raw_manifest["variables"][name])
            for name in sorted(raw_manifest["variables"])
        ),
        local_fragments=tuple(
            (target, tuple(raw_manifest["local-fragments"][target]))
            for target in sorted(raw_manifest["local-fragments"])
        ),
        required_labels=repository_content._collect_required_labels(raw_profiles),
        dependency_updates=tuple(
            DependencyUpdate(
                ecosystem=item["ecosystem"],
                directory=item["directory"],
                schedule=item["schedule"],
            )
            for item in raw_manifest["dependency-updates"]
        ),
        boundaries=tuple(
            RepositoryBoundary(
                path=item["path"],
                boundary_type=item["type"],
                title=item["title"],
            )
            for item in raw_manifest["boundaries"]
        ),
        canonical_validation=CanonicalValidation(
            executable=raw_manifest["canonical-validation"]["executable"],
            arguments=tuple(raw_manifest["canonical-validation"]["arguments"]),
            working_directory=raw_manifest["canonical-validation"][
                "working-directory"
            ],
        ),
        github=GitHubContract(
            repository=github["repository"],
            default_branch=github["default-branch"],
            settings=GitHubSettings(
                delete_branch_on_merge=github_settings["delete-branch-on-merge"],
                allow_squash_merge=github_settings["allow-squash-merge"],
                allow_merge_commit=github_settings["allow-merge-commit"],
                allow_rebase_merge=github_settings["allow-rebase-merge"],
                squash_merge_commit_title=github_settings.get(
                    "squash-merge-commit-title",
                    DEFAULT_SQUASH_MERGE_COMMIT_TITLE,
                ),
                squash_merge_commit_message=github_settings.get(
                    "squash-merge-commit-message",
                    DEFAULT_SQUASH_MERGE_COMMIT_MESSAGE,
                ),
            ),
            ruleset=_freeze_mapping(github["ruleset"]),
            features=GitHubFeatures(
                issues=github_features["issues"],
                projects=github_features["projects"],
                wiki=github_features["wiki"],
            ),
        ),
        content_blockers=tuple(
            ContractBlocker(blocker.target, blocker.message)
            for blocker in content_blockers
        ),
    )
