"""Resolve repository declarations into one normalized repository contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContractError(Exception):
    """Raised when a repository contract cannot be validated and normalized."""


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
class GitHubSettings:
    delete_branch_on_merge: bool
    allow_squash_merge: bool
    allow_merge_commit: bool
    allow_rebase_merge: bool


@dataclass(frozen=True)
class GitHubContract:
    repository: str
    default_branch: str
    settings: GitHubSettings
    ruleset: tuple[tuple[str, Any], ...] | None

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
    github: GitHubContract
    plan_blockers: tuple[ContractBlocker, ...] = ()


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


def resolve_repository_contract(
    repository: Path,
    *,
    standards_root: Path,
    manifest: str | None = None,
    retain_plan_blockers: bool = False,
) -> RepositoryContract:
    """Validate and normalize all repository contract knowledge in one call."""

    # Imported here so the legacy implementation can delegate to this interface
    # while its internal parsing and rendering helpers are deepened incrementally.
    from . import standards

    repository = repository.expanduser().resolve()
    standards_root = standards_root.expanduser().resolve()
    if not repository.is_dir():
        raise ContractError(f"repository directory not found: {repository}")

    try:
        manifest_path, raw_manifest = standards._load_manifest(repository, manifest)
        raw_profiles = standards._load_profiles(
            standards_root, raw_manifest["profiles"]
        )
        managed_files, plan_blockers = standards._build_plan_with_blockers(
            standards_root,
            repository,
            raw_manifest,
            resolved_profiles=raw_profiles,
        )
        if plan_blockers and not retain_plan_blockers:
            diagnostics = "\n".join(
                f"- {blocker.target}: {blocker.message}"
                for blocker in plan_blockers
            )
            raise standards.StandardsError(
                f"invalid managed-content plan:\n{diagnostics}"
            )
    except standards.StandardsError as exc:
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
        required_labels=standards._collect_required_labels(raw_profiles),
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
        github=GitHubContract(
            repository=github["repository"],
            default_branch=github["default-branch"],
            settings=GitHubSettings(
                delete_branch_on_merge=github_settings["delete-branch-on-merge"],
                allow_squash_merge=github_settings["allow-squash-merge"],
                allow_merge_commit=github_settings["allow-merge-commit"],
                allow_rebase_merge=github_settings["allow-rebase-merge"],
            ),
            ruleset=_freeze_mapping(github["ruleset"]),
        ),
        plan_blockers=tuple(
            ContractBlocker(blocker.target, blocker.message)
            for blocker in plan_blockers
        ),
    )
