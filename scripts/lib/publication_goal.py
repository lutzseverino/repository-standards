"""Goal-oriented adapter for first publication."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .first_publication import (
    PublicationError,
    PublicationPlan,
    PublicationReport,
    load_publication_plan,
    plan_first_publication,
    publish_first_publication,
    write_publication_plan,
)
from .live_reconciliation import GitHubAdapter


def _private_state_root(override: Path | None) -> Path:
    if override is not None:
        parent = override.expanduser().resolve()
    elif os.environ.get("REPOSITORY_STANDARDS_STATE_HOME"):
        parent = Path(os.environ["REPOSITORY_STANDARDS_STATE_HOME"]).expanduser().resolve()
    elif os.environ.get("XDG_STATE_HOME"):
        parent = Path(os.environ["XDG_STATE_HOME"]).expanduser().resolve()
    else:
        parent = Path.home() / ".local/state"
    root = parent / "repository-standards/publication"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root.parent, 0o700)
    os.chmod(root, 0o700)
    return root


def _proposal_path(repository: Path, state_home: Path | None) -> Path:
    repository = repository.expanduser().resolve()
    root = _private_state_root(state_home)
    try:
        root.relative_to(repository)
    except ValueError:
        pass
    else:
        raise PublicationError(
            "lifecycle proposal state must remain outside the participating repository"
        )
    identity = hashlib.sha256(str(repository).encode("utf-8")).hexdigest()
    return root / f"{identity}.json"


def _render_proposal(proposal: PublicationPlan) -> None:
    timestamp = datetime.fromtimestamp(
        proposal.commit.timestamp, timezone.utc
    ).isoformat()
    print(f"Lifecycle proposal {proposal.plan_id}")
    print(f"- repository: {proposal.repository_name} ({proposal.repository})")
    print(
        f"- selected release: {proposal.standards_release} "
        f"(protocol {proposal.standards_protocol})"
    )
    print(f"- branch: {proposal.branch}")
    print(f"- origin: {proposal.remote_url}")
    print(f"- push target: {proposal.push_url}")
    print("\nInitial commit metadata:")
    print(f"- message: {proposal.commit.message}")
    print(
        "- author and committer: "
        f"{json.dumps(proposal.commit.author_name)} "
        f"<{json.dumps(proposal.commit.author_email)}>"
    )
    print(f"- timestamp: {timestamp}")
    print(f"- tree: {proposal.commit.tree_oid}")
    print("\nInitial commit contents:")
    for item in proposal.commit.files:
        print(f"- {item.mode} {item.object_id} {json.dumps(item.path)}")
    print("\nComplete ordered transition:")
    for step in proposal.steps:
        print(f"- {step}")
    print("\nDeclared GitHub operations:")
    print(
        json.dumps(
            [
                {
                    "description": operation.description,
                    "method": operation.method,
                    "endpoint": operation.endpoint,
                    "payload": operation.payload,
                }
                for operation in proposal.live_delta.operations
            ],
            indent=2,
            sort_keys=True,
        )
    )
    print("\nObserved starting state:")
    print(json.dumps(proposal.observed_github_state, indent=2, sort_keys=True))
    print("\nNo repository or GitHub mutation was performed.")
    print(f"Exact confirmation required: {proposal.confirmation}")


def _render_failure(report: PublicationReport) -> None:
    print(f"error: {report.error}", file=sys.stderr)
    print("Completed work:", file=sys.stderr)
    for step in report.completed or ("none",):
        print(f"- {step}", file=sys.stderr)
    if report.failed is not None:
        print(f"Failed work:\n- {report.failed}", file=sys.stderr)
    else:
        print(f"Completion unknown:\n- {report.uncertain}", file=sys.stderr)
    print("Remaining work:", file=sys.stderr)
    for step in report.remaining or ("none",):
        print(f"- {step}", file=sys.stderr)
    print("No destructive rollback was attempted.", file=sys.stderr)


def run_publish_goal(
    repository: Path,
    adapter: GitHubAdapter,
    *,
    standards_root: Path,
    confirmation: str | None,
    state_home: Path | None = None,
    allow_local_push_for_testing: bool = False,
) -> int:
    """Preview or execute first publication through one goal interface."""

    try:
        path = _proposal_path(repository, state_home)
        if confirmation is None:
            proposal = plan_first_publication(
                repository,
                adapter,
                standards_root=standards_root,
                _allow_local_push_for_testing=allow_local_push_for_testing,
            )
            write_publication_plan(proposal, path)
            os.chmod(path, 0o600)
            _render_proposal(proposal)
            return 0

        proposal = load_publication_plan(
            path,
            _allow_local_push_for_testing=allow_local_push_for_testing,
        )
        if confirmation != proposal.confirmation:
            raise PublicationError(
                "exact confirmation for the current lifecycle proposal is required"
            )
        try:
            path.unlink()
        except OSError as exc:
            raise PublicationError(
                f"cannot invalidate confirmed lifecycle proposal before execution: {exc}"
            ) from exc
        report = publish_first_publication(
            proposal,
            adapter,
            standards_root=standards_root,
            confirmation=confirmation,
        )
    except PublicationError as exc:
        message = str(exc).replace("publication Plan", "lifecycle proposal")
        print(f"error: {message}", file=sys.stderr)
        return 2

    if not report.complete:
        _render_failure(report)
        return 2
    print(f"Standards-complete repository: {proposal.repository_name}")
    print(f"- initial commit: {report.commit_oid}")
    print("- main is published and established as the default branch")
    print("- final repository assessment proves standards completeness")
    print("- no pull request was created")
    return 0
