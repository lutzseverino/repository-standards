from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.live_reconciliation import (
    GitHubAdapter,
    GitHubSnapshot,
    LiveLifecycle,
    apply_live_delta,
    reconcile_live_github,
    render_live_audit,
)
from lib.repository_contract import (
    GitHubContract,
    GitHubFeatures,
    GitHubSettings,
    RepositoryContract,
)
from lib.standards import StandardsError


class LiveReconciliationTests(unittest.TestCase):
    def contract(self) -> RepositoryContract:
        return RepositoryContract(
            repository=Path("/repository"),
            manifest_path=Path("/repository/.repository-standards.json"),
            standards_root=Path("/standards"),
            protocol=5,
            release="5.0.0",
            selected_profiles=("common",),
            profiles=(),
            managed_files=(),
            managed_paths=(),
            managed_absences=(),
            repository_owned=(),
            variables=(),
            local_fragments=(),
            required_labels=("bug",),
            dependency_updates=(),
            boundaries=(),
            github=GitHubContract(
                repository="owner/example",
                default_branch="main",
                settings=GitHubSettings(
                    delete_branch_on_merge=True,
                    allow_squash_merge=True,
                    allow_merge_commit=False,
                    allow_rebase_merge=False,
                ),
                ruleset=(
                    ("allow-bypass-actors", False),
                    ("allowed-merge-methods", ("squash",)),
                    ("name", "Protect main"),
                    ("prevent-deletion", True),
                    ("prevent-force-push", True),
                    ("require-current-branch", True),
                    ("required-approvals", 0),
                    ("required-status-checks", ("CI / Required",)),
                ),
            ),
        )

    def test_one_delta_projects_both_audit_findings_and_write_operations(self) -> None:
        snapshot = GitHubSnapshot(
            repository={
                "default_branch": "trunk",
                "delete_branch_on_merge": False,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
                "has_issues": False,
                "has_projects": False,
                "has_wiki": False,
            },
            label_names=frozenset({"repository-specific"}),
            rulesets=(
                {
                    "id": 8,
                    "name": "Repository local",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {
                            "include": ["refs/heads/dev"],
                            "exclude": [],
                        }
                    },
                    "bypass_actors": [],
                    "rules": [],
                },
            ),
            lifecycle=LiveLifecycle.PUBLISHED,
        )

        delta = reconcile_live_github(self.contract(), snapshot)

        self.assertEqual(render_live_audit(delta), list(delta.findings))
        self.assertTrue(
            any("default-branch" in finding for finding in delta.findings),
            delta.findings,
        )
        self.assertTrue(
            any("features.issues" in finding for finding in delta.findings),
            delta.findings,
        )
        self.assertTrue(
            any("required labels" in finding for finding in delta.findings),
            delta.findings,
        )
        self.assertTrue(
            any("Protect main" in finding for finding in delta.findings),
            delta.findings,
        )
        self.assertEqual(
            [operation.description for operation in delta.operations],
            [
                "ESTABLISH default branch 'main'",
                "UPDATE   repository settings",
                "CREATE   label 'bug'",
                "CREATE   ruleset 'Protect main'",
            ],
        )
        self.assertNotIn("repository-specific", "\n".join(delta.findings))
        self.assertFalse(
            any("Repository local" in operation.description for operation in delta.operations)
        )

    def test_replaceable_adapter_observes_paginated_labels_and_rulesets(self) -> None:
        class FakeAdapter(GitHubAdapter):
            def __init__(self) -> None:
                self.requests: list[tuple[str, str]] = []

            def request(
                self,
                method: str,
                endpoint: str,
                payload: dict[str, object] | None = None,
            ) -> object:
                self.requests.append((method, endpoint))
                responses: dict[str, object] = {
                    "repos/owner/example": {
                        "default_branch": "main",
                        "delete_branch_on_merge": True,
                        "allow_squash_merge": True,
                        "allow_merge_commit": False,
                        "allow_rebase_merge": False,
                        "squash_merge_commit_title": "PR_TITLE",
                        "squash_merge_commit_message": "PR_BODY",
                        "has_issues": True,
                        "has_projects": False,
                        "has_wiki": False,
                    },
                    "repos/owner/example/labels?per_page=100&page=1": [
                        {"name": f"extra-{index:03d}"} for index in range(100)
                    ],
                    "repos/owner/example/labels?per_page=100&page=2": [
                        {"name": "bug"}
                    ],
                    "repos/owner/example/rulesets?includes_parents=false&per_page=100&page=1": [
                        {
                            "id": 1,
                            "name": "Protect main",
                            "source_type": "Organization",
                            "source": "owner",
                        },
                        *(
                            {"id": index + 2, "name": f"extra-{index:03d}"}
                            for index in range(99)
                        ),
                    ],
                    "repos/owner/example/rulesets?includes_parents=false&per_page=100&page=2": [
                        {
                            "id": 101,
                            "name": "Protect main",
                            "source_type": "Repository",
                            "source": "owner/example",
                        }
                    ],
                    "repos/owner/example/rulesets/101": {
                        "id": 101,
                        "name": "Protect main",
                        "target": "branch",
                        "enforcement": "active",
                        "conditions": {
                            "ref_name": {
                                "include": ["~DEFAULT_BRANCH"],
                                "exclude": [],
                            }
                        },
                        "bypass_actors": [],
                        "rules": [],
                    },
                }
                return responses[endpoint]

        adapter = FakeAdapter()

        snapshot = adapter.observe(self.contract())

        self.assertIn("bug", snapshot.label_names)
        self.assertEqual(snapshot.rulesets[0]["id"], 101)
        self.assertIn(
            ("GET", "repos/owner/example/labels?per_page=100&page=2"),
            adapter.requests,
        )
        self.assertIn(
            (
                "GET",
                "repos/owner/example/rulesets?includes_parents=false&per_page=100&page=2",
            ),
            adapter.requests,
        )

    def test_adapter_surfaces_observation_authentication_failures(self) -> None:
        class FailingAdapter(GitHubAdapter):
            def request(
                self,
                method: str,
                endpoint: str,
                payload: dict[str, object] | None = None,
            ) -> object:
                raise StandardsError("GitHub authentication failed")

        with self.assertRaisesRegex(StandardsError, "authentication failed"):
            FailingAdapter().observe(self.contract())

    def test_adapter_rejects_rulesets_when_bypass_actors_are_not_observable(
        self,
    ) -> None:
        class ReadOnlyAdapter(GitHubAdapter):
            def request(
                self,
                method: str,
                endpoint: str,
                payload: dict[str, object] | None = None,
            ) -> object:
                if endpoint == "repos/owner/example":
                    return {}
                if endpoint.endswith("/labels?per_page=100&page=1"):
                    return []
                if endpoint.endswith(
                    "/rulesets?includes_parents=false&per_page=100&page=1"
                ):
                    return [{"id": 7, "name": "Protect main"}]
                if endpoint.endswith("/rulesets/7"):
                    return {
                        "id": 7,
                        "name": "Protect main",
                        "target": "branch",
                        "enforcement": "active",
                        "conditions": {},
                        "rules": [],
                    }
                raise AssertionError(endpoint)

        with self.assertRaisesRegex(
            StandardsError, "Administration \\(write\\) permission"
        ):
            ReadOnlyAdapter().observe(self.contract())

    def test_ruleset_comparison_and_write_payload_have_identical_semantics(self) -> None:
        drifted_ruleset = {
            "id": 7,
            "name": "Protect main",
            "target": "tag",
            "enforcement": "disabled",
            "conditions": {
                "ref_name": {
                    "include": ["refs/heads/release"],
                    "exclude": ["refs/heads/main"],
                }
            },
            "bypass_actors": [{"actor_id": 1, "actor_type": "Team"}],
            "rules": [
                {"type": "required_signatures"},
                {
                    "type": "pull_request",
                    "parameters": {
                        "required_approving_review_count": 2,
                        "allowed_merge_methods": ["merge"],
                        "require_code_owner_review": True,
                    },
                },
                {
                    "type": "required_status_checks",
                    "parameters": {
                        "strict_required_status_checks_policy": False,
                        "required_status_checks": [{"context": "old-check"}],
                    },
                },
            ],
        }
        snapshot = GitHubSnapshot(
            repository={
                "default_branch": "main",
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False,
            },
            label_names=frozenset({"bug"}),
            rulesets=(drifted_ruleset,),
        )

        delta = reconcile_live_github(self.contract(), snapshot)

        self.assertGreaterEqual(len(delta.findings), 8)
        self.assertEqual(len(delta.operations), 1)
        operation = delta.operations[0]
        self.assertEqual(operation.description, "UPDATE   ruleset 'Protect main'")
        self.assertEqual(operation.payload["target"], "branch")
        self.assertEqual(operation.payload["enforcement"], "active")
        self.assertEqual(operation.payload["bypass_actors"], [])
        self.assertEqual(
            operation.payload["conditions"]["ref_name"],
            {"include": ["~DEFAULT_BRANCH"], "exclude": []},
        )
        self.assertIn({"type": "deletion"}, operation.payload["rules"])
        self.assertIn({"type": "non_fast_forward"}, operation.payload["rules"])
        self.assertIn({"type": "required_signatures"}, operation.payload["rules"])

        reconciled = reconcile_live_github(
            self.contract(),
            GitHubSnapshot(
                repository=snapshot.repository,
                label_names=snapshot.label_names,
                rulesets=({"id": 7, **operation.payload},),
            ),
        )

        self.assertTrue(reconciled.clean, reconciled.findings)

    def test_ruleset_rejects_targets_beyond_the_declared_default_branch(self) -> None:
        snapshot = GitHubSnapshot(
            repository={
                "default_branch": "main",
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False,
            },
            label_names=frozenset({"bug"}),
            rulesets=(
                {
                    "id": 7,
                    "name": "Protect main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {
                        "ref_name": {
                            "include": [
                                "~DEFAULT_BRANCH",
                                "refs/heads/release",
                            ],
                            "exclude": [],
                        }
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
                                    {"context": "CI / Required"}
                                ],
                            },
                        },
                    ],
                },
            ),
        )

        delta = reconcile_live_github(self.contract(), snapshot)

        self.assertIn(
            "github.ruleset must target only the default branch", delta.findings
        )

    def test_prepared_creation_baseline_reports_publication_requirements_pending(
        self,
    ) -> None:
        delta = reconcile_live_github(
            self.contract(),
            GitHubSnapshot(
                repository={
                    "default_branch": "main",
                    "delete_branch_on_merge": True,
                    "allow_squash_merge": True,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": False,
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "PR_BODY",
                    "has_issues": True,
                    "has_projects": False,
                    "has_wiki": False,
                },
                label_names=frozenset({"bug"}),
                rulesets=(),
                lifecycle=LiveLifecycle.PREPARED,
            ),
        )

        self.assertFalse(delta.clean)
        self.assertEqual(delta.operations, ())
        self.assertEqual(len(delta.pending_findings), 2)
        self.assertTrue(
            all("pending first publication" in item for item in delta.pending_findings)
        )

    def test_required_label_case_collisions_are_renamed_in_place(self) -> None:
        delta = reconcile_live_github(
            self.contract(),
            GitHubSnapshot(
                repository={
                    "default_branch": "main",
                    "delete_branch_on_merge": True,
                    "allow_squash_merge": True,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": False,
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "PR_BODY",
                    "has_issues": True,
                    "has_projects": False,
                    "has_wiki": False,
                },
                label_names=frozenset({"Bug", "repository-specific"}),
                rulesets=(),
            ),
        )

        label_operations = [
            operation
            for operation in delta.operations
            if "label" in operation.description
        ]
        self.assertEqual(len(label_operations), 1)
        self.assertEqual(
            label_operations[0].description,
            "UPDATE   label 'Bug' to 'bug'",
        )
        self.assertEqual(
            label_operations[0].endpoint,
            "repos/owner/example/labels/Bug",
        )
        self.assertEqual(label_operations[0].payload, {"new_name": "bug"})

    def test_partial_application_reports_completed_failed_and_remaining_work(
        self,
    ) -> None:
        class FailingAdapter(GitHubAdapter):
            def __init__(self) -> None:
                self.applied = 0

            def request(
                self,
                method: str,
                endpoint: str,
                payload: dict[str, object] | None = None,
            ) -> object:
                self.applied += 1
                if self.applied == 2:
                    raise StandardsError("permission denied")
                return {}

        delta = reconcile_live_github(
            self.contract(),
            GitHubSnapshot(
                repository={
                    "default_branch": "trunk",
                    "delete_branch_on_merge": False,
                    "allow_squash_merge": True,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": False,
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "PR_BODY",
                    "has_issues": True,
                    "has_projects": False,
                    "has_wiki": False,
                },
                label_names=frozenset(),
                rulesets=(),
            ),
        )

        report = apply_live_delta(delta, FailingAdapter())

        self.assertFalse(report.complete)
        self.assertEqual(
            [item.description for item in report.completed],
            ["ESTABLISH default branch 'main'"],
        )
        self.assertEqual(report.failed.description, "UPDATE   repository settings")
        self.assertEqual(
            [item.description for item in report.remaining],
            ["CREATE   label 'bug'", "CREATE   ruleset 'Protect main'"],
        )
        self.assertEqual(report.error, "permission denied")

    def test_declared_repository_features_change_without_touching_undeclared_ones(
        self,
    ) -> None:
        contract = self.contract()
        contract = replace(
            contract,
            github=replace(
                contract.github,
                features=GitHubFeatures(issues=True, projects=True, wiki=False),
            ),
        )
        delta = reconcile_live_github(
            contract,
            GitHubSnapshot(
                repository={
                    "default_branch": "main",
                    "delete_branch_on_merge": True,
                    "allow_squash_merge": True,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": False,
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "PR_BODY",
                    "has_issues": True,
                    "has_projects": False,
                    "has_wiki": False,
                    "has_discussions": True,
                },
                label_names=frozenset({"bug"}),
                rulesets=(
                    {
                        "id": 7,
                        "name": "Protect main",
                        "target": "branch",
                        "enforcement": "active",
                        "conditions": {
                            "ref_name": {
                                "include": ["~DEFAULT_BRANCH"],
                                "exclude": [],
                            }
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
                                        {"context": "CI / Required"}
                                    ],
                                },
                            },
                        ],
                    },
                ),
            ),
        )

        self.assertEqual(
            delta.operations[0].payload,
            {"has_projects": True},
        )
        self.assertNotIn("has_discussions", delta.operations[0].payload)


if __name__ == "__main__":
    unittest.main()
