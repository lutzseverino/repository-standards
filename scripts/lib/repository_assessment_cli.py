"""Command adapter for repository-level standards check and repair goals."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .github_reconciliation import GitHubAdapter, GitHubCliAdapter
from .publication_goal import run_publish_goal
from .repository_assessment import (
    AssessmentConclusion,
    AssessmentScope,
    RepositoryAssessment,
    assess_repository,
    repair_repository,
)
from .repository_contract import (
    ContractError,
    build_initial_repository_contract,
    resolve_repository_contract,
)


EXIT_STATUS = {
    AssessmentConclusion.STANDARDS_COMPLETE: 0,
    AssessmentConclusion.NOT_STANDARDS_COMPLETE: 1,
    AssessmentConclusion.UNVERIFIED: 2,
}


def _entries(values) -> list[dict[str, str]]:
    return [
        {"subject": value.subject, "description": value.description}
        for value in values
    ]


def assessment_mapping(assessment: RepositoryAssessment) -> dict[str, Any]:
    """Return the stable JSON projection of a repository assessment."""

    application = assessment.application_report
    return {
        "conclusion": assessment.conclusion.value,
        "scope": assessment.scope.value,
        "lifecycle": (
            assessment.lifecycle.value if assessment.lifecycle is not None else None
        ),
        "satisfied-requirements": _entries(assessment.satisfied_requirements),
        "differences": [
            {
                "subject": difference.subject,
                "description": difference.description,
                "pending": difference.pending,
            }
            for difference in assessment.differences
        ],
        "evidence-gaps": _entries(assessment.evidence_gaps),
        "automatic-corrections": [
            {
                "subject": correction.subject,
                "action": correction.action,
                "kind": correction.kind.value,
                "target": correction.target,
            }
            for correction in assessment.automatic_corrections
        ],
        "required-maintainer-work": [
            {"subject": work.subject, "action": work.action}
            for work in assessment.required_maintainer_work
        ],
        "preservation-evidence": _entries(assessment.preservation_evidence),
        "application": (
            None
            if application is None
            else {
                "completed": list(application.completed),
                "failed": application.failed,
                "error": application.error,
                "remaining": list(application.remaining),
            }
        ),
    }


def render_assessment(
    assessment: RepositoryAssessment, *, verbose: bool = False
) -> str:
    """Render an actionable human assessment, with full evidence on request."""

    lines = [
        f"Conclusion: {assessment.conclusion.value}",
        f"Scope: {assessment.scope.value}",
        "Lifecycle: "
        + (
            assessment.lifecycle.value
            if assessment.lifecycle is not None
            else "unverified"
        ),
        "Counts: "
        f"{len(assessment.satisfied_requirements)} satisfied, "
        f"{len(assessment.differences)} differences, "
        f"{len(assessment.evidence_gaps)} evidence gaps, "
        f"{len(assessment.automatic_corrections)} automatic corrections, "
        f"{len(assessment.required_maintainer_work)} required maintainer actions, "
        f"{len(assessment.preservation_evidence)} preservation items",
    ]
    actionable_sections = (
        (
            "Differences",
            (
                f"[{item.subject}] {item.description}"
                for item in assessment.differences
            ),
        ),
        (
            "Evidence gaps",
            (
                f"[{item.subject}] {item.description}"
                for item in assessment.evidence_gaps
            ),
        ),
        (
            "Automatic corrections",
            (
                f"[{item.subject}] {item.action}"
                for item in assessment.automatic_corrections
            ),
        ),
        (
            "Required maintainer work",
            (
                f"[{item.subject}] {item.action}"
                for item in assessment.required_maintainer_work
            ),
        ),
    )
    evidence_sections = (
        (
            "Satisfied requirements",
            (
                f"[{item.subject}] {item.description}"
                for item in assessment.satisfied_requirements
            ),
        ),
        (
            "Preservation evidence",
            (
                f"[{item.subject}] {item.description}"
                for item in assessment.preservation_evidence
            ),
        ),
    )
    sections = (
        evidence_sections[:1] + actionable_sections + evidence_sections[1:]
        if verbose
        else actionable_sections
    )
    for title, values in sections:
        items = tuple(values)
        lines.extend(("", f"{title}:"))
        lines.extend(f"- {item}" for item in items or ("none",))

    report = assessment.application_report
    if report is not None:
        lines.extend(("", "Application report:", "- Completed:"))
        lines.extend(f"  - {item}" for item in report.completed or ("none",))
        lines.append(f"- Failed: {report.failed or 'none'}")
        if report.error:
            lines.append(f"- Error: {report.error}")
        lines.append("- Remaining:")
        lines.extend(f"  - {item}" for item in report.remaining or ("none",))
    return "\n".join(lines) + "\n"


def _add_repository_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "repository",
        nargs="?",
        default=".",
        help="participating repository (default: current directory)",
    )
    parser.add_argument(
        "--manifest", help="manifest path, relative to the repository"
    )
    parser.add_argument(
        "--scope",
        choices=tuple(scope.value for scope in AssessmentScope),
        default=AssessmentScope.REPOSITORY.value,
        help="explicit diagnostic scope (default: whole repository)",
    )


def standards_main(
    argv: list[str] | None = None,
    *,
    github_adapter: GitHubAdapter | None = None,
    _publication_state_home: Path | None = None,
    _allow_local_push_for_testing: bool = False,
) -> int:
    """Run one repository-level standards goal."""

    arguments = list(argv) if argv is not None else sys.argv[1:]
    standards_root = Path(__file__).resolve().parents[2]
    contract_input_arguments = (
        len(arguments) in (3, 4)
        and arguments[0] == "create"
        and arguments[1] == "--contract-input"
        and (
            len(arguments) == 3
            or arguments[3] == "--retain-content-blockers"
        )
    )
    if contract_input_arguments:
        retain_content_blockers = len(arguments) == 4
        try:
            initialization = json.loads(
                Path(arguments[2]).read_text(encoding="utf-8")
            )
            contract = build_initial_repository_contract(
                initialization,
                standards_root=standards_root,
                retain_content_blockers=retain_content_blockers,
            )
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            print(
                f"error: cannot build initial repository contract: {exc}",
                file=sys.stderr,
            )
            return 2
        output: dict[str, Any] = contract.as_mapping()
        if retain_content_blockers:
            output = {
                "contract": output,
                "conflicts": [
                    {"target": blocker.target, "message": blocker.message}
                    for blocker in contract.content_blockers
                ],
            }
        print(json.dumps(output, indent=2))
        return 0

    parser = argparse.ArgumentParser(
        prog="standards",
        description="Perform one repository standards goal",
    )
    commands = parser.add_subparsers(dest="goal", required=True)
    check = commands.add_parser("check", help="assess repository conformance")
    _add_repository_arguments(check)
    check_output = check.add_mutually_exclusive_group()
    check_output.add_argument("--json", action="store_true", dest="json_output")
    check_output.add_argument(
        "--verbose",
        action="store_true",
        help="include complete satisfied and preservation evidence",
    )
    repair = commands.add_parser(
        "repair", help="preview and apply safe automatic corrections"
    )
    _add_repository_arguments(repair)
    repair.add_argument(
        "--verbose",
        action="store_true",
        help="include complete satisfied and preservation evidence",
    )
    create = commands.add_parser(
        "create", help="create a prepared repository baseline"
    )
    create.add_argument("--name", required=True)
    create.add_argument("--purpose", required=True)
    create.add_argument(
        "--visibility", required=True, choices=("private", "public", "internal")
    )
    create.add_argument("--license", required=True)
    create.add_argument("--owner", required=True)
    create.add_argument("--destination", default=".")
    create.add_argument("--validation-executable", required=True)
    create.add_argument("--validation-argument", action="append", default=[])
    create.add_argument("--validation-working-directory", default=".")
    create.add_argument("--version")
    create.add_argument("--fact", action="append", default=[])
    create.add_argument("--profile", action="append", default=[])
    publish = commands.add_parser(
        "publish", help="publish a prepared repository for the first time"
    )
    publish.add_argument("repository", nargs="?", default=".")
    publish.add_argument("--confirm")
    adopt = commands.add_parser(
        "adopt", help="prepare and commit a standards adoption"
    )
    adopt.add_argument("version", nargs="?")
    adopt.add_argument("--repository", default=".")
    adopt.add_argument("--validation-executable")
    adopt.add_argument("--validation-argument", action="append", default=[])
    adopt.add_argument("--validation-working-directory", default=".")
    adopt.add_argument("--github-repository")
    adopt.add_argument("--title")
    adopt.add_argument("--fact", action="append", default=[])
    adopt.add_argument("--profile", action="append", default=[])
    adopt.add_argument("--repository-owned", action="append", default=[])
    adopt.add_argument("--no-ruleset", action="store_true")
    adopt.add_argument("--confirm")
    args = parser.parse_args(arguments)

    if args.goal == "create":
        command = [
            sys.executable,
            str(
                standards_root
                / ".agents/skills/create-repository/scripts/create"
            ),
            "--name",
            args.name,
            "--purpose",
            args.purpose,
            "--visibility",
            args.visibility,
            "--license",
            args.license,
            "--owner",
            args.owner,
            "--destination",
            str(Path(args.destination).expanduser().resolve()),
            "--validation-executable",
            args.validation_executable,
            "--validation-working-directory",
            args.validation_working_directory,
        ]
        for argument in args.validation_argument:
            command.append(f"--validation-argument={argument}")
        if args.version:
            command.extend(("--version", args.version))
        for fact in args.fact:
            command.extend(("--fact", fact))
        for profile in args.profile:
            command.extend(("--profile", profile))
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    if args.goal == "publish":
        return run_publish_goal(
            Path(args.repository),
            github_adapter or GitHubCliAdapter(),
            standards_root=standards_root,
            confirmation=args.confirm,
            state_home=_publication_state_home,
            allow_local_push_for_testing=_allow_local_push_for_testing,
        )

    if args.goal == "adopt":
        command = [
            sys.executable,
            str(
                standards_root
                / ".agents/skills/adopt-standards/scripts/adopt"
            ),
            "--repository",
            str(Path(args.repository).expanduser().resolve()),
        ]
        if args.validation_executable:
            command.extend(("--validation-executable", args.validation_executable))
        for argument in args.validation_argument:
            command.append(f"--validation-argument={argument}")
        if args.validation_working_directory != ".":
            command.extend(
                (
                    "--validation-working-directory",
                    args.validation_working_directory,
                )
            )
        if args.github_repository:
            command.extend(("--github-repository", args.github_repository))
        if args.title:
            command.extend(("--title", args.title))
        for fact in args.fact:
            command.extend(("--fact", fact))
        for profile in args.profile:
            command.extend(("--profile", profile))
        for pattern in args.repository_owned:
            command.extend(("--repository-owned", pattern))
        if args.no_ruleset:
            command.append("--no-ruleset")
        if args.confirm:
            command.extend(("--confirm", args.confirm))
        if args.version:
            command.append(args.version)
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode

    if args.goal not in {"check", "repair"}:
        print(
            f"error: standards {args.goal} is not yet available",
            file=sys.stderr,
        )
        return 2

    repository = Path(args.repository).expanduser().resolve()
    try:
        contract = resolve_repository_contract(
            repository,
            standards_root=standards_root,
            manifest=args.manifest,
            retain_content_blockers=True,
        )
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    adapter = github_adapter or GitHubCliAdapter()
    scope = AssessmentScope(args.scope)
    if args.goal == "check":
        assessment = assess_repository(contract, adapter, scope=scope)
        if args.json_output:
            print(json.dumps(assessment_mapping(assessment), indent=2))
        else:
            print(render_assessment(assessment, verbose=args.verbose), end="")
        return EXIT_STATUS[assessment.conclusion]

    print("Assessment before repair:")

    def preview(assessment: RepositoryAssessment) -> None:
        print(render_assessment(assessment, verbose=args.verbose), end="")
        sys.stdout.flush()

    assessment = repair_repository(
        contract,
        adapter,
        scope=scope,
        preview=preview,
    )
    print("\nAssessment after repair:")
    print(render_assessment(assessment, verbose=args.verbose), end="")
    report = assessment.application_report
    if report is not None and not report.succeeded:
        return 2
    return EXIT_STATUS[assessment.conclusion]
