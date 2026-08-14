"""Inspect live GitHub repository settings against a manifest contract."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .standards import StandardsError


JsonFetcher = Callable[[str], Any]
SETTINGS_MAPPING = {
    "delete-branch-on-merge": "delete_branch_on_merge",
    "allow-squash-merge": "allow_squash_merge",
    "allow-merge-commit": "allow_merge_commit",
    "allow-rebase-merge": "allow_rebase_merge",
}


@dataclass(frozen=True)
class LiveOperation:
    description: str
    method: str
    endpoint: str
    payload: dict[str, Any]


class GitHubCliTransport:
    """Read and write GitHub JSON through the authenticated GitHub CLI."""

    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or os.environ.get("REPOSITORY_STANDARDS_GH", "gh")

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        if shutil.which(self.executable) is None:
            raise StandardsError("live GitHub operations require the GitHub CLI: gh")
        command = [self.executable, "api", endpoint]
        request_input: str | None = None
        if method != "GET":
            command.extend(["--method", method, "--input", "-"])
            request_input = json.dumps(payload or {})
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
                    "; authenticate with `gh auth login` using a token with Issues (write) "
                    "and Administration (write) permission for the repository"
                )
            raise StandardsError(
                f"GitHub API {method} failed for {endpoint}: {message}{guidance}"
            )
        if not result.stdout.strip():
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise StandardsError(
                f"GitHub API returned invalid JSON for {method} {endpoint}"
            ) from exc


def gh_json(endpoint: str) -> Any:
    return GitHubCliTransport().request("GET", endpoint)


def _rule_by_type(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any] | None:
    return next(
        (rule for rule in ruleset.get("rules", []) if rule.get("type") == rule_type),
        None,
    )


def _compare_settings(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for expected_name, actual_name in SETTINGS_MAPPING.items():
        if actual.get(actual_name) != expected[expected_name]:
            errors.append(
                f"github.settings.{expected_name} is {actual.get(actual_name)!r}; "
                f"expected {expected[expected_name]!r}"
            )
    return errors


def _repository_label_names(repository: str, fetch_json: JsonFetcher) -> set[str]:
    names: set[str] = set()
    page = 1
    while True:
        labels = fetch_json(f"repos/{repository}/labels?per_page=100&page={page}")
        if not isinstance(labels, list):
            raise StandardsError("GitHub labels API must return a list")
        names.update(
            label["name"]
            for label in labels
            if isinstance(label, dict)
            and isinstance(label.get("name"), str)
            and label["name"]
        )
        if len(labels) < 100:
            return names
        page += 1


def _compare_ruleset(
    expected: dict[str, Any], actual: dict[str, Any], default_branch: str
) -> list[str]:
    errors: list[str] = []
    if actual.get("target") not in {None, "branch"}:
        errors.append("github.ruleset must target branches")
    if actual.get("enforcement") != "active":
        errors.append("github.ruleset must be actively enforced")
    conditions = actual.get("conditions", {}).get("ref_name", {})
    included = set(conditions.get("include", []))
    if not ({"~DEFAULT_BRANCH", f"refs/heads/{default_branch}"} & included):
        errors.append("github.ruleset must include the default branch")
    if conditions.get("exclude"):
        errors.append("github.ruleset must not exclude branches from its target")

    bypass_actors = actual.get("bypass_actors", [])
    has_bypass = bool(bypass_actors)
    if has_bypass != expected["allow-bypass-actors"]:
        errors.append(
            "github.ruleset bypass actors do not match allow-bypass-actors"
        )

    deletion = _rule_by_type(actual, "deletion") is not None
    if deletion != expected["prevent-deletion"]:
        errors.append("github.ruleset deletion protection does not match the manifest")
    force_push = _rule_by_type(actual, "non_fast_forward") is not None
    if force_push != expected["prevent-force-push"]:
        errors.append("github.ruleset force-push protection does not match the manifest")

    pull_request = _rule_by_type(actual, "pull_request")
    if pull_request is None:
        errors.append("github.ruleset is missing the pull_request rule")
    else:
        parameters = pull_request.get("parameters", {})
        if parameters.get("required_approving_review_count") != expected[
            "required-approvals"
        ]:
            errors.append("github.ruleset required approvals do not match the manifest")
        actual_methods = set(parameters.get("allowed_merge_methods", []))
        if actual_methods != set(expected["allowed-merge-methods"]):
            errors.append("github.ruleset allowed merge methods do not match the manifest")

    status_checks = _rule_by_type(actual, "required_status_checks")
    if status_checks is None:
        errors.append("github.ruleset is missing the required_status_checks rule")
    else:
        parameters = status_checks.get("parameters", {})
        if parameters.get("strict_required_status_checks_policy") != expected[
            "require-current-branch"
        ]:
            errors.append(
                "github.ruleset current-branch requirement does not match the manifest"
            )
        contexts = {
            item.get("context")
            for item in parameters.get("required_status_checks", [])
            if item.get("context")
        }
        if contexts != set(expected["required-status-checks"]):
            errors.append(
                "github.ruleset required status checks are "
                f"{sorted(contexts)!r}; expected "
                f"{sorted(expected['required-status-checks'])!r}"
            )
    return errors


def inspect_live_github(
    contract: dict[str, Any],
    fetch_json: JsonFetcher = gh_json,
    *,
    required_labels: Iterable[str] = (),
) -> list[str]:
    repository = contract["repository"]
    repository_data = fetch_json(f"repos/{repository}")
    errors: list[str] = []
    if repository_data.get("default_branch") != contract["default-branch"]:
        errors.append(
            f"github.default-branch is {repository_data.get('default_branch')!r}; "
            f"expected {contract['default-branch']!r}"
        )
    errors.extend(_compare_settings(contract["settings"], repository_data))

    required_label_names = set(required_labels)
    if required_label_names:
        actual_label_names = _repository_label_names(repository, fetch_json)
        missing_labels = sorted(required_label_names - actual_label_names)
        if missing_labels:
            errors.append(f"github required labels are missing: {missing_labels!r}")

    expected_ruleset = contract.get("ruleset")
    if expected_ruleset is None:
        return errors
    summaries = fetch_json(f"repos/{repository}/rulesets")
    summary = next(
        (item for item in summaries if item.get("name") == expected_ruleset["name"]),
        None,
    )
    if summary is None:
        errors.append(f"github.ruleset {expected_ruleset['name']!r} is missing")
        return errors
    ruleset = fetch_json(f"repos/{repository}/rulesets/{summary['id']}")
    errors.extend(
        _compare_ruleset(expected_ruleset, ruleset, contract["default-branch"])
    )
    return errors


def _ruleset_payload(
    expected: dict[str, Any],
    actual: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if expected["allow-bypass-actors"]:
        bypass_actors = list((actual or {}).get("bypass_actors", []))
        if not bypass_actors:
            raise StandardsError(
                "github.ruleset.allow-bypass-actors is true but no existing bypass "
                "actors can be preserved"
            )
    else:
        bypass_actors = []
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
            {
                "type": "pull_request",
                "parameters": pull_request_parameters,
            },
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
        "bypass_actors": bypass_actors,
        "conditions": conditions,
        "rules": rules,
    }


def plan_live_github(
    contract: dict[str, Any],
    transport: GitHubCliTransport,
    *,
    required_labels: Iterable[str] = (),
) -> list[LiveOperation]:
    repository = contract["repository"]
    repository_endpoint = f"repos/{repository}"
    repository_data = transport.request("GET", repository_endpoint)
    operations: list[LiveOperation] = []

    settings_payload: dict[str, Any] = {}
    if repository_data.get("default_branch") != contract["default-branch"]:
        settings_payload["default_branch"] = contract["default-branch"]
    for manifest_name, api_name in SETTINGS_MAPPING.items():
        expected_value = contract["settings"][manifest_name]
        if repository_data.get(api_name) != expected_value:
            settings_payload[api_name] = expected_value
    if settings_payload:
        operations.append(
            LiveOperation(
                "UPDATE   repository settings",
                "PATCH",
                repository_endpoint,
                settings_payload,
            )
        )

    actual_labels = _repository_label_names(
        repository,
        lambda endpoint: transport.request("GET", endpoint),
    )
    for label in sorted(set(required_labels) - actual_labels):
        operations.append(
            LiveOperation(
                f"CREATE   label {label!r}",
                "POST",
                f"{repository_endpoint}/labels",
                {
                    "name": label,
                    "color": "ededed",
                    "description": "Required by repository standards",
                },
            )
        )

    expected_ruleset = contract.get("ruleset")
    if expected_ruleset is None:
        return operations
    summaries = transport.request("GET", f"{repository_endpoint}/rulesets")
    if not isinstance(summaries, list):
        raise StandardsError("GitHub rulesets API must return a list")
    summary = next(
        (
            item
            for item in summaries
            if isinstance(item, dict) and item.get("name") == expected_ruleset["name"]
        ),
        None,
    )
    if summary is None:
        operations.append(
            LiveOperation(
                f"CREATE   ruleset {expected_ruleset['name']!r}",
                "POST",
                f"{repository_endpoint}/rulesets",
                _ruleset_payload(expected_ruleset),
            )
        )
        return operations
    actual_ruleset = transport.request(
        "GET", f"{repository_endpoint}/rulesets/{summary['id']}"
    )
    if _compare_ruleset(
        expected_ruleset, actual_ruleset, contract["default-branch"]
    ):
        operations.append(
            LiveOperation(
                f"UPDATE   ruleset {expected_ruleset['name']!r}",
                "PUT",
                f"{repository_endpoint}/rulesets/{summary['id']}",
                _ruleset_payload(expected_ruleset, actual_ruleset),
            )
        )
    return operations
