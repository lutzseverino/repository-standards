"""Inspect live GitHub repository settings against a manifest contract."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Callable, Iterable

from .standards import StandardsError


JsonFetcher = Callable[[str], Any]


def gh_json(endpoint: str) -> Any:
    if shutil.which("gh") is None:
        raise StandardsError("live audit requires the GitHub CLI: gh")
    result = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise StandardsError(f"GitHub API request failed for {endpoint}: {message}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise StandardsError(f"GitHub API returned invalid JSON for {endpoint}") from exc


def _rule_by_type(ruleset: dict[str, Any], rule_type: str) -> dict[str, Any] | None:
    return next(
        (rule for rule in ruleset.get("rules", []) if rule.get("type") == rule_type),
        None,
    )


def _compare_settings(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    mappings = {
        "delete-branch-on-merge": "delete_branch_on_merge",
        "allow-squash-merge": "allow_squash_merge",
        "allow-merge-commit": "allow_merge_commit",
        "allow-rebase-merge": "allow_rebase_merge",
    }
    errors: list[str] = []
    for expected_name, actual_name in mappings.items():
        if actual.get(actual_name) != expected[expected_name]:
            errors.append(
                f"github.settings.{expected_name} is {actual.get(actual_name)!r}; "
                f"expected {expected[expected_name]!r}"
            )
    return errors


def _compare_ruleset(
    expected: dict[str, Any], actual: dict[str, Any], default_branch: str
) -> list[str]:
    errors: list[str] = []
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
        actual_label_names: set[str] = set()
        page = 1
        while True:
            labels = fetch_json(
                f"repos/{repository}/labels?per_page=100&page={page}"
            )
            if not isinstance(labels, list):
                raise StandardsError("GitHub labels API must return a list")
            actual_label_names.update(
                label["name"]
                for label in labels
                if isinstance(label, dict)
                and isinstance(label.get("name"), str)
                and label["name"]
            )
            if len(labels) < 100:
                break
            page += 1
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
