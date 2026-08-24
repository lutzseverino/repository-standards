from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.live_reconciliation import GitHubAdapter, GitHubSnapshot
from lib.repository_assessment import (
    AssessmentConclusion,
    AssessmentScope,
    assess_repository,
    repair_repository,
)
from lib.repository_contract import (
    ContractBlocker,
    GitHubContract,
    GitHubSettings,
    ManagedFile,
    RepositoryContract,
)
from lib.standards import StandardsError


class SnapshotAdapter(GitHubAdapter):
    def __init__(self, *snapshots: GitHubSnapshot) -> None:
        self.snapshots = list(snapshots)
        self.applied: list[str] = []

    def observe(self, contract, *, lifecycle=None):
        if not self.snapshots:
            raise AssertionError("unexpected GitHub observation")
        return self.snapshots.pop(0)

    def apply(self, operation):
        self.applied.append(operation.description)


class RepositoryAssessmentTests(unittest.TestCase):
    def contract(self, repository: Path) -> RepositoryContract:
        repository = repository.resolve()
        return RepositoryContract(
            repository=repository,
            manifest_path=repository / ".repository-standards.json",
            standards_root=Path("/standards"),
            protocol=5,
            release="5.0.0",
            selected_profiles=("common",),
            profiles=(),
            managed_files=(
                ManagedFile("managed.txt", "file", b"current\n", ("common",)),
            ),
            managed_paths=("managed.txt",),
            managed_absences=(),
            repository_owned=("owned.txt",),
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
                ruleset=None,
            ),
        )

    def published_snapshot(self) -> GitHubSnapshot:
        return GitHubSnapshot(
            repository={
                "full_name": "owner/example",
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
                "permissions": {"admin": True, "push": True},
            },
            branches=({"name": "main"},),
            label_names=frozenset({"bug", "repository-specific"}),
            rulesets=(
                {
                    "id": 9,
                    "name": "Repository local",
                    "source_type": "Repository",
                    "source": "owner/example",
                },
            ),
        )

    def test_conforming_published_repository_is_standards_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            (repository / "owned.txt").write_text("maintainer\n", encoding="utf-8")

            assessment = assess_repository(
                self.contract(repository), SnapshotAdapter(self.published_snapshot())
            )

        self.assertEqual(
            assessment.conclusion, AssessmentConclusion.STANDARDS_COMPLETE
        )
        self.assertEqual(assessment.lifecycle, "published")
        self.assertTrue(assessment.satisfied_requirements)
        self.assertTrue(
            any(
                "repository-specific" in item.description
                for item in assessment.preservation_evidence
            )
        )
        self.assertTrue(
            any(
                "Repository local" in item.description
                for item in assessment.preservation_evidence
            )
        )
        self.assertEqual(assessment.differences, ())
        self.assertEqual(assessment.evidence_gaps, ())
        self.assertEqual(assessment.automatic_corrections, ())
        self.assertEqual(assessment.required_maintainer_work, ())

    def test_unavailable_github_evidence_retains_local_differences(self) -> None:
        class UnavailableGitHub(GitHubAdapter):
            def observe(self, contract, *, lifecycle=None):
                raise StandardsError("GitHub authentication is unavailable")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("drifted\n", encoding="utf-8")

            assessment = assess_repository(
                self.contract(repository), UnavailableGitHub()
            )

        self.assertEqual(assessment.conclusion, AssessmentConclusion.UNVERIFIED)
        self.assertTrue(
            any("managed.txt" in item.description for item in assessment.differences)
        )
        self.assertEqual(
            [gap.description for gap in assessment.evidence_gaps],
            ["GitHub authentication is unavailable"],
        )
        self.assertTrue(assessment.automatic_corrections)

    def test_unproven_repository_identity_is_an_evidence_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            snapshot = self.published_snapshot()
            wrong_identity = GitHubSnapshot(
                repository={**snapshot.repository, "full_name": "owner/other"},
                branches=snapshot.branches,
                label_names=snapshot.label_names,
                rulesets=snapshot.rulesets,
            )

            assessment = assess_repository(
                self.contract(repository), SnapshotAdapter(wrong_identity)
            )

        self.assertEqual(assessment.conclusion, AssessmentConclusion.UNVERIFIED)
        self.assertIn("identity", assessment.evidence_gaps[0].description)

    def test_managed_absence_is_a_deterministic_automatic_correction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "retired.txt").write_text("retired\n", encoding="utf-8")
            contract = replace(
                self.contract(repository),
                managed_files=(
                    ManagedFile("retired.txt", "absent", b"", ("common",)),
                ),
                managed_paths=("retired.txt",),
                managed_absences=("retired.txt",),
            )

            assessment = assess_repository(
                contract, SnapshotAdapter(self.published_snapshot())
            )

        self.assertEqual(
            assessment.conclusion,
            AssessmentConclusion.NOT_STANDARDS_COMPLETE,
        )
        self.assertEqual(
            [item.action for item in assessment.automatic_corrections],
            ["DELETE retired.txt"],
        )

    def test_symlinked_managed_path_blocks_repair_without_following_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            outside = repository / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            (repository / "managed.txt").symlink_to(outside)

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(self.published_snapshot()),
                preview=lambda value: None,
            )

            self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")

        self.assertEqual(assessment.application_report.failed, "preflight")
        self.assertTrue(
            any("symlink" in work.action for work in assessment.required_maintainer_work)
        )

    def test_failed_post_application_observation_reports_verification_failure(self) -> None:
        class IneffectiveGitHub(GitHubAdapter):
            def __init__(self, owner: "RepositoryAssessmentTests") -> None:
                self.owner = owner

            def observe(self, contract, *, lifecycle=None):
                snapshot = self.owner.published_snapshot()
                return GitHubSnapshot(
                    repository={
                        **snapshot.repository,
                        "delete_branch_on_merge": False,
                    },
                    branches=snapshot.branches,
                    label_names=snapshot.label_names,
                    rulesets=snapshot.rulesets,
                )

            def apply(self, operation):
                return None

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                IneffectiveGitHub(self),
                preview=lambda value: None,
            )

        self.assertEqual(assessment.application_report.failed, "verification")
        self.assertIn(
            "github: UPDATE   repository settings",
            assessment.application_report.remaining,
        )

    def test_unavailable_post_application_evidence_is_a_verification_failure(self) -> None:
        class LostVerificationGitHub(GitHubAdapter):
            def __init__(self, owner: "RepositoryAssessmentTests") -> None:
                self.owner = owner
                self.observations = 0

            def observe(self, contract, *, lifecycle=None):
                self.observations += 1
                if self.observations == 4:
                    raise StandardsError("GitHub verification is unavailable")
                snapshot = self.owner.published_snapshot()
                return GitHubSnapshot(
                    repository={
                        **snapshot.repository,
                        "delete_branch_on_merge": False,
                    },
                    branches=snapshot.branches,
                    label_names=snapshot.label_names,
                    rulesets=snapshot.rulesets,
                )

            def apply(self, operation):
                return None

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                LostVerificationGitHub(self),
                preview=lambda value: None,
            )

        self.assertEqual(assessment.conclusion, AssessmentConclusion.UNVERIFIED)
        self.assertEqual(assessment.application_report.failed, "verification")
        self.assertIn(
            "github: GitHub verification is unavailable",
            assessment.application_report.remaining,
        )

    def test_repair_previews_every_correction_before_mutation_and_reassesses(self) -> None:
        class MutableGitHub(GitHubAdapter):
            def __init__(self, owner: "RepositoryAssessmentTests") -> None:
                self.owner = owner
                self.applied: list[str] = []

            def observe(self, contract, *, lifecycle=None):
                snapshot = self.owner.published_snapshot()
                if self.applied:
                    return snapshot
                repository = dict(snapshot.repository)
                repository["delete_branch_on_merge"] = False
                return GitHubSnapshot(
                    repository=repository,
                    branches=snapshot.branches,
                    label_names=snapshot.label_names,
                    rulesets=snapshot.rulesets,
                )

            def apply(self, operation):
                self.applied.append(operation.description)

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")
            adapter = MutableGitHub(self)
            previewed: list[str] = []

            def preview(assessment) -> None:
                self.assertEqual(managed.read_text(encoding="utf-8"), "drifted\n")
                self.assertEqual(adapter.applied, [])
                previewed.extend(
                    correction.action
                    for correction in assessment.automatic_corrections
                )

            repaired = repair_repository(
                self.contract(repository), adapter, preview=preview
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "current\n")

        self.assertEqual(
            previewed,
            ["UPDATE managed.txt", "UPDATE   repository settings"],
        )
        self.assertEqual(adapter.applied, ["UPDATE   repository settings"])
        self.assertEqual(
            repaired.conclusion, AssessmentConclusion.STANDARDS_COMPLETE
        )
        self.assertIsNotNone(repaired.application_report)
        self.assertEqual(
            repaired.application_report.completed,
            (
                "repository-content: UPDATE managed.txt",
                "github: UPDATE   repository settings",
            ),
        )
        self.assertTrue(repaired.application_report.succeeded)

    def test_prepared_repository_is_inferred_and_requires_first_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            snapshot = self.published_snapshot()
            prepared = GitHubSnapshot(
                repository=snapshot.repository,
                branches=(),
                label_names=snapshot.label_names,
                rulesets=snapshot.rulesets,
            )

            assessment = assess_repository(
                self.contract(repository), SnapshotAdapter(prepared)
            )

        self.assertEqual(
            assessment.conclusion,
            AssessmentConclusion.NOT_STANDARDS_COMPLETE,
        )
        self.assertEqual(assessment.lifecycle, "prepared")
        self.assertTrue(
            any("first publication" in item.action for item in assessment.required_maintainer_work)
        )

    def test_ambiguous_lifecycle_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            snapshot = self.published_snapshot()
            ambiguous = GitHubSnapshot(
                repository={**snapshot.repository, "default_branch": None},
                branches=({"name": "orphaned"},),
                label_names=snapshot.label_names,
                rulesets=snapshot.rulesets,
            )

            assessment = assess_repository(
                self.contract(repository), SnapshotAdapter(ambiguous)
            )

        self.assertEqual(assessment.conclusion, AssessmentConclusion.UNVERIFIED)
        self.assertIsNone(assessment.lifecycle)
        self.assertIn("ambiguous", assessment.evidence_gaps[0].description)

    def test_prepared_repair_reports_first_publication_as_remaining_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            snapshot = self.published_snapshot()
            prepared = GitHubSnapshot(
                repository=snapshot.repository,
                branches=(),
                label_names=snapshot.label_names,
                rulesets=snapshot.rulesets,
            )

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(prepared, prepared, prepared),
                preview=lambda value: None,
            )

        self.assertEqual(
            assessment.conclusion,
            AssessmentConclusion.NOT_STANDARDS_COMPLETE,
        )
        self.assertEqual(
            assessment.application_report.remaining,
            ("github: perform first publication",),
        )

    def test_restricted_content_repair_changes_only_content_and_stays_unverified(self) -> None:
        class GitHubMustNotBeObserved(GitHubAdapter):
            def observe(self, contract, *, lifecycle=None):
                raise AssertionError("restricted content repair observed GitHub")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                GitHubMustNotBeObserved(),
                scope=AssessmentScope.CONTENT,
                preview=lambda value: None,
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "current\n")

        self.assertEqual(assessment.conclusion, AssessmentConclusion.UNVERIFIED)
        self.assertEqual(assessment.scope, AssessmentScope.CONTENT)
        self.assertEqual(assessment.automatic_corrections, ())
        self.assertEqual(
            assessment.application_report.completed,
            ("repository-content: UPDATE managed.txt",),
        )

    def test_incomplete_whole_repository_preflight_prevents_local_mutation(self) -> None:
        class UnavailableGitHub(GitHubAdapter):
            def observe(self, contract, *, lifecycle=None):
                raise StandardsError("GitHub permission is insufficient")

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                UnavailableGitHub(),
                preview=lambda value: None,
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "drifted\n")

        self.assertEqual(assessment.application_report.failed, "preflight")
        self.assertIn(
            "repository-content: UPDATE managed.txt",
            assessment.application_report.remaining,
        )

    def test_insufficient_github_write_permission_blocks_default_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")
            snapshot = self.published_snapshot()
            insufficient = GitHubSnapshot(
                repository={
                    **snapshot.repository,
                    "delete_branch_on_merge": False,
                    "permissions": {"admin": False, "push": True},
                },
                branches=snapshot.branches,
                label_names=snapshot.label_names,
                rulesets=snapshot.rulesets,
            )

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(insufficient),
                preview=lambda value: None,
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "drifted\n")

        self.assertEqual(assessment.application_report.failed, "preflight")
        self.assertIn("permission", assessment.application_report.error)

    def test_ownership_blocker_prevents_every_default_repair_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("maintainer content\n", encoding="utf-8")
            contract = replace(
                self.contract(repository),
                plan_blockers=(
                    ContractBlocker(
                        "managed.txt",
                        "managed content conflicts with repository ownership",
                    ),
                ),
            )

            assessment = repair_repository(
                contract,
                SnapshotAdapter(self.published_snapshot()),
                preview=lambda value: None,
            )

            self.assertEqual(
                managed.read_text(encoding="utf-8"), "maintainer content\n"
            )

        self.assertEqual(assessment.application_report.failed, "preflight")
        self.assertTrue(assessment.required_maintainer_work)

    def test_changed_observation_invalidates_repair_before_local_mutation(self) -> None:
        first = self.published_snapshot()
        changed = GitHubSnapshot(
            repository={**first.repository, "has_wiki": True},
            branches=first.branches,
            label_names=first.label_names,
            rulesets=first.rulesets,
        )
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(first, changed),
                preview=lambda value: None,
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "drifted\n")

        self.assertEqual(
            assessment.application_report.failed, "stale-observation"
        )

    def test_missing_declared_default_branch_blocks_every_default_mutation(self) -> None:
        snapshot = self.published_snapshot()
        blocked = GitHubSnapshot(
            repository={**snapshot.repository, "default_branch": "trunk"},
            branches=({"name": "trunk"},),
            label_names=snapshot.label_names,
            rulesets=snapshot.rulesets,
        )
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            managed = repository / "managed.txt"
            managed.write_text("drifted\n", encoding="utf-8")

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(blocked),
                preview=lambda value: None,
            )

            self.assertEqual(managed.read_text(encoding="utf-8"), "drifted\n")

        self.assertEqual(assessment.application_report.failed, "preflight")
        self.assertTrue(
            any(
                "default branch" in work.action
                for work in assessment.required_maintainer_work
            )
        )

    def test_github_failure_reports_completed_failed_and_remaining_without_rollback(self) -> None:
        class PartiallyFailingGitHub(GitHubAdapter):
            def __init__(self, owner: "RepositoryAssessmentTests") -> None:
                self.owner = owner
                self.completed: list[str] = []

            def observe(self, contract, *, lifecycle=None):
                snapshot = self.owner.published_snapshot()
                repository = dict(snapshot.repository)
                if not self.completed:
                    repository["delete_branch_on_merge"] = False
                return GitHubSnapshot(
                    repository=repository,
                    branches=snapshot.branches,
                    label_names=frozenset(),
                    rulesets=snapshot.rulesets,
                )

            def apply(self, operation):
                if operation.description.startswith("CREATE   label"):
                    raise StandardsError("GitHub label write failed")
                self.completed.append(operation.description)

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            adapter = PartiallyFailingGitHub(self)

            assessment = repair_repository(
                self.contract(repository), adapter, preview=lambda value: None
            )

        report = assessment.application_report
        self.assertEqual(
            report.completed, ("github: UPDATE   repository settings",)
        )
        self.assertEqual(report.failed, "github: CREATE   label 'bug'")
        self.assertEqual(report.remaining, ())
        self.assertEqual(adapter.completed, ["UPDATE   repository settings"])
        self.assertTrue(
            any("required labels" in item.description for item in assessment.differences)
        )

    def test_successful_rerun_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            snapshot = self.published_snapshot()

            assessment = repair_repository(
                self.contract(repository),
                SnapshotAdapter(snapshot, snapshot, snapshot),
                preview=lambda value: None,
            )

        self.assertEqual(
            assessment.conclusion, AssessmentConclusion.STANDARDS_COMPLETE
        )
        self.assertEqual(assessment.application_report.completed, ())
        self.assertTrue(assessment.application_report.succeeded)

    def test_partial_github_failure_recovers_idempotently_on_rerun(self) -> None:
        class RecoverableGitHub(GitHubAdapter):
            def __init__(self, owner: "RepositoryAssessmentTests") -> None:
                self.owner = owner
                self.settings_current = False
                self.label_present = False
                self.fail_label_once = True

            def observe(self, contract, *, lifecycle=None):
                snapshot = self.owner.published_snapshot()
                return GitHubSnapshot(
                    repository={
                        **snapshot.repository,
                        "delete_branch_on_merge": self.settings_current,
                    },
                    branches=snapshot.branches,
                    label_names=(
                        frozenset({"bug"})
                        if self.label_present
                        else frozenset()
                    ),
                    rulesets=snapshot.rulesets,
                )

            def apply(self, operation):
                if operation.description == "UPDATE   repository settings":
                    self.settings_current = True
                    return None
                if self.fail_label_once:
                    self.fail_label_once = False
                    raise StandardsError("transient label failure")
                self.label_present = True
                return None

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "managed.txt").write_text("current\n", encoding="utf-8")
            adapter = RecoverableGitHub(self)
            contract = self.contract(repository)

            first = repair_repository(
                contract, adapter, preview=lambda value: None
            )
            recovered = repair_repository(
                contract, adapter, preview=lambda value: None
            )
            rerun = repair_repository(
                contract, adapter, preview=lambda value: None
            )

        self.assertEqual(
            first.application_report.completed,
            ("github: UPDATE   repository settings",),
        )
        self.assertEqual(
            recovered.application_report.completed,
            ("github: CREATE   label 'bug'",),
        )
        self.assertEqual(
            recovered.conclusion, AssessmentConclusion.STANDARDS_COMPLETE
        )
        self.assertEqual(rerun.application_report.completed, ())

    def test_assessment_order_is_stable_for_equivalent_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "z.txt").write_text("drift\n", encoding="utf-8")
            contract = replace(
                self.contract(repository),
                managed_files=(
                    ManagedFile("z.txt", "file", b"z\n", ("common",)),
                    ManagedFile("a.txt", "file", b"a\n", ("common",)),
                ),
                managed_paths=("z.txt", "a.txt"),
            )
            snapshot = self.published_snapshot()

            first = assess_repository(contract, SnapshotAdapter(snapshot))
            second = assess_repository(contract, SnapshotAdapter(snapshot))

        self.assertEqual(first, second)
        self.assertEqual(
            [item.action for item in first.automatic_corrections],
            ["UPDATE z.txt", "CREATE a.txt"],
        )


if __name__ == "__main__":
    unittest.main()
