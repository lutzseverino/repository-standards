"""Assess repository content and declared GitHub state through one interface."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Callable, Protocol

from .github_reconciliation import (
    GitHubAdapter,
    GitHubSnapshot,
    GitHubReconciliation,
    GitHubLifecycle,
    apply_github_reconciliation,
    reconcile_github,
)
from .repository_content_reconciliation import (
    ContentCorrection,
    ContentReconciliation,
    apply_content_reconciliation,
    calculate_content_reconciliation,
)
from .repository_contract import RepositoryContract
from .repository_content import (
    StandardsError,
    inspect_boundaries,
    inspect_repository_owned_documents,
)


class AssessmentConclusion(str, Enum):
    """The only whole-repository conformance conclusions."""

    STANDARDS_COMPLETE = "standards-complete"
    NOT_STANDARDS_COMPLETE = "not-standards-complete"
    UNVERIFIED = "unverified"


class AssessmentScope(str, Enum):
    """The complete repository or one explicit diagnostic scope."""

    REPOSITORY = "repository"
    CONTENT = "content"
    GITHUB = "github"


class CorrectionKind(str, Enum):
    """Machine-readable automatic correction operation."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPLY = "apply"


class RepositoryLifecycle(str, Enum):
    """The lifecycle state proven by repository evidence."""

    PREPARED = "prepared"
    PUBLISHED = "published"


class RepositoryObserver(Protocol):
    """Read-only boundary required to calculate repository evidence."""

    def observe(
        self,
        contract: RepositoryContract,
        *,
        lifecycle: GitHubLifecycle = GitHubLifecycle.PUBLISHED,
    ) -> GitHubSnapshot: ...


@dataclass(frozen=True)
class AssessmentEntry:
    subject: str
    description: str


@dataclass(frozen=True)
class AutomaticCorrection:
    subject: str
    action: str
    kind: CorrectionKind
    target: str


@dataclass(frozen=True)
class MaintainerWork:
    subject: str
    action: str


@dataclass(frozen=True)
class ApplicationReport:
    completed: tuple[str, ...] = ()
    failed: str | None = None
    error: str | None = None
    remaining: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.failed is None


@dataclass(frozen=True)
class RepositoryAssessment:
    """One complete account of repository conformance and repair evidence."""

    conclusion: AssessmentConclusion
    scope: AssessmentScope
    lifecycle: RepositoryLifecycle | None
    satisfied_requirements: tuple[AssessmentEntry, ...]
    differences: tuple[AssessmentEntry, ...]
    evidence_gaps: tuple[AssessmentEntry, ...]
    automatic_corrections: tuple[AutomaticCorrection, ...]
    required_maintainer_work: tuple[MaintainerWork, ...]
    preservation_evidence: tuple[AssessmentEntry, ...]
    application_report: ApplicationReport | None = None


@dataclass(frozen=True)
class _AssessmentCalculation:
    assessment: RepositoryAssessment
    content_reconciliation: ContentReconciliation | None
    github_snapshot: GitHubSnapshot | None
    github_reconciliation: GitHubReconciliation | None
    remote_blockers: tuple[AssessmentEntry, ...]


def _infer_lifecycle(snapshot: GitHubSnapshot) -> RepositoryLifecycle | None:
    default_branch = snapshot.repository.get("default_branch")
    if snapshot.branches and isinstance(default_branch, str) and default_branch:
        return RepositoryLifecycle.PUBLISHED
    if not snapshot.branches:
        return RepositoryLifecycle.PREPARED
    return None


