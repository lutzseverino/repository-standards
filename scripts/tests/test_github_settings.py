from __future__ import annotations

import unittest
import sys
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.github_settings import inspect_live_github


class GitHubSettingsTests(unittest.TestCase):
    def contract(self) -> dict[str, Any]:
        return {
            "repository": "owner/example",
            "default-branch": "main",
            "settings": {
                "delete-branch-on-merge": True,
                "allow-squash-merge": True,
                "allow-merge-commit": False,
                "allow-rebase-merge": False,
            },
            "ruleset": {
                "name": "Protect main",
                "required-status-checks": [
                    "CI / Required",
                ],
                "require-current-branch": True,
                "required-approvals": 0,
                "allowed-merge-methods": ["squash"],
                "prevent-deletion": True,
                "prevent-force-push": True,
                "allow-bypass-actors": False,
            },
        }

    def responses(self) -> dict[str, Any]:
        return {
            "repos/owner/example": {
                "default_branch": "main",
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
            },
            "repos/owner/example/rulesets": [
                {"id": 7, "name": "Protect main"}
            ],
            "repos/owner/example/rulesets/7": {
                "name": "Protect main",
                "enforcement": "active",
                "conditions": {
                    "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
                },
                "bypass_actors": [],
                "rules": [
                    {"type": "deletion"},
                    {"type": "non_fast_forward"},
                    {
                        "type": "pull_request",
                        "parameters": {
                            "required_approving_review_count": 0,
                            "allowed_merge_methods": ["squash"],
                        },
                    },
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "strict_required_status_checks_policy": True,
                            "required_status_checks": [
                                {"context": "CI / Required"},
                            ],
                        },
                    },
                ],
            },
        }

    def test_conforming_repository_passes(self) -> None:
        responses = self.responses()
        self.assertEqual(
            inspect_live_github(self.contract(), responses.__getitem__), []
        )

    def test_ruleset_and_repository_drift_are_reported(self) -> None:
        responses = self.responses()
        responses["repos/owner/example"]["allow_merge_commit"] = True
        status_rule = responses["repos/owner/example/rulesets/7"]["rules"][3]
        status_rule["parameters"]["required_status_checks"] = [
            {"context": "validate"}
        ]
        errors = inspect_live_github(self.contract(), responses.__getitem__)
        self.assertTrue(
            any("allow-merge-commit" in error for error in errors), errors
        )
        self.assertTrue(
            any("required status checks" in error for error in errors), errors
        )

    def test_absent_ruleset_is_reported(self) -> None:
        responses = self.responses()
        responses["repos/owner/example/rulesets"] = []
        errors = inspect_live_github(self.contract(), responses.__getitem__)
        self.assertEqual(errors, ["github.ruleset 'Protect main' is missing"])

    def test_missing_required_labels_are_reported_and_extra_labels_are_allowed(self) -> None:
        responses = self.responses()
        responses["repos/owner/example/labels?per_page=100&page=1"] = [
            {"name": "bug"},
            {"name": "enhancement"},
            {"name": "needs-triage"},
            {"name": "needs-info"},
            {"name": "ready-for-agent"},
            {"name": "ready-for-human"},
            {"name": "repository-specific"},
        ]
        required = [
            "bug",
            "enhancement",
            "needs-triage",
            "needs-info",
            "ready-for-agent",
            "ready-for-human",
            "wontfix",
        ]

        errors = inspect_live_github(
            self.contract(),
            responses.__getitem__,
            required_labels=required,
        )

        self.assertEqual(errors, ["github required labels are missing: ['wontfix']"])

    def test_required_labels_are_found_across_all_label_pages(self) -> None:
        responses = self.responses()
        responses["repos/owner/example/labels?per_page=100&page=1"] = [
            {"name": f"extra-{index:03d}"} for index in range(100)
        ]
        required = [
            "bug",
            "enhancement",
            "needs-triage",
            "needs-info",
            "ready-for-agent",
            "ready-for-human",
            "wontfix",
        ]
        responses["repos/owner/example/labels?per_page=100&page=2"] = [
            {"name": name} for name in required
        ]

        errors = inspect_live_github(
            self.contract(),
            responses.__getitem__,
            required_labels=required,
        )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
