"""Reconcile one normalized repository contract with observed GitHub state."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol
from urllib.parse import quote

from .repository_content import StandardsError


SETTINGS_MAPPING = {
    "delete-branch-on-merge": "delete_branch_on_merge",
    "allow-squash-merge": "allow_squash_merge",
    "allow-merge-commit": "allow_merge_commit",
    "allow-rebase-merge": "allow_rebase_merge",
    "squash-merge-commit-title": "squash_merge_commit_title",
    "squash-merge-commit-message": "squash_merge_commit_message",
}
FEATURES_MAPPING = {
    "issues": "has_issues",
    "projects": "has_projects",
    "wiki": "has_wiki",
}
GRAPHQL_SETTINGS_MAPPING = {
    "delete_branch_on_merge": "deleteBranchOnMerge",
    "allow_squash_merge": "squashMergeAllowed",
    "allow_merge_commit": "mergeCommitAllowed",
    "allow_rebase_merge": "rebaseMergeAllowed",
    "squash_merge_commit_title": "squashMergeCommitTitle",
    "squash_merge_commit_message": "squashMergeCommitMessage",
}
REPOSITORY_SETTINGS_QUERY = (
    "query($owner:String!,$name:String!){"
    "repository(owner:$owner,name:$name){"
    "deleteBranchOnMerge mergeCommitAllowed rebaseMergeAllowed "
    "squashMergeAllowed squashMergeCommitTitle squashMergeCommitMessage"
    "}}"
)


class NormalizedGitHubContract(Protocol):
    def as_mapping(self) -> dict[str, Any]: ...


class GitHubRepositoryContract(Protocol):
    @property
    def github(self) -> NormalizedGitHubContract: ...

    @property
    def required_labels(self) -> tuple[str, ...]: ...


class GitHubLifecycle(Enum):
    """Lifecycle state that determines which GitHub requirements are applicable."""

    PREPARED = "prepared"
    PUBLISHED = "published"


@dataclass(frozen=True)
class GitHubSnapshot:
    """The complete GitHub state used by one reconciliation decision."""

    repository: dict[str, Any]
    branches: tuple[dict[str, Any], ...]
    label_names: frozenset[str]
    rulesets: tuple[dict[str, Any], ...]
    lifecycle: GitHubLifecycle = GitHubLifecycle.PUBLISHED


@dataclass(frozen=True)
class GitHubCorrection:
    description: str
    method: str
    endpoint: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class GitHubDifference:
    findings: tuple[str, ...]
    operations: tuple[GitHubCorrection, ...] = ()
    pending: bool = False
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class GitHubReconciliation:
    """One shared source for repository assessment findings and GitHub corrections."""

    repository: str
    differences: tuple[GitHubDifference, ...]

    @property
    def findings(self) -> tuple[str, ...]:
        return tuple(
            finding
            for difference in self.differences
            for finding in difference.findings
        )

    @property
    def operations(self) -> tuple[GitHubCorrection, ...]:
        return tuple(
            operation
            for difference in self.differences
            for operation in difference.operations
        )

    @property
    def pending_findings(self) -> tuple[str, ...]:
        return tuple(
            finding
            for difference in self.differences
            if difference.pending
            for finding in difference.findings
        )

    @property
    def blockers(self) -> tuple[str, ...]:
        return tuple(
            blocker
            for difference in self.differences
            for blocker in difference.blockers
        )

    @property
    def clean(self) -> bool:
        return not self.differences


@dataclass(frozen=True)
class GitHubApplicationReport:
    completed: tuple[GitHubCorrection, ...]
    failed: GitHubCorrection | None
    remaining: tuple[GitHubCorrection, ...]
    error: str | None

    @property
    def complete(self) -> bool:
        return self.failed is None


class GitHubAdapter:
    """Replaceable boundary for observing and mutating declared GitHub state."""

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        raise NotImplementedError

    def _collect_pages(self, endpoint: str) -> list[Any]:
        results: list[Any] = []
        page = 1
        separator = "&" if "?" in endpoint else "?"
        while True:
            page_items = self.request(
                "GET", f"{endpoint}{separator}per_page=100&page={page}"
            )
            if not isinstance(page_items, list):
                resource = endpoint.rsplit("/", 1)[-1]
                raise StandardsError(f"GitHub {resource} API must return a list")
            results.extend(page_items)
            if len(page_items) < 100:
                return results
            page += 1

    def _observe_repository(self, repository_name: str) -> dict[str, Any]:
        repository = self.request("GET", f"repos/{repository_name}")
        if not isinstance(repository, dict):
            raise StandardsError("GitHub repository API must return an object")
        return dict(repository)

    def observe(
        self,
        contract: GitHubRepositoryContract,
        *,
        lifecycle: GitHubLifecycle = GitHubLifecycle.PUBLISHED,
    ) -> GitHubSnapshot:
        """Read every GitHub resource needed by one reconciliation pass."""

        github = contract.github.as_mapping()
        endpoint = f"repos/{github['repository']}"
        repository = self._observe_repository(github["repository"])

        labels = self._collect_pages(f"{endpoint}/labels")
        label_names = frozenset(
            label["name"]
            for label in labels
            if isinstance(label, dict)
            and isinstance(label.get("name"), str)
            and label["name"]
        )

        summaries = self._collect_pages(
            f"{endpoint}/rulesets?includes_parents=false"
        )
        observed_rulesets = [
            dict(item)
            for item in summaries
            if isinstance(item, dict)
            and item.get("source_type", "Repository") == "Repository"
            and item.get("source", github["repository"])
            == github["repository"]
        ]
        expected_ruleset = github["ruleset"]
        if expected_ruleset is not None:
            summary = next(
                (
                    item
                    for item in observed_rulesets
                    if item.get("name") == expected_ruleset["name"]
                ),
                None,
            )
            if summary is not None:
                ruleset = self.request(
                    "GET", f"{endpoint}/rulesets/{summary['id']}"
                )
                if not isinstance(ruleset, dict):
                    raise StandardsError("GitHub ruleset API must return an object")
                if "bypass_actors" not in ruleset:
                    raise StandardsError(
                        "GitHub ruleset bypass actors are not observable; complete "
                        "reconciliation requires Administration (write) permission"
                    )
                observed_rulesets[observed_rulesets.index(summary)] = {
                    **summary,
                    **ruleset,
                }

        branches = self._collect_pages(f"{endpoint}/branches")
        if not all(
            isinstance(branch, dict)
            and isinstance(branch.get("name"), str)
            and branch["name"]
            for branch in branches
        ):
            raise StandardsError("GitHub branches API must return named objects")

        return GitHubSnapshot(
            repository=dict(repository),
            branches=tuple(dict(branch) for branch in branches),
            label_names=label_names,
            rulesets=tuple(observed_rulesets),
            lifecycle=lifecycle,
        )

    def apply(self, operation: GitHubCorrection) -> Any:
        return self.request(
            operation.method, operation.endpoint, operation.payload
        )


class GitHubCliAdapter(GitHubAdapter):
    """Read and write GitHub JSON through the authenticated GitHub CLI."""

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or os.environ.get("REPOSITORY_STANDARDS_GH", "gh")

    def _run_json(
        self,
        command: list[str],
        *,
        request_input: str | None,
        failure_context: str,
        permission: str,
    ) -> Any:
        if shutil.which(self.executable) is None:
            raise StandardsError("GitHub corrections require the GitHub CLI: gh")
        result = subprocess.run(
            command,
            input=request_input,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            guidance = ""
            if any(
                marker in message.lower()
                for marker in (
                    "401",
                    "403",
                    "404",
                    "bad credentials",
                    "forbidden",
                    "not accessible",
                    "not found",
                    "unauthorized",
                )
            ):
                guidance = (
                    "; authenticate with `gh auth login` using a token with "
                    f"Issues ({permission}) and Administration ({permission}) "
                    "permission for the repository"
                )
            raise StandardsError(f"{failure_context}: {message}{guidance}")
        if not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise StandardsError(f"{failure_context}: invalid JSON") from exc

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        command = [self.executable, "api", endpoint]
        request_input: str | None = None
        if method != "GET":
            command.extend(["--method", method, "--input", "-"])
            request_input = json.dumps(payload or {})
        return self._run_json(
            command,
            request_input=request_input,
            failure_context=f"GitHub API {method} failed for {endpoint}",
            permission="read" if method == "GET" else "write",
        )

    def _observe_repository(self, repository_name: str) -> dict[str, Any]:
        repository = super()._observe_repository(repository_name)
        if all(
            repository.get(field) is not None
            for field in GRAPHQL_SETTINGS_MAPPING
        ):
            return repository

        owner, name = repository_name.split("/", 1)
        response = self._run_json(
            [
                self.executable,
                "api",
                "graphql",
                "-f",
                f"query={REPOSITORY_SETTINGS_QUERY}",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={name}",
            ],
            request_input=None,
            failure_context=(
                f"GitHub GraphQL repository settings query failed for "
                f"{repository_name}"
            ),
            permission="read",
        )
        graphql_repository = (
            response.get("data", {}).get("repository")
            if isinstance(response, dict)
            else None
        )
        if not isinstance(graphql_repository, dict):
            raise StandardsError(
                "GitHub GraphQL repository settings query must return an object"
            )
        if any(
            graphql_repository.get(field) is None
            for field in GRAPHQL_SETTINGS_MAPPING.values()
        ):
            raise StandardsError(
                "GitHub GraphQL repository settings are not completely observable"
            )
        return {
            **repository,
            **{
                rest_field: graphql_repository[graphql_field]
                for rest_field, graphql_field in GRAPHQL_SETTINGS_MAPPING.items()
            },
        }


def _rule_by_type(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any] | None:
    return next(
        (
            rule
            for rule in ruleset.get("rules", [])
            if isinstance(rule, dict) and rule.get("type") == rule_type
        ),
        None,
    )


def _ruleset_findings(
    expected: dict[str, Any], actual: dict[str, Any], default_branch: str
) -> list[str]:
    findings: list[str] = []
    if actual.get("target") != "branch":
        findings.append("github.ruleset must target branches")
    if actual.get("enforcement") != "active":
        findings.append("github.ruleset must be actively enforced")
    conditions = actual.get("conditions", {}).get("ref_name", {})
    included = set(conditions.get("include", []))
    if included not in (
        {"~DEFAULT_BRANCH"},
        {f"refs/heads/{default_branch}"},
    ):
        findings.append("github.ruleset must target only the default branch")
    if conditions.get("exclude"):
        findings.append("github.ruleset must not exclude branches from its target")

    if "bypass_actors" not in actual:
        raise StandardsError(
            "GitHub ruleset bypass actors are required in an observed snapshot"
        )
    if bool(actual["bypass_actors"]) != expected["allow-bypass-actors"]:
        findings.append(
            "github.ruleset bypass actors do not match allow-bypass-actors"
        )
    if (_rule_by_type(actual, "deletion") is not None) != expected[
        "prevent-deletion"
    ]:
        findings.append(
            "github.ruleset deletion protection does not match the manifest"
        )
    if (_rule_by_type(actual, "non_fast_forward") is not None) != expected[
        "prevent-force-push"
    ]:
        findings.append(
            "github.ruleset force-push protection does not match the manifest"
        )

    pull_request = _rule_by_type(actual, "pull_request")
    if pull_request is None:
        findings.append("github.ruleset is missing the pull_request rule")
    else:
        parameters = pull_request.get("parameters", {})
        if parameters.get("required_approving_review_count") != expected[
            "required-approvals"
        ]:
            findings.append(
                "github.ruleset required approvals do not match the manifest"
            )
        if set(parameters.get("allowed_merge_methods", [])) != set(
            expected["allowed-merge-methods"]
        ):
            findings.append(
                "github.ruleset allowed merge methods do not match the manifest"
            )

    status_checks = _rule_by_type(actual, "required_status_checks")
    if status_checks is None:
        findings.append("github.ruleset is missing the required_status_checks rule")
    else:
        parameters = status_checks.get("parameters", {})
        if parameters.get("strict_required_status_checks_policy") != expected[
            "require-current-branch"
        ]:
            findings.append(
                "github.ruleset current-branch requirement does not match the manifest"
            )
        contexts = {
            item.get("context")
            for item in parameters.get("required_status_checks", [])
            if isinstance(item, dict) and item.get("context")
        }
        if contexts != set(expected["required-status-checks"]):
            findings.append(
                "github.ruleset required status checks are "
                f"{sorted(contexts)!r}; expected "
                f"{sorted(expected['required-status-checks'])!r}"
            )
    return findings


def _ruleset_payload(
    expected: dict[str, Any], actual: dict[str, Any] | None = None
) -> dict[str, Any]:
    actual_rules = list((actual or {}).get("rules", []))
    managed_rule_types = {
        "deletion",
        "non_fast_forward",
        "pull_request",
        "required_status_checks",
    }
    rules = [
        dict(rule)
        for rule in actual_rules
        if isinstance(rule, dict) and rule.get("type") not in managed_rule_types
    ]
    if expected["prevent-deletion"]:
        rules.append({"type": "deletion"})
    if expected["prevent-force-push"]:
        rules.append({"type": "non_fast_forward"})

    actual_pull_request = _rule_by_type(actual or {}, "pull_request") or {}
    pull_request_parameters = dict(actual_pull_request.get("parameters", {}))
    if actual is None:
        pull_request_parameters.update(
            {
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
            }
        )
    pull_request_parameters.update(
        {
            "required_approving_review_count": expected["required-approvals"],
            "allowed_merge_methods": expected["allowed-merge-methods"],
        }
    )

    actual_status_checks = _rule_by_type(actual or {}, "required_status_checks") or {}
    status_check_parameters = dict(actual_status_checks.get("parameters", {}))
    actual_checks = {
        item.get("context"): item
        for item in status_check_parameters.get("required_status_checks", [])
        if isinstance(item, dict) and isinstance(item.get("context"), str)
    }
    status_check_parameters.update(
        {
            "strict_required_status_checks_policy": expected[
                "require-current-branch"
            ],
            "required_status_checks": [
                dict(actual_checks.get(context, {"context": context}))
                for context in expected["required-status-checks"]
            ],
        }
    )
    rules.extend(
        [
            {"type": "pull_request", "parameters": pull_request_parameters},
            {
                "type": "required_status_checks",
                "parameters": status_check_parameters,
            },
        ]
    )
    conditions = dict((actual or {}).get("conditions", {}))
    conditions["ref_name"] = {"include": ["~DEFAULT_BRANCH"], "exclude": []}
    return {
        "name": expected["name"],
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": conditions,
        "rules": rules,
    }


def reconcile_github(
    contract: GitHubRepositoryContract, snapshot: GitHubSnapshot
) -> GitHubReconciliation:
    """Return every applicable difference without reading or writing GitHub."""

    github = contract.github.as_mapping()
    repository_name = github["repository"]
    endpoint = f"repos/{repository_name}"
    differences: list[GitHubDifference] = []

    repository_findings: list[str] = []
    repository_payload: dict[str, Any] = {}
    if snapshot.lifecycle is GitHubLifecycle.PREPARED:
        differences.append(
            GitHubDifference(
                (
                    "github.default-branch is pending first publication; "
                    f"expected {github['default-branch']!r}",
                ),
                pending=True,
            )
        )
    elif (
        snapshot.repository.get("default_branch") != github["default-branch"]
        or not any(
            branch.get("name") == github["default-branch"]
            for branch in snapshot.branches
        )
    ):
        if snapshot.repository.get("default_branch") == github["default-branch"]:
            default_branch_finding = (
                f"github.default-branch {github['default-branch']!r} is not established"
            )
        else:
            default_branch_finding = (
                f"github.default-branch is "
                f"{snapshot.repository.get('default_branch')!r}; "
                f"expected {github['default-branch']!r}"
            )
        default_branch = github["default-branch"]
        branch_exists = any(
            branch.get("name") == default_branch for branch in snapshot.branches
        )
        differences.append(
            GitHubDifference(
                (default_branch_finding,),
                (
                    GitHubCorrection(
                        f"ESTABLISH default branch {github['default-branch']!r}",
                        "PATCH",
                        endpoint,
                        {"default_branch": github["default-branch"]},
                    ),
                ),
                blockers=(
                    ()
                    if branch_exists
                    else (
                        f"create or publish default branch {default_branch!r} "
                        "before reconciliation",
                    )
                ),
            )
        )

    for contract_name, api_name in SETTINGS_MAPPING.items():
        expected = github["settings"][contract_name]
        if snapshot.repository.get(api_name) != expected:
            repository_findings.append(
                f"github.settings.{contract_name} is "
                f"{snapshot.repository.get(api_name)!r}; expected {expected!r}"
            )
            repository_payload[api_name] = expected

    expected_features = github["features"]
    for contract_name, api_name in FEATURES_MAPPING.items():
        expected = expected_features[contract_name]
        if snapshot.repository.get(api_name) != expected:
            repository_findings.append(
                f"github.features.{contract_name} is "
                f"{snapshot.repository.get(api_name)!r}; expected {expected!r}"
            )
            repository_payload[api_name] = expected

    if repository_findings:
        differences.append(
            GitHubDifference(
                tuple(repository_findings),
                (
                    GitHubCorrection(
                        "UPDATE   repository settings",
                        "PATCH",
                        endpoint,
                        repository_payload,
                    ),
                ),
            )
        )

    actual_labels_by_identity = {
        label.casefold(): label for label in snapshot.label_names
    }
    missing_labels: list[str] = []
    incorrectly_cased_labels: list[tuple[str, str]] = []
    label_operations: list[GitHubCorrection] = []
    for label in sorted(contract.required_labels):
        actual_label = actual_labels_by_identity.get(label.casefold())
        if actual_label is None:
            missing_labels.append(label)
            label_operations.append(
                GitHubCorrection(
                    f"CREATE   label {label!r}",
                    "POST",
                    f"{endpoint}/labels",
                    {
                        "name": label,
                        "color": "ededed",
                        "description": "Required by repository standards",
                    },
                )
            )
        elif actual_label != label:
            incorrectly_cased_labels.append((actual_label, label))
            label_operations.append(
                GitHubCorrection(
                    f"UPDATE   label {actual_label!r} to {label!r}",
                    "PATCH",
                    f"{endpoint}/labels/{quote(actual_label, safe='')}",
                    {"new_name": label},
                )
            )
    label_findings: list[str] = []
    if missing_labels:
        label_findings.append(
            f"github required labels are missing: {missing_labels!r}"
        )
    if incorrectly_cased_labels:
        label_findings.append(
            "github required labels have incorrect casing: "
            f"{incorrectly_cased_labels!r}"
        )
    if label_findings:
        differences.append(
            GitHubDifference(tuple(label_findings), tuple(label_operations))
        )

    expected_ruleset = github["ruleset"]
    if expected_ruleset is not None:
        if snapshot.lifecycle is GitHubLifecycle.PREPARED:
            differences.append(
                GitHubDifference(
                    (
                        f"github.ruleset {expected_ruleset['name']!r} is pending "
                        "first publication",
                    ),
                    pending=True,
                )
            )
        else:
            actual_ruleset = next(
                (
                    ruleset
                    for ruleset in snapshot.rulesets
                    if ruleset.get("name") == expected_ruleset["name"]
                ),
                None,
            )
            if actual_ruleset is None:
                differences.append(
                    GitHubDifference(
                        (f"github.ruleset {expected_ruleset['name']!r} is missing",),
                        (
                            GitHubCorrection(
                                f"CREATE   ruleset {expected_ruleset['name']!r}",
                                "POST",
                                f"{endpoint}/rulesets",
                                _ruleset_payload(expected_ruleset),
                            ),
                        ),
                    )
                )
            else:
                ruleset_findings = _ruleset_findings(
                    expected_ruleset, actual_ruleset, github["default-branch"]
                )
                if ruleset_findings:
                    differences.append(
                        GitHubDifference(
                            tuple(ruleset_findings),
                            (
                                GitHubCorrection(
                                    f"UPDATE   ruleset {expected_ruleset['name']!r}",
                                    "PUT",
                                    f"{endpoint}/rulesets/{actual_ruleset['id']}",
                                    _ruleset_payload(expected_ruleset, actual_ruleset),
                                ),
                            ),
                        )
                    )

    return GitHubReconciliation(repository_name, tuple(differences))

def apply_github_reconciliation(
    reconciliation: GitHubReconciliation, adapter: GitHubAdapter
) -> GitHubApplicationReport:
    """Apply the GitHub reconciliation in order without rolling back completed operations."""

    operations = reconciliation.operations
    for index, operation in enumerate(operations):
        try:
            adapter.apply(operation)
        except StandardsError as exc:
            return GitHubApplicationReport(
                completed=operations[:index],
                failed=operation,
                remaining=operations[index + 1 :],
                error=str(exc),
            )
    return GitHubApplicationReport(
        completed=operations,
        failed=None,
        remaining=(),
        error=None,
    )