def _calculate_assessment(
    contract: RepositoryContract,
    github_adapter: RepositoryObserver,
    *,
    scope: AssessmentScope = AssessmentScope.REPOSITORY,
    application_report: ApplicationReport | None = None,
) -> _AssessmentCalculation:
    """Observe and calculate one deterministic repository assessment."""

    satisfied: list[AssessmentEntry] = []
    differences: list[AssessmentEntry] = []
    evidence_gaps: list[AssessmentEntry] = []
    corrections: list[AutomaticCorrection] = []
    maintainer_work: list[MaintainerWork] = []
    preservation: list[AssessmentEntry] = []
    lifecycle: RepositoryLifecycle | None = None
    content_reconciliation: ContentReconciliation | None = None
    github_snapshot: GitHubSnapshot | None = None
    github_reconciliation: GitHubReconciliation | None = None
    remote_blockers: list[AssessmentEntry] = []

    if scope in {AssessmentScope.REPOSITORY, AssessmentScope.CONTENT}:
        reconciliation = calculate_content_reconciliation(contract)
        content_reconciliation = reconciliation
        for operation in reconciliation.operations:
            if operation.status == "ok":
                satisfied.append(
                    AssessmentEntry(
                        "repository-content",
                        f"{operation.target} satisfies its managed content contract",
                    )
                )
                continue
            differences.append(
                AssessmentEntry(
                    "repository-content",
                    f"{operation.target} is {operation.status}",
                )
            )
            corrections.append(
                AutomaticCorrection(
                    "repository-content",
                    _operation_action(operation),
                    _operation_kind(operation),
                    operation.target,
                )
            )
        for blocker in reconciliation.blockers:
            differences.append(
                AssessmentEntry("repository-content", blocker.message)
            )
            maintainer_work.append(
                MaintainerWork(
                    "repository-content",
                    f"resolve {blocker.target}: {blocker.message}",
                )
            )

        for boundary in inspect_boundaries(contract.repository, contract.boundaries):
            if boundary.status == "ok":
                satisfied.append(
                    AssessmentEntry(
                        "repository-content",
                        f"boundary {boundary.path} satisfies its "
                        "documentation contract",
                    )
                )
            else:
                for message in boundary.messages:
                    differences.append(
                        AssessmentEntry("repository-content", message)
                    )
                    maintainer_work.append(
                        MaintainerWork("repository-content", message)
                    )

        for document in inspect_repository_owned_documents(
            contract.repository, contract.repository_owned
        ):
            if document.status == "ok":
                satisfied.append(
                    AssessmentEntry(
                        "repository-content",
                        f"{document.path} satisfies its authored document contract",
                    )
                )
            else:
                for message in document.messages:
                    differences.append(
                        AssessmentEntry("repository-content", message)
                    )
                    maintainer_work.append(
                        MaintainerWork("repository-content", message)
                    )

        preservation.extend(
            AssessmentEntry(
                "repository-content",
                f"repository-owned declaration {path!r} is excluded from "
                "automatic correction",
            )
            for path in sorted(contract.repository_owned)
        )

    if scope in {AssessmentScope.REPOSITORY, AssessmentScope.GITHUB}:
        try:
            snapshot = github_adapter.observe(
                contract, lifecycle=GitHubLifecycle.PUBLISHED
            )
        except StandardsError as exc:
            evidence_gaps.append(
                AssessmentEntry("github", str(exc))
            )
        else:
            github_snapshot = snapshot
            expected_identity = contract.github.repository
            observed_identity = snapshot.repository.get("full_name")
            if observed_identity != expected_identity:
                evidence_gaps.append(
                    AssessmentEntry(
                        "github",
                        f"GitHub repository identity is {observed_identity!r}; "
                        f"expected {expected_identity!r}",
                    )
                )
            else:
                lifecycle = _infer_lifecycle(snapshot)
                if lifecycle is None:
                    evidence_gaps.append(
                        AssessmentEntry(
                            "github",
                            "repository lifecycle is ambiguous from the "
                            "observed GitHub state",
                        )
                    )
                else:
                    try:
                        reconciliation = reconcile_github(
                            contract,
                            replace(
                                snapshot,
                                lifecycle=GitHubLifecycle(lifecycle.value),
                            ),
                        )
                    except StandardsError as exc:
                        evidence_gaps.append(AssessmentEntry("github", str(exc)))
                    else:
                        github_reconciliation = reconciliation
                        if not reconciliation.differences:
                            satisfied.append(
                                AssessmentEntry(
                                    "github",
                                    "declared GitHub state satisfies its contract",
                                )
                            )
                        for difference in reconciliation.differences:
                            for finding in difference.findings:
                                differences.append(AssessmentEntry("github", finding))
                            for blocker in difference.blockers:
                                remote_blockers.append(
                                    AssessmentEntry("github", blocker)
                                )
                                maintainer_work.append(
                                    MaintainerWork("github", blocker)
                                )
                            if not difference.blockers:
                                for operation in difference.operations:
                                    corrections.append(
                                        AutomaticCorrection(
                                            "github",
                                            operation.description,
                                            CorrectionKind.APPLY,
                                            operation.endpoint,
                                        )
                                    )
                            if difference.pending:
                                maintainer_work.append(
                                    MaintainerWork(
                                        "github", "perform first publication"
                                    )
                                )

            required_label_identities = {
                label.casefold() for label in contract.required_labels
            }
            preservation.extend(
                AssessmentEntry(
                    "github",
                    f"undeclared GitHub label {label!r} is excluded from "
                    "automatic correction",
                )
                for label in sorted(snapshot.label_names)
                if label.casefold() not in required_label_identities
            )
            preservation.extend(
                AssessmentEntry(
                    "github",
                    f"undeclared GitHub branch {branch['name']!r} is excluded "
                    "from automatic correction",
                )
                for branch in sorted(
                    snapshot.branches, key=lambda item: str(item.get("name", ""))
                )
                if branch.get("name") != contract.github.default_branch
            )
            managed_ruleset = (
                contract.github.as_mapping()["ruleset"] or {}
            ).get("name")
            preservation.extend(
                AssessmentEntry(
                    "github",
                    f"undeclared GitHub ruleset {ruleset['name']!r} is excluded "
                    "from automatic correction",
                )
                for ruleset in sorted(
                    snapshot.rulesets, key=lambda item: str(item.get("name", ""))
                )
                if ruleset.get("name") != managed_ruleset
            )

    if scope is not AssessmentScope.REPOSITORY:
        evidence_gaps.append(
            AssessmentEntry(
                "repository",
                f"{scope.value}-only assessment cannot prove repository completeness",
            )
        )

    if evidence_gaps:
        conclusion = AssessmentConclusion.UNVERIFIED
    elif differences:
        conclusion = AssessmentConclusion.NOT_STANDARDS_COMPLETE
    else:
        conclusion = AssessmentConclusion.STANDARDS_COMPLETE

    return _AssessmentCalculation(
        RepositoryAssessment(
            conclusion=conclusion,
            scope=scope,
            lifecycle=lifecycle,
            satisfied_requirements=tuple(satisfied),
            differences=tuple(differences),
            evidence_gaps=tuple(evidence_gaps),
            automatic_corrections=tuple(corrections),
            required_maintainer_work=tuple(maintainer_work),
            preservation_evidence=tuple(preservation),
            application_report=application_report,
        ),
        content_reconciliation,
        github_snapshot,
        github_reconciliation,
        tuple(remote_blockers),
    )


