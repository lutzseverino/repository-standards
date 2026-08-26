from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.github_reconciliation import (
    GitHubAdapter,
    GitHubSnapshot,
    GitHubLifecycle,
    apply_github_reconciliation,
    reconcile_github,
)
from lib.repository_contract import (
    CanonicalValidation,
    GitHubContract,
    GitHubFeatures,
    GitHubSettings,
    RepositoryContract,
)
from lib.repository_content import StandardsError


class GitHubReconciliationTests(unittest.TestCase):
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
            canonical_validation=CanonicalValidation("scripts/validate", ()),
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

    def test_one_reconciliation_projects_findings_and_corrections(self) -> None:
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
            branches=({"name": "main"}, {"name": "trunk"}),
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
            lifecycle=GitHubLifecycle.PUBLISHED,
        )

        reconciliation = reconcile_github(self.contract(), snapshot)

        self.assertEqual(
            list(reconciliation.findings),
            [
                finding
                for difference in reconciliation.differences
                for finding in difference.findings
            ],
        )
        self.assertTrue(
            any("default-branch" in finding for finding in reconciliation.findings),
            reconciliation.findings,
        )
        self.assertTrue(
            any("features.issues" in finding for finding in reconciliation.findings),
            reconciliation.findings,
        )
        self.assertTrue(
            any("required labels" in finding for finding in reconciliation.findings),
            reconciliation.findings,
        )
        self.assertTrue(
            any("Protect main" in finding for finding in reconciliation.findings),
            reconciliation.findings,
        )
        self.assertEqual(
            [operation.description for operation in reconciliation.operations],
            [
                "ESTABLISH default branch 'main'",
                "UPDATE   repository settings",
                "CREATE   label 'bug'",
                "CREATE   ruleset 'Protect main'",
            ],
        )
        self.assertNotIn("repository-specific", "\n".join(reconciliation.findings))
        self.assertFalse(
            any("Repository local" in operation.description for operation in reconciliation.operations)
        )

    def test_replaceable_adapter_observes_branches_labels_and_rulesets(self) -> None:
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
                    "repos/owner/example/branches?per_page=100&page=1": [
                        {"name": "main"}
                    ],
                }
                return responses[endpoint]

        adapter = FakeAdapter()

        snapshot = adapter.observe(self.contract())

        self.assertEqual(snapshot.branches, ({"name": "main"},))
        self.assertIn("bug", snapshot.label_names)
        self.assertIn(101, {ruleset["id"] for ruleset in snapshot.rulesets})
        self.assertIn(2, {ruleset["id"] for ruleset in snapshot.rulesets})
        self.assertNotIn(1, {ruleset["id"] for ruleset in snapshot.rulesets})
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

    def test_adapter_retains_undeclared_rulesets_when_none_is_managed(self) -> None:
        class FakeAdapter(GitHubAdapter):
            def request(self, method, endpoint, payload=None):
                responses = {
                    "repos/owner/example": {},
                    "repos/owner/example/labels?per_page=100&page=1": [],
                    "repos/owner/example/rulesets?includes_parents=false&per_page=100&page=1": [
                        {
                            "id": 7,
                            "name": "Repository local",
                            "source_type": "Repository",
                            "source": "owner/example",
                        }
                    ],
                    "repos/owner/example/branches?per_page=100&page=1": [],
                }
                return responses[endpoint]

        contract = self.contract()
        contract = replace(
            contract,
            github=replace(contract.github, ruleset=None),
        )

        snapshot = FakeAdapter().observe(contract)

        self.assertEqual(
            snapshot.rulesets,
            (
                {
                    "id": 7,
                    "name": "Repository local",
                    "source_type": "Repository",
                    "source": "owner/example",
                },
            ),
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
            branches=({"name": "main"},),
            label_names=frozenset({"bug"}),
            rulesets=(drifted_ruleset,),
        )

        reconciliation = reconcile_github(self.contract(), snapshot)

        self.assertGreaterEqual(len(reconciliation.findings), 8)
        self.assertEqual(len(reconciliation.operations), 1)
        operation = reconciliation.operations[0]
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

        reconciled = reconcile_github(
            self.contract(),
            GitHubSnapshot(
                repository=snapshot.repository,
                branches=snapshot.branches,
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
            branches=({"name": "main"},),
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

        reconciliation = reconcile_github(self.contract(), snapshot)

        self.assertIn(
            "github.ruleset must target only the default branch", reconciliation.findings
        )

    def test_prepared_creation_baseline_reports_publication_requirements_pending(
        self,
    ) -> None:
        reconciliation = reconcile_github(
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
                branches=(),
                label_names=frozenset({"bug"}),
                rulesets=(),
                lifecycle=GitHubLifecycle.PREPARED,
            ),
        )

        self.assertFalse(reconciliation.clean)
        self.assertEqual(reconciliation.operations, ())
        self.assertEqual(len(reconciliation.pending_findings), 2)
        self.assertTrue(
            all("pending first publication" in item for item in reconciliation.pending_findings)
        )

    def test_empty_observed_branch_set_requires_default_branch_establishment(
        self,
    ) -> None:
        reconciliation = reconcile_github(
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
                branches=(),
                label_names=frozenset({"bug"}),
                rulesets=(),
            ),
        )

        operation = reconciliation.operations[0]
        self.assertEqual(
            reconciliation.blockers,
            ("create or publish default branch 'main' before reconciliation",),
        )
        self.assertEqual(operation.description, "ESTABLISH default branch 'main'")
        self.assertEqual(operation.method, "PATCH")
        self.assertEqual(operation.endpoint, "repos/owner/example")
        self.assertEqual(operation.payload, {"default_branch": "main"})

    def test_required_label_case_collisions_are_renamed_in_place(self) -> None:
        reconciliation = reconcile_github(
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
                branches=({"name": "main"},),
                label_names=frozenset({"Bug", "repository-specific"}),
                rulesets=(),
            ),
        )

        label_operations = [
            operation
            for operation in reconciliation.operations
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

        reconciliation = reconcile_github(
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
                branches=({"name": "main"}, {"name": "trunk"}),
                label_names=frozenset(),
                rulesets=(),
            ),
        )

        report = apply_github_reconciliation(reconciliation, FailingAdapter())

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
        reconciliation = reconcile_github(
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
                branches=({"name": "main"},),
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
            reconciliation.operations[0].payload,
            {"has_projects": True},
        )
        self.assertNotIn("has_discussions", reconciliation.operations[0].payload)


if __name__ == "__main__":
    unittest.main()
