"""Plan and perform first publication from a prepared creation baseline."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .live_reconciliation import (
    GitHubAdapter,
    GitHubSnapshot,
    LiveDesiredStateDelta,
    LiveDifference,
    LiveLifecycle,
    LiveOperation,
    reconcile_live_github,
)
from .repository_contract import ContractError, RepositoryContract, resolve_repository_contract
from .standards import (
    StandardsError,
    inspect,
    inspect_boundaries,
    inspect_repository_owned_documents,
)


INITIAL_COMMIT_MESSAGE = "chore: publish initial repository"
GITHUB_REMOTE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?/?$"
)


class PublicationError(Exception):
    """Raised when first publication cannot be planned safely."""


@dataclass(frozen=True)
class InitialCommitFile:
    path: str
    mode: str
    object_id: str


@dataclass(frozen=True)
class InitialCommitPreview:
    tree_oid: str
    message: str
    author_name: str
    author_email: str
    timestamp: int
    timezone: str
    files: tuple[InitialCommitFile, ...]


@dataclass(frozen=True)
class PublicationPlan:
    plan_id: str
    repository: Path
    git_directory: Path
    repository_name: str
    standards_release: str
    standards_protocol: int
    branch: str
    remote_url: str
    push_url: str
    local_push_for_testing: bool
    commit: InitialCommitPreview
    observed_github_state: dict[str, Any]
    remote_fingerprint: str
    live_delta: LiveDesiredStateDelta
    steps: tuple[str, ...]
    confirmation: str


@dataclass(frozen=True)
class PublicationReport:
    completed: tuple[str, ...]
    failed: str | None
    uncertain: str | None
    remaining: tuple[str, ...]
    error: str | None
    commit_oid: str | None
    standards_complete: bool = False

    @property
    def complete(self) -> bool:
        return (
            self.failed is None
            and self.uncertain is None
            and self.standards_complete
        )


def _git(
    repository: Path,
    *arguments: str,
    environment: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
        input=input_text,
    )


def _required_git_value(repository: Path, *arguments: str, label: str) -> str:
    result = _git(repository, *arguments)
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        diagnostic = result.stderr.strip() or result.stdout.strip()
        suffix = f": {diagnostic}" if diagnostic else ""
        raise PublicationError(f"cannot determine {label}{suffix}")
    return value


def _validate_git_identity(repository: Path, name: str, email: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": "@0 +0000",
        }
    )
    result = _git(
        repository,
        "var",
        "GIT_AUTHOR_IDENT",
        environment=environment,
    )
    if result.returncode != 0:
        raise PublicationError(
            "cannot validate effective Git identity: "
            + (result.stderr.strip() or result.stdout.strip())
        )
    if result.stdout.rstrip("\r\n") != f"{name} <{email}> 0 +0000":
        raise PublicationError(
            "effective Git identity contains characters Git strips or normalizes"
        )


def _validate_offline_baseline(contract: RepositoryContract) -> None:
    managed = inspect(contract.repository, contract.managed_files)
    drift = [result for result in managed if result.status != "ok"]
    boundaries = inspect_boundaries(contract.repository, contract.boundaries)
    invalid_boundaries = [result for result in boundaries if result.status != "ok"]
    documents = inspect_repository_owned_documents(
        contract.repository, contract.repository_owned
    )
    invalid_documents = [result for result in documents if result.status != "ok"]
    findings = [
        *(f"{result.target}: {result.status}" for result in drift),
        *(
            f"boundary {result.path}: {'; '.join(result.messages)}"
            for result in invalid_boundaries
        ),
        *(
            f"document {result.path}: {'; '.join(result.messages)}"
            for result in invalid_documents
        ),
    ]
    if findings:
        raise PublicationError(
            "prepared creation baseline does not pass the selected release:\n- "
            + "\n- ".join(findings)
        )


def _initial_tree(repository: Path, git_directory: Path) -> tuple[str, tuple[InitialCommitFile, ...]]:
    with tempfile.TemporaryDirectory(prefix="first-publication-plan-") as directory:
        temporary = Path(directory)
        object_directory = temporary / "objects"
        object_directory.mkdir()
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_INDEX_FILE": str(temporary / "index"),
                "GIT_OBJECT_DIRECTORY": str(object_directory),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(git_directory / "objects"),
            }
        )
        existing_index = git_directory / "index"
        if existing_index.is_file():
            shutil.copyfile(existing_index, temporary / "index")
        added = _git(repository, "add", "--all", environment=environment)
        if added.returncode != 0:
            raise PublicationError(
                "cannot construct the initial commit preview: "
                + (added.stderr.strip() or added.stdout.strip())
            )
        tree = _git(repository, "write-tree", environment=environment)
        if tree.returncode != 0:
            raise PublicationError(
                "cannot compute the initial Git tree: "
                + (tree.stderr.strip() or tree.stdout.strip())
            )
        listed = _git(repository, "ls-files", "--stage", "-z", environment=environment)
        if listed.returncode != 0:
            raise PublicationError(
                "cannot list the initial commit contents: "
                + (listed.stderr.strip() or listed.stdout.strip())
            )
    files: list[InitialCommitFile] = []
    for record in listed.stdout.split("\0"):
        if not record:
            continue
        metadata, path = record.split("\t", 1)
        mode, object_id, stage = metadata.split(" ", 2)
        if stage != "0":
            raise PublicationError(f"initial commit contains an unresolved stage: {path}")
        files.append(InitialCommitFile(path, mode, object_id))
    if not files:
        raise PublicationError("prepared creation baseline has no initial commit contents")
    return tree.stdout.strip(), tuple(files)


def _collect_pages(adapter: GitHubAdapter, endpoint: str) -> tuple[dict[str, Any], ...]:
    results: list[dict[str, Any]] = []
    page = 1
    separator = "&" if "?" in endpoint else "?"
    while True:
        try:
            response = adapter.request(
                "GET", f"{endpoint}{separator}per_page=100&page={page}"
            )
        except (StandardsError, OSError) as exc:
            raise PublicationError(str(exc)) from exc
        if not isinstance(response, list) or not all(
            isinstance(item, dict) for item in response
        ):
            raise PublicationError(f"GitHub {endpoint} response must be a list")
        results.extend(response)
        if len(response) < 100:
            return tuple(results)
        page += 1


def _observed_github_state(
    snapshot: GitHubSnapshot,
    branches: tuple[dict[str, Any], ...],
    pulls: tuple[dict[str, Any], ...],
    git_refs: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    return json.loads(
        json.dumps(
            {
                "repository": snapshot.repository,
                "labels": sorted(snapshot.label_names),
                "rulesets": snapshot.rulesets,
                "branches": branches,
                "pulls": pulls,
                "git-refs": [
                    {"object-id": object_id, "ref": reference}
                    for object_id, reference in git_refs
                ],
            }
        )
    )


def _remote_fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_identifier(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plan_identity_payload(
    *,
    repository: Path,
    git_directory: Path,
    repository_name: str,
    release: str,
    protocol: int,
    branch: str,
    remote_url: str,
    push_url: str,
    local_push_for_testing: bool,
    commit: InitialCommitPreview,
    observed_github_state: dict[str, Any],
    remote_fingerprint: str,
    live_delta: LiveDesiredStateDelta,
) -> dict[str, Any]:
    return {
        "repository": str(repository),
        "git-directory": str(git_directory),
        "repository-name": repository_name,
        "release": release,
        "protocol": protocol,
        "branch": branch,
        "remote-url": remote_url,
        "push-url": push_url,
        "local-push-for-testing": local_push_for_testing,
        "tree": commit.tree_oid,
        "files": [file.__dict__ for file in commit.files],
        "commit": {
            "message": commit.message,
            "author-name": commit.author_name,
            "author-email": commit.author_email,
            "timestamp": commit.timestamp,
            "timezone": commit.timezone,
        },
        "observed-github-state": observed_github_state,
        "remote": remote_fingerprint,
        "live-operations": [
            {
                "description": operation.description,
                "method": operation.method,
                "endpoint": operation.endpoint,
                "payload": operation.payload,
            }
            for operation in live_delta.operations
        ],
    }


def _publication_steps(delta: LiveDesiredStateDelta) -> tuple[str, ...]:
    return (
        "CREATE   initial commit",
        "INSTALL  initial Git index",
        "PUBLISH  main to origin",
        *(operation.description for operation in delta.operations),
        "VERIFY   committed content",
        "VERIFY   live GitHub state",
    )


def _remote_refs(push_url: str) -> tuple[tuple[str, str], ...]:
    result = subprocess.run(
        ["git", "ls-remote", push_url],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise PublicationError(
            "cannot inspect origin refs: "
            + (result.stderr.strip() or result.stdout.strip())
        )
    refs: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        try:
            object_id, reference = line.split("\t", 1)
        except ValueError as exc:
            raise PublicationError("origin ref response was invalid") from exc
        refs.append((object_id, reference))
    return tuple(refs)


def plan_first_publication(
    repository: Path,
    adapter: GitHubAdapter,
    *,
    standards_root: Path,
    now: datetime | None = None,
    _allow_local_push_for_testing: bool = False,
) -> PublicationPlan:
    """Validate and preview first publication without mutating either repository."""

    repository = repository.expanduser().resolve()
    try:
        contract = resolve_repository_contract(
            repository, standards_root=standards_root
        )
        _validate_offline_baseline(contract)
    except (ContractError, StandardsError) as exc:
        raise PublicationError(str(exc)) from exc

    top_level = Path(
        _required_git_value(
            repository, "rev-parse", "--show-toplevel", label="Git worktree root"
        )
    ).resolve()
    if top_level != repository:
        raise PublicationError(
            f"target must be the Git worktree root: {top_level}"
        )
    branch = _required_git_value(
        repository, "symbolic-ref", "--short", "HEAD", label="current branch"
    )
    if branch != "main":
        raise PublicationError(f"prepared creation baseline must be on unborn main, not {branch!r}")
    head = _git(repository, "rev-parse", "--verify", "HEAD")
    if head.returncode == 0:
        raise PublicationError(
            f"prepared creation baseline must have no commits; found {head.stdout.strip()}"
        )
    local_refs = _git(repository, "for-each-ref", "--format=%(refname)", "refs")
    if local_refs.returncode != 0:
        raise PublicationError(
            "cannot inspect local Git refs: "
            + (local_refs.stderr.strip() or local_refs.stdout.strip())
        )
    if local_refs.stdout.strip():
        raise PublicationError(
            "prepared creation baseline must have no local refs; found "
            + ", ".join(local_refs.stdout.splitlines())
        )
    git_directory_value = _required_git_value(
        repository, "rev-parse", "--git-dir", label="Git directory"
    )
    git_directory = Path(git_directory_value)
    if not git_directory.is_absolute():
        git_directory = repository / git_directory
    git_directory = git_directory.resolve()
    if (git_directory / "index.lock").exists():
        raise PublicationError(
            "prepared creation baseline has an active Git index lock"
        )

    author_name = _required_git_value(
        repository,
        "config",
        "--get",
        "user.name",
        label="effective Git user.name",
    )
    author_email = _required_git_value(
        repository,
        "config",
        "--get",
        "user.email",
        label="effective Git user.email",
    )
    if any(character in author_name + author_email for character in "\r\n"):
        raise PublicationError(
            "effective Git identity must use single-line name and email values"
        )
    _validate_git_identity(repository, author_name, author_email)

    remote_url = _required_git_value(
        repository,
        "config",
        "--local",
        "--get",
        "remote.origin.url",
        label="origin URL",
    )
    match = GITHUB_REMOTE.fullmatch(remote_url)
    remote_repository = match.group("repository") if match else None
    if remote_repository != contract.github.repository:
        raise PublicationError(
            f"origin identifies {remote_repository or remote_url!r}; "
            f"the repository contract requires {contract.github.repository!r}"
        )
    push_urls_result = _git(
        repository, "remote", "get-url", "--push", "--all", "origin"
    )
    push_urls = tuple(
        line.strip()
        for line in push_urls_result.stdout.splitlines()
        if line.strip()
    )
    if push_urls_result.returncode != 0 or not push_urls:
        raise PublicationError(
            "cannot read origin push URL: "
            + (
                push_urls_result.stderr.strip()
                or push_urls_result.stdout.strip()
                or "value is missing"
            )
        )
    if len(push_urls) != 1:
        raise PublicationError(
            "origin must have exactly one push URL; found "
            + ", ".join(repr(url) for url in push_urls)
        )
    push_url = push_urls[0]
    push_match = GITHUB_REMOTE.fullmatch(push_url)
    push_repository = push_match.group("repository") if push_match else None
    if (
        push_repository != contract.github.repository
        and not _allow_local_push_for_testing
    ):
        raise PublicationError(
            f"origin push target identifies {push_repository or push_url!r}; "
            f"the repository contract requires {contract.github.repository!r}"
        )
    git_refs = _remote_refs(push_url)
    if git_refs:
        raise PublicationError(
            "Git remote is not empty; refs already exist: "
            + ", ".join(reference for _, reference in git_refs)
        )

    tree_oid, files = _initial_tree(repository, git_directory)
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise PublicationError("publication plan time must include a timezone")
    instant = instant.astimezone(timezone.utc).replace(microsecond=0)
    commit = InitialCommitPreview(
        tree_oid=tree_oid,
        message=INITIAL_COMMIT_MESSAGE,
        author_name=author_name,
        author_email=author_email,
        timestamp=int(instant.timestamp()),
        timezone="+0000",
        files=files,
    )

    try:
        snapshot = adapter.observe(contract, lifecycle=LiveLifecycle.PUBLISHED)
    except StandardsError as exc:
        raise PublicationError(str(exc)) from exc
    repository_name = contract.github.repository
    if snapshot.repository.get("full_name") != repository_name:
        raise PublicationError(
            f"GitHub returned repository identity {snapshot.repository.get('full_name')!r}; "
            f"expected {repository_name!r}"
        )
    permissions = snapshot.repository.get("permissions")
    if not isinstance(permissions, dict):
        raise PublicationError("GitHub repository response did not prove permissions")
    missing_permissions = [
        permission for permission in ("admin", "push") if permissions.get(permission) is not True
    ]
    if missing_permissions:
        raise PublicationError(
            "first publication requires GitHub permissions: "
            + ", ".join(missing_permissions)
        )
    endpoint = f"repos/{repository_name}"
    branches = snapshot.branches
    pulls = _collect_pages(adapter, f"{endpoint}/pulls?state=all")
    if branches:
        raise PublicationError("GitHub repository is not empty; remote branches already exist")
    if pulls:
        raise PublicationError("prepared GitHub repository unexpectedly contains pull requests")

    prepared_snapshot = GitHubSnapshot(
        repository=snapshot.repository,
        branches=snapshot.branches,
        label_names=snapshot.label_names,
        rulesets=snapshot.rulesets,
        lifecycle=LiveLifecycle.PREPARED,
    )
    prepared_delta = reconcile_live_github(contract, prepared_snapshot)
    applicable_findings = tuple(
        finding
        for difference in prepared_delta.differences
        if not difference.pending
        for finding in difference.findings
    )
    if applicable_findings:
        raise PublicationError(
            "prepared GitHub state has applicable drift:\n- "
            + "\n- ".join(applicable_findings)
        )
    live_delta = reconcile_live_github(contract, snapshot)
    steps = _publication_steps(live_delta)
    observed_github_state = _observed_github_state(
        snapshot, branches, pulls, git_refs
    )
    remote_fingerprint = _remote_fingerprint(observed_github_state)
    plan_id = _plan_identifier(
        _plan_identity_payload(
            repository=repository,
            git_directory=git_directory,
            repository_name=repository_name,
            release=contract.release,
            protocol=contract.protocol,
            branch=branch,
            remote_url=remote_url,
            push_url=push_url,
            local_push_for_testing=_allow_local_push_for_testing,
            commit=commit,
            observed_github_state=observed_github_state,
            remote_fingerprint=remote_fingerprint,
            live_delta=live_delta,
        )
    )
    confirmation = f"Publish {repository_name} from plan {plan_id}"
    return PublicationPlan(
        plan_id=plan_id,
        repository=repository,
        git_directory=git_directory,
        repository_name=repository_name,
        standards_release=contract.release,
        standards_protocol=contract.protocol,
        branch=branch,
        remote_url=remote_url,
        push_url=push_url,
        local_push_for_testing=_allow_local_push_for_testing,
        commit=commit,
        observed_github_state=observed_github_state,
        remote_fingerprint=remote_fingerprint,
        live_delta=live_delta,
        steps=steps,
        confirmation=confirmation,
    )


def publication_plan_mapping(plan: PublicationPlan) -> dict[str, Any]:
    """Return the complete portable record required to revalidate one Plan."""

    return {
        "version": 1,
        "plan-id": plan.plan_id,
        "repository": str(plan.repository),
        "git-directory": str(plan.git_directory),
        "repository-name": plan.repository_name,
        "standards-release": plan.standards_release,
        "standards-protocol": plan.standards_protocol,
        "branch": plan.branch,
        "remote-url": plan.remote_url,
        "push-url": plan.push_url,
        "local-push-for-testing": plan.local_push_for_testing,
        "commit": {
            "tree-oid": plan.commit.tree_oid,
            "message": plan.commit.message,
            "author-name": plan.commit.author_name,
            "author-email": plan.commit.author_email,
            "timestamp": plan.commit.timestamp,
            "timezone": plan.commit.timezone,
            "files": [
                {
                    "path": item.path,
                    "mode": item.mode,
                    "object-id": item.object_id,
                }
                for item in plan.commit.files
            ],
        },
        "observed-github-state": plan.observed_github_state,
        "remote-fingerprint": plan.remote_fingerprint,
        "live-delta": {
            "repository": plan.live_delta.repository,
            "differences": [
                {
                    "findings": list(difference.findings),
                    "pending": difference.pending,
                    "operations": [
                        {
                            "description": operation.description,
                            "method": operation.method,
                            "endpoint": operation.endpoint,
                            "payload": operation.payload,
                        }
                        for operation in difference.operations
                    ],
                }
                for difference in plan.live_delta.differences
            ],
        },
        "steps": list(plan.steps),
        "confirmation": plan.confirmation,
    }


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationError(f"publication Plan field {field} must be an object")
    return value


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PublicationError(f"publication Plan field {field} must be a string")
    return value


def publication_plan_from_mapping(
    value: object, *, _allow_local_push_for_testing: bool = False
) -> PublicationPlan:
    """Load and authenticate one portable Plan record."""

    root = _mapping(value, "root")
    if root.get("version") != 1:
        raise PublicationError("unsupported publication Plan version")
    commit_value = _mapping(root.get("commit"), "commit")
    raw_files = commit_value.get("files")
    if not isinstance(raw_files, list):
        raise PublicationError("publication Plan field commit.files must be a list")
    files = tuple(
        InitialCommitFile(
            _string(_mapping(item, "commit.files[]").get("path"), "commit.files[].path"),
            _string(_mapping(item, "commit.files[]").get("mode"), "commit.files[].mode"),
            _string(
                _mapping(item, "commit.files[]").get("object-id"),
                "commit.files[].object-id",
            ),
        )
        for item in raw_files
    )
    timestamp = commit_value.get("timestamp")
    protocol = root.get("standards-protocol")
    if not isinstance(timestamp, int) or isinstance(timestamp, bool):
        raise PublicationError("publication Plan field commit.timestamp must be an integer")
    if not isinstance(protocol, int) or isinstance(protocol, bool):
        raise PublicationError("publication Plan field standards-protocol must be an integer")
    commit = InitialCommitPreview(
        tree_oid=_string(commit_value.get("tree-oid"), "commit.tree-oid"),
        message=_string(commit_value.get("message"), "commit.message"),
        author_name=_string(commit_value.get("author-name"), "commit.author-name"),
        author_email=_string(commit_value.get("author-email"), "commit.author-email"),
        timestamp=timestamp,
        timezone=_string(commit_value.get("timezone"), "commit.timezone"),
        files=files,
    )
    delta_value = _mapping(root.get("live-delta"), "live-delta")
    raw_differences = delta_value.get("differences")
    if not isinstance(raw_differences, list):
        raise PublicationError("publication Plan field live-delta.differences must be a list")
    differences: list[LiveDifference] = []
    for raw_difference in raw_differences:
        difference = _mapping(raw_difference, "live-delta.differences[]")
        raw_findings = difference.get("findings")
        raw_operations = difference.get("operations")
        pending = difference.get("pending")
        if not isinstance(raw_findings, list) or not all(
            isinstance(item, str) for item in raw_findings
        ):
            raise PublicationError("publication Plan findings must be strings")
        if not isinstance(raw_operations, list) or not isinstance(pending, bool):
            raise PublicationError("publication Plan live difference is invalid")
        operations: list[LiveOperation] = []
        for raw_operation in raw_operations:
            operation = _mapping(raw_operation, "live operation")
            payload = _mapping(operation.get("payload"), "live operation payload")
            operations.append(
                LiveOperation(
                    _string(operation.get("description"), "live operation description"),
                    _string(operation.get("method"), "live operation method"),
                    _string(operation.get("endpoint"), "live operation endpoint"),
                    payload,
                )
            )
        differences.append(
            LiveDifference(tuple(raw_findings), tuple(operations), pending)
        )
    live_delta = LiveDesiredStateDelta(
        _string(delta_value.get("repository"), "live-delta.repository"),
        tuple(differences),
    )
    raw_steps = root.get("steps")
    if not isinstance(raw_steps, list) or not all(
        isinstance(item, str) and item for item in raw_steps
    ):
        raise PublicationError("publication Plan steps must be non-empty strings")
    repository = Path(_string(root.get("repository"), "repository"))
    git_directory = Path(_string(root.get("git-directory"), "git-directory"))
    repository_name = _string(root.get("repository-name"), "repository-name")
    release = _string(root.get("standards-release"), "standards-release")
    branch = _string(root.get("branch"), "branch")
    remote_url = _string(root.get("remote-url"), "remote-url")
    push_url = _string(root.get("push-url"), "push-url")
    local_push_for_testing = root.get("local-push-for-testing")
    if not isinstance(local_push_for_testing, bool):
        raise PublicationError(
            "publication Plan field local-push-for-testing must be a boolean"
        )
    if local_push_for_testing and not _allow_local_push_for_testing:
        raise PublicationError(
            "portable publication Plans cannot enable the test-only local push transport"
        )
    observed_github_state = _mapping(
        root.get("observed-github-state"), "observed-github-state"
    )
    remote_fingerprint = _string(
        root.get("remote-fingerprint"), "remote-fingerprint"
    )
    if _remote_fingerprint(observed_github_state) != remote_fingerprint:
        raise PublicationError(
            "publication Plan observed GitHub state does not match its fingerprint"
        )
    plan_id = _string(root.get("plan-id"), "plan-id")
    expected_id = _plan_identifier(
        _plan_identity_payload(
            repository=repository,
            git_directory=git_directory,
            repository_name=repository_name,
            release=release,
            protocol=protocol,
            branch=branch,
            remote_url=remote_url,
            push_url=push_url,
            local_push_for_testing=local_push_for_testing,
            commit=commit,
            observed_github_state=observed_github_state,
            remote_fingerprint=remote_fingerprint,
            live_delta=live_delta,
        )
    )
    if plan_id != expected_id:
        raise PublicationError("publication Plan identity does not match its recorded inputs")
    confirmation = _string(root.get("confirmation"), "confirmation")
    if confirmation != f"Publish {repository_name} from plan {plan_id}":
        raise PublicationError("publication Plan confirmation is invalid")
    expected_steps = _publication_steps(live_delta)
    if tuple(raw_steps) != expected_steps:
        raise PublicationError(
            "publication Plan steps do not match its live desired-state delta"
        )
    return PublicationPlan(
        plan_id=plan_id,
        repository=repository,
        git_directory=git_directory,
        repository_name=repository_name,
        standards_release=release,
        standards_protocol=protocol,
        branch=branch,
        remote_url=remote_url,
        push_url=push_url,
        local_push_for_testing=local_push_for_testing,
        commit=commit,
        observed_github_state=observed_github_state,
        remote_fingerprint=remote_fingerprint,
        live_delta=live_delta,
        steps=tuple(raw_steps),
        confirmation=confirmation,
    )


def write_publication_plan(plan: PublicationPlan, path: Path) -> None:
    """Persist a Plan outside the target repository without changing the target."""

    expanded_path = path.expanduser()
    if not expanded_path.is_absolute():
        expanded_path = Path.cwd() / expanded_path
    path = expanded_path.parent.resolve() / expanded_path.name
    for protected in (plan.repository, plan.git_directory):
        try:
            path.relative_to(protected)
        except ValueError:
            continue
        raise PublicationError(
            "publication Plan file must be outside the target repository and Git directory"
        )
    if not path.parent.is_dir():
        raise PublicationError(f"publication Plan directory does not exist: {path.parent}")
    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = None
        with stream:
            stream.write(json.dumps(publication_plan_mapping(plan), indent=2) + "\n")
        os.replace(temporary, path)
        temporary = None
    except OSError as exc:
        raise PublicationError(f"cannot write publication Plan: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass


def load_publication_plan(
    path: Path, *, _allow_local_push_for_testing: bool = False
) -> PublicationPlan:
    try:
        value = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read publication Plan: {exc}") from exc
    return publication_plan_from_mapping(
        value, _allow_local_push_for_testing=_allow_local_push_for_testing
    )


def _failed_report(
    steps: tuple[str, ...],
    index: int,
    error: str,
    *,
    commit_oid: str | None,
) -> PublicationReport:
    return PublicationReport(
        completed=steps[:index],
        failed=steps[index],
        uncertain=None,
        remaining=steps[index + 1 :],
        error=error,
        commit_oid=commit_oid,
    )


def _uncertain_report(
    steps: tuple[str, ...],
    index: int,
    error: str,
    *,
    commit_oid: str | None,
) -> PublicationReport:
    return PublicationReport(
        completed=steps[:index],
        failed=None,
        uncertain=steps[index],
        remaining=steps[index + 1 :],
        error=error,
        commit_oid=commit_oid,
    )


def _remote_main_observation(plan: PublicationPlan) -> tuple[str | None, str | None]:
    observed = subprocess.run(
        ["git", "ls-remote", plan.push_url, f"refs/heads/{plan.branch}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if observed.returncode != 0:
        return None, observed.stderr.strip() or observed.stdout.strip()
    line = observed.stdout.strip()
    return (line.split("\t", 1)[0] if line else None), None


def _commit_metadata_error(plan: PublicationPlan, commit_oid: str) -> str | None:
    message = _git(plan.repository, "show", "-s", "--format=%B", commit_oid)
    metadata = _git(
        plan.repository,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%at%x00%ai%x00%cn%x00%ce%x00%ct%x00%ci%x00%P",
        commit_oid,
    )
    if message.returncode != 0 or metadata.returncode != 0:
        return "cannot verify the created commit metadata"
    values = metadata.stdout.rstrip("\n").split("\0")
    if len(values) != 9:
        return "created commit metadata response was invalid"
    (
        author_name,
        author_email,
        author_timestamp,
        author_date,
        committer_name,
        committer_email,
        committer_timestamp,
        committer_date,
        parents,
    ) = values
    expected_timestamp = str(plan.commit.timestamp)
    if message.stdout.rstrip("\n") != plan.commit.message:
        return "created commit message does not match the confirmed Plan"
    if (author_name, committer_name) != (
        plan.commit.author_name,
        plan.commit.author_name,
    ):
        return "created commit author or committer name does not match the confirmed Plan"
    if (author_email, committer_email) != (
        plan.commit.author_email,
        plan.commit.author_email,
    ):
        return "created commit author or committer email does not match the confirmed Plan"
    if (author_timestamp, committer_timestamp) != (
        expected_timestamp,
        expected_timestamp,
    ):
        return "created commit timestamp does not match the confirmed Plan"
    if not author_date.endswith(f" {plan.commit.timezone}") or not committer_date.endswith(
        f" {plan.commit.timezone}"
    ):
        return "created commit timezone does not match the confirmed Plan"
    if parents:
        return "created initial commit unexpectedly has a parent"
    return None


def _verify_committed_content(
    plan: PublicationPlan, contract: RepositoryContract, commit_oid: str
) -> str | None:
    head = _git(plan.repository, "rev-parse", "HEAD")
    if head.returncode != 0 or head.stdout.strip() != commit_oid:
        return "local HEAD no longer identifies the published initial commit"
    tree = _git(plan.repository, "rev-parse", "HEAD^{tree}")
    if tree.returncode != 0 or tree.stdout.strip() != plan.commit.tree_oid:
        return "committed tree does not match the planned initial content"
    status = _git(
        plan.repository,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    if status.returncode != 0 or status.stdout:
        return "working tree changed while first publication was running"
    remote_oid, observation_error = _remote_main_observation(plan)
    if observation_error:
        return f"cannot verify published main: {observation_error}"
    if remote_oid != commit_oid:
        return "published main does not identify the planned initial commit"
    try:
        _validate_offline_baseline(contract)
    except (PublicationError, StandardsError, OSError) as exc:
        return str(exc)
    return None


def _verify_live_state(
    plan: PublicationPlan,
    contract: RepositoryContract,
    adapter: GitHubAdapter,
) -> str | None:
    try:
        snapshot = adapter.observe(contract, lifecycle=LiveLifecycle.PUBLISHED)
        delta = reconcile_live_github(contract, snapshot)
        pulls = _collect_pages(
            adapter, f"repos/{plan.repository_name}/pulls?state=all"
        )
    except (PublicationError, StandardsError, OSError) as exc:
        return str(exc)
    if snapshot.repository.get("full_name") != plan.repository_name:
        return "re-observed GitHub repository identity changed"
    if delta.findings:
        return "live GitHub state remains non-conforming:\n- " + "\n- ".join(
            delta.findings
        )
    if not any(branch.get("name") == plan.branch for branch in snapshot.branches):
        return f"GitHub did not re-observe published branch {plan.branch!r}"
    if pulls:
        return "first publication unexpectedly left a pull request"
    return None


def _live_operation_state(
    contract: RepositoryContract,
    adapter: GitHubAdapter,
    operation: LiveOperation,
    expected_remaining: tuple[LiveOperation, ...],
) -> tuple[str, str | None]:
    try:
        snapshot = adapter.observe(contract, lifecycle=LiveLifecycle.PUBLISHED)
        delta = reconcile_live_github(contract, snapshot)
    except (StandardsError, OSError) as exc:
        return "unknown", str(exc)
    if delta.operations == expected_remaining:
        return "completed", None
    if delta.operations == (operation, *expected_remaining):
        return "failed", None
    return (
        "unknown",
        "re-observed live desired-state delta differs from both the pre-write "
        "and successful-write states",
    )


def publish_first_publication(
    plan: PublicationPlan,
    adapter: GitHubAdapter,
    *,
    standards_root: Path,
    confirmation: str,
) -> PublicationReport:
    """Publish one current plan after its exact human confirmation."""

    if confirmation != plan.confirmation:
        raise PublicationError(
            "Publish requires the exact confirmation from the current Plan; "
            "a repository or plan reference alone is not authorization"
        )
    plan_time = datetime.fromtimestamp(plan.commit.timestamp, timezone.utc)
    try:
        fresh = plan_first_publication(
            plan.repository,
            adapter,
            standards_root=standards_root,
            now=plan_time,
            _allow_local_push_for_testing=plan.local_push_for_testing,
        )
    except PublicationError as exc:
        raise PublicationError(
            f"publication Plan {plan.plan_id} is stale: {exc}"
        ) from exc
    if fresh.plan_id != plan.plan_id:
        raise PublicationError(
            f"publication Plan {plan.plan_id} is stale; review a new Plan before Publish"
        )

    try:
        contract = resolve_repository_contract(
            plan.repository, standards_root=standards_root
        )
    except (ContractError, StandardsError) as exc:
        raise PublicationError(str(exc)) from exc

    steps = plan.steps
    commit_environment = os.environ.copy()
    git_date = f"{plan.commit.timestamp} {plan.commit.timezone}"
    commit_environment.update(
        {
            "GIT_AUTHOR_NAME": plan.commit.author_name,
            "GIT_AUTHOR_EMAIL": plan.commit.author_email,
            "GIT_AUTHOR_DATE": git_date,
            "GIT_COMMITTER_NAME": plan.commit.author_name,
            "GIT_COMMITTER_EMAIL": plan.commit.author_email,
            "GIT_COMMITTER_DATE": git_date,
        }
    )
    with tempfile.TemporaryDirectory(prefix="first-publication-publish-") as directory:
        temporary_index = Path(directory) / "index"
        commit_environment["GIT_INDEX_FILE"] = str(temporary_index)
        existing_index = plan.git_directory / "index"
        if existing_index.is_file():
            try:
                shutil.copyfile(existing_index, temporary_index)
            except OSError as exc:
                return _failed_report(
                    steps,
                    0,
                    f"cannot copy the prepared Git index: {exc}",
                    commit_oid=None,
                )
        staged = _git(
            plan.repository,
            "add",
            "--all",
            environment=commit_environment,
        )
        if staged.returncode != 0:
            return _failed_report(
                steps,
                0,
                staged.stderr.strip() or staged.stdout.strip(),
                commit_oid=None,
            )
        tree = _git(plan.repository, "write-tree", environment=commit_environment)
        if tree.returncode != 0 or tree.stdout.strip() != plan.commit.tree_oid:
            return _failed_report(
                steps,
                0,
                tree.stderr.strip()
                or tree.stdout.strip()
                or "prepared content no longer matches the confirmed Plan",
                commit_oid=None,
            )
        committed = _git(
            plan.repository,
            "commit-tree",
            plan.commit.tree_oid,
            environment=commit_environment,
            input_text=f"{plan.commit.message}\n",
        )
        if committed.returncode != 0:
            return _failed_report(
                steps,
                0,
                committed.stderr.strip() or committed.stdout.strip(),
                commit_oid=None,
            )
        commit_oid = committed.stdout.strip()
        metadata_error = _commit_metadata_error(plan, commit_oid)
        if metadata_error:
            return _failed_report(
                steps,
                0,
                metadata_error,
                commit_oid=commit_oid,
            )
        index_lock = plan.git_directory / "index.lock"
        lock_created = False
        try:
            descriptor = os.open(
                index_lock,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o666,
            )
            lock_created = True
            with temporary_index.open("rb") as source, os.fdopen(
                descriptor, "wb"
            ) as destination:
                shutil.copyfileobj(source, destination)
        except OSError as exc:
            if lock_created:
                try:
                    index_lock.unlink()
                except OSError:
                    pass
            return _failed_report(
                steps,
                0,
                f"cannot install the initial commit index: {exc}",
                commit_oid=commit_oid,
            )
        updated = _git(
            plan.repository,
            "update-ref",
            f"refs/heads/{plan.branch}",
            commit_oid,
            "",
        )
        if updated.returncode != 0:
            reference = f"refs/heads/{plan.branch}"
            current = _git(
                plan.repository,
                "for-each-ref",
                "--format=%(refname)%00%(objectname)",
                reference,
            )
            if current.returncode != 0:
                try:
                    index_lock.unlink()
                except OSError:
                    pass
                update_error = updated.stderr.strip() or updated.stdout.strip()
                observation_error = (
                    current.stderr.strip()
                    or current.stdout.strip()
                    or "ref observation failed"
                )
                return _uncertain_report(
                    steps,
                    0,
                    "local branch update failed and re-observation failed; "
                    f"completion is unknown: {update_error}; {observation_error}",
                    commit_oid=commit_oid,
                )
            current_oid = None
            for line in current.stdout.splitlines():
                ref_name, separator, object_id = line.partition("\0")
                if separator and ref_name == reference:
                    current_oid = object_id
                    break
            if current_oid is None:
                try:
                    index_lock.unlink()
                except OSError:
                    pass
                return _failed_report(
                    steps,
                    0,
                    updated.stderr.strip() or updated.stdout.strip(),
                    commit_oid=commit_oid,
                )
            if current_oid != commit_oid:
                try:
                    index_lock.unlink()
                except OSError:
                    pass
                return _uncertain_report(
                    steps,
                    0,
                    "local branch update failed and re-observation found an "
                    "unexpected commit",
                    commit_oid=commit_oid,
                )
        try:
            os.replace(index_lock, existing_index)
        except OSError as exc:
            try:
                index_lock.unlink()
            except OSError:
                pass
            return _failed_report(
                steps,
                1,
                f"cannot install the initial Git index: {exc}",
                commit_oid=commit_oid,
            )

    pushed = _git(
        plan.repository,
        "push",
        "--set-upstream",
        "origin",
        plan.branch,
    )
    if pushed.returncode != 0:
        remote_oid, observation_error = _remote_main_observation(plan)
        if remote_oid != commit_oid:
            push_error = pushed.stderr.strip() or pushed.stdout.strip()
            if observation_error:
                return _uncertain_report(
                    steps,
                    2,
                    f"{push_error}; completion is unknown because re-observation "
                    f"failed: {observation_error}",
                    commit_oid=commit_oid,
                )
            return _failed_report(
                steps,
                2,
                push_error,
                commit_oid=commit_oid,
            )

    operations = plan.live_delta.operations
    for live_index, operation in enumerate(operations):
        operation_index = live_index + 3
        try:
            adapter.apply(operation)
        except (StandardsError, OSError) as exc:
            state, observation_error = _live_operation_state(
                contract,
                adapter,
                operation,
                operations[live_index + 1 :],
            )
            if state == "completed":
                continue
            if state == "unknown":
                return _uncertain_report(
                    steps,
                    operation_index,
                    f"{exc}; completion is unknown: {observation_error}",
                    commit_oid=commit_oid,
                )
            return _failed_report(
                steps,
                operation_index,
                str(exc),
                commit_oid=commit_oid,
            )

    content_index = len(steps) - 2
    content_error = _verify_committed_content(plan, contract, commit_oid)
    if content_error:
        return _failed_report(
            steps,
            content_index,
            content_error,
            commit_oid=commit_oid,
        )
    live_error = _verify_live_state(plan, contract, adapter)
    if live_error:
        return _failed_report(
            steps,
            content_index + 1,
            live_error,
            commit_oid=commit_oid,
        )
    return PublicationReport(
        completed=steps,
        failed=None,
        uncertain=None,
        remaining=(),
        error=None,
        commit_oid=commit_oid,
        standards_complete=True,
    )