def assess_repository(
    contract: RepositoryContract,
    github_adapter: RepositoryObserver,
    *,
    scope: AssessmentScope = AssessmentScope.REPOSITORY,
) -> RepositoryAssessment:
    """Observe and calculate one deterministic repository assessment."""

    return _calculate_assessment(
        contract,
        github_adapter,
        scope=scope,
    ).assessment


def _operation_action(operation: ContentCorrection) -> str:
    return f"{_operation_kind(operation).value.upper()} {operation.target}"


def _operation_kind(operation: ContentCorrection) -> CorrectionKind:
    if operation.mode == "absent":
        return CorrectionKind.DELETE
    if operation.status == "missing":
        return CorrectionKind.CREATE
    return CorrectionKind.UPDATE


def _remaining_work(assessment: RepositoryAssessment) -> tuple[str, ...]:
    corrections = tuple(
        f"{correction.subject}: {correction.action}"
        for correction in assessment.automatic_corrections
    )
    maintainer_work = tuple(
        f"{work.subject}: {work.action}"
        for work in assessment.required_maintainer_work
    )
    return corrections + maintainer_work


def _same_observation(
    earlier: _AssessmentCalculation, later: _AssessmentCalculation
) -> bool:
    return (
        earlier.content_reconciliation == later.content_reconciliation
        and earlier.github_snapshot == later.github_snapshot
        and earlier.github_reconciliation == later.github_reconciliation
        and earlier.assessment == later.assessment
    )


def _blocking_evidence_gaps(
    assessment: RepositoryAssessment,
) -> tuple[AssessmentEntry, ...]:
    restricted_gap = (
        f"{assessment.scope.value}-only assessment cannot prove "
        "repository completeness"
        if assessment.scope is not AssessmentScope.REPOSITORY
        else None
    )
    return tuple(
        gap
        for gap in assessment.evidence_gaps
        if gap.description != restricted_gap
    )


def _github_repair_permission_error(
    calculation: _AssessmentCalculation,
) -> str | None:
    reconciliation = calculation.github_reconciliation
    snapshot = calculation.github_snapshot
    if reconciliation is None or snapshot is None or not reconciliation.operations:
        return None
    permissions = snapshot.repository.get("permissions")
    if not isinstance(permissions, dict):
        return "GitHub repair permissions could not be proven"
    missing = tuple(
        permission
        for permission in ("admin", "push")
        if permissions.get(permission) is not True
    )
    if not missing:
        return None
    return "GitHub repair requires permission: " + ", ".join(missing)


def _reassess_with_report(
    contract: RepositoryContract,
    github_adapter: GitHubAdapter,
    scope: AssessmentScope,
    report: ApplicationReport,
) -> RepositoryAssessment:
    return _calculate_assessment(
        contract,
        github_adapter,
        scope=scope,
        application_report=report,
    ).assessment


def repair_repository(
    contract: RepositoryContract,
    github_adapter: GitHubAdapter,
    *,
    scope: AssessmentScope = AssessmentScope.REPOSITORY,
    preview: Callable[[RepositoryAssessment], None],
) -> RepositoryAssessment:
    """Preview, safely apply, and re-assess automatic repository corrections."""

    initial = _calculate_assessment(contract, github_adapter, scope=scope)
    preview(initial.assessment)
    remaining = _remaining_work(initial.assessment)

    blocking_gaps = _blocking_evidence_gaps(initial.assessment)
    content_blockers = (
        initial.content_reconciliation.blockers if initial.content_reconciliation is not None else ()
    )
    permission_error = _github_repair_permission_error(initial)
    if (
        blocking_gaps
        or content_blockers
        or initial.remote_blockers
        or permission_error
    ):
        report = ApplicationReport(
            failed="preflight",
            error=(
                "repository repair has deterministic GitHub blockers"
                if initial.remote_blockers
                else permission_error
                or "repository repair requires complete, unblocked preflight evidence"
            ),
            remaining=remaining,
        )
        return replace(initial.assessment, application_report=report)

    current = _calculate_assessment(contract, github_adapter, scope=scope)
    if not _same_observation(initial, current):
        report = ApplicationReport(
            failed="stale-observation",
            error="repository state changed after preview; run repair again",
            remaining=_remaining_work(current.assessment),
        )
        return replace(current.assessment, application_report=report)

    completed: list[str] = []
    if current.content_reconciliation is not None:
        local_report = apply_content_reconciliation(current.content_reconciliation)
        completed.extend(
            f"repository-content: {_operation_action(operation)}"
            for operation in current.content_reconciliation.changes
            if operation.target in local_report.completed
        )
        if not local_report.succeeded:
            assert local_report.failed is not None
            report = ApplicationReport(
                completed=tuple(completed),
                failed=f"repository-content: {local_report.failed.target}",
                error=local_report.failed.message,
                remaining=(
                    *(
                        f"repository-content: {_operation_action(operation)}"
                        for operation in current.content_reconciliation.changes
                        if operation.target in local_report.remaining
                    ),
                    *(
                        f"github: {operation.description}"
                        for operation in (
                            current.github_reconciliation.operations
                            if current.github_reconciliation is not None
                            else ()
                        )
                    ),
                ),
            )
            return _reassess_with_report(
                contract, github_adapter, scope, report
            )

    if current.github_reconciliation is not None and current.github_reconciliation.operations:
        github_current = _calculate_assessment(
            contract, github_adapter, scope=AssessmentScope.GITHUB
        )
        if (
            github_current.github_snapshot != current.github_snapshot
            or github_current.github_reconciliation != current.github_reconciliation
        ):
            report = ApplicationReport(
                completed=tuple(completed),
                failed="github: stale-observation",
                error="GitHub state changed after preview; run repair again",
                remaining=tuple(
                    f"github: {operation.description}"
                    for operation in current.github_reconciliation.operations
                ),
            )
            return _reassess_with_report(
                contract, github_adapter, scope, report
            )

        github_report = apply_github_reconciliation(current.github_reconciliation, github_adapter)
        completed.extend(
            f"github: {operation.description}"
            for operation in github_report.completed
        )
        if not github_report.complete:
            assert github_report.failed is not None
            report = ApplicationReport(
                completed=tuple(completed),
                failed=f"github: {github_report.failed.description}",
                error=github_report.error,
                remaining=tuple(
                    f"github: {operation.description}"
                    for operation in github_report.remaining
                ),
            )
            return _reassess_with_report(
                contract, github_adapter, scope, report
            )

    report = ApplicationReport(completed=tuple(completed))
    final = _calculate_assessment(
        contract, github_adapter, scope=scope, application_report=report
    )
    verification_gaps = _blocking_evidence_gaps(final.assessment)
    if final.assessment.automatic_corrections or verification_gaps:
        report = replace(
            report,
            failed="verification",
            error="repository repair could not prove its automatic corrections",
            remaining=(
                *_remaining_work(final.assessment),
                *(
                    f"{gap.subject}: {gap.description}"
                    for gap in verification_gaps
                ),
            ),
        )
        return replace(final.assessment, application_report=report)
    if final.assessment.required_maintainer_work:
        return replace(
            final.assessment,
            application_report=replace(
                report,
                remaining=_remaining_work(final.assessment),
            ),
        )
    return final.assessment
