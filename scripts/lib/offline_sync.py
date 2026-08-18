"""Plan and apply offline repository synchronization from one contract."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .repository_contract import RepositoryContract
from .standards import (
    StandardsError,
    _preview_text,
    _validate_managed_target,
    inspect,
)


@dataclass(frozen=True)
class SynchronizationBlocker:
    target: str
    message: str
    intended_action: str


@dataclass(frozen=True)
class SynchronizationOperation:
    target: str
    status: str
    mode: str
    expected: bytes
    actual: bytes | None
    origins: tuple[str, ...]


@dataclass(frozen=True)
class SynchronizationPlan:
    contract: RepositoryContract
    operations: tuple[SynchronizationOperation, ...]
    blockers: tuple[SynchronizationBlocker, ...]

    @property
    def changes(self) -> tuple[SynchronizationOperation, ...]:
        return tuple(
            operation for operation in self.operations if operation.status != "ok"
        )


@dataclass(frozen=True)
class FailedOperation:
    target: str
    message: str


@dataclass(frozen=True)
class ApplicationReport:
    completed: tuple[str, ...]
    failed: FailedOperation | None
    remaining: tuple[str, ...]

    @property
    def succeeded(self) -> bool:
        return self.failed is None


def plan_synchronization(contract: RepositoryContract) -> SynchronizationPlan:
    """Inspect every managed target and retain all deterministic blockers."""

    operations: list[SynchronizationOperation] = []
    blockers: list[SynchronizationBlocker] = []
    contract_blockers: dict[str, list[str]] = {}
    for blocker in contract.plan_blockers:
        contract_blockers.setdefault(blocker.target, []).append(blocker.message)
    for managed_file in contract.managed_files:
        try:
            result = inspect(contract.repository, (managed_file,))[0]
        except StandardsError as exc:
            blockers.append(
                SynchronizationBlocker(managed_file.target, str(exc), "INVALID")
            )
            continue

        intended_action = _intended_action(result.status, result.mode)
        target_contract_blockers = contract_blockers.pop(result.target, [])
        blockers.extend(
            SynchronizationBlocker(result.target, message, intended_action)
            for message in target_contract_blockers
        )
        if result.status == "not-file":
            if result.mode == "absent":
                message = "managed absence requires a regular file"
            else:
                message = "managed target is not a regular file"
            blockers.append(
                SynchronizationBlocker(result.target, message, intended_action)
            )
            continue
        ignored_error = _ignored_managed_absence(contract.repository, result)
        if ignored_error:
            blockers.append(
                SynchronizationBlocker(
                    result.target,
                    ignored_error,
                    intended_action,
                )
            )
            continue
        if target_contract_blockers:
            continue
        operations.append(
            SynchronizationOperation(
                target=result.target,
                status=result.status,
                mode=result.mode,
                expected=result.expected,
                actual=result.actual,
                origins=result.origins,
            )
        )

    for target, messages in contract_blockers.items():
        blockers.extend(
            SynchronizationBlocker(target, message, "INVALID")
            for message in messages
        )
    return SynchronizationPlan(contract, tuple(operations), tuple(blockers))


def _intended_action(status: str, mode: str) -> str:
    if status == "ok":
        return "PRESERVE"
    if mode == "absent":
        return "DELETE"
    if status == "missing":
        return "CREATE"
    if status == "not-file":
        return "INVALID"
    return "UPDATE"


def _ignored_managed_absence(repository: Path, result) -> str | None:
    if result.mode != "absent" or result.status != "present":
        return None
    if not (repository / ".git").exists():
        return None
    try:
        check = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "check-ignore",
                "--quiet",
                "--",
                result.target,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return f"cannot inspect ignore status for managed absence: {exc}"
    if check.returncode == 0:
        return "ignored managed absence cannot be previewed reliably"
    if check.returncode == 1:
        return None
    return "cannot inspect ignore status for managed absence: " + (
        check.stderr.strip() or check.stdout.strip() or f"git exited {check.returncode}"
    )


def render_synchronization_preview(plan: SynchronizationPlan) -> str:
    """Render every preservation, intended change, and deterministic blocker."""

    parts: list[str] = []
    for operation in plan.operations:
        if operation.status == "ok":
            suffix = " (absent)" if operation.mode == "absent" else ""
            parts.append(f"PRESERVE {operation.target}{suffix}\n")
        elif operation.mode == "absent":
            parts.append(_preview_text(operation))
        elif operation.status == "missing":
            parts.append(f"CREATE   {operation.target}\n")
            parts.append(_preview_text(operation))
        else:
            parts.append(f"UPDATE   {operation.target}\n")
            parts.append(_preview_text(operation))
    for blocker in plan.blockers:
        parts.append(f"{blocker.intended_action:<8} {blocker.target}\n")
        parts.append(f"BLOCKED  {blocker.target} ({blocker.message})\n")
    return "".join(parts)


def _apply_operation(
    repository: Path, operation: SynchronizationOperation
) -> None:
    target = repository / operation.target
    _validate_managed_target(repository, target, operation.target)
    if target.exists() and not target.is_file():
        raise StandardsError(f"managed target is not a file: {operation.target}")
    if operation.mode == "absent":
        target.unlink()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(operation.expected)


def apply_synchronization_plan(plan: SynchronizationPlan) -> ApplicationReport:
    """Apply the plan in order and report exact partial progress on failure."""

    changes = plan.changes
    if plan.blockers:
        return ApplicationReport(
            (),
            FailedOperation(
                "preflight",
                f"{len(plan.blockers)} deterministic blocker(s) prevent application",
            ),
            tuple(operation.target for operation in changes),
        )

    completed: list[str] = []
    for index, operation in enumerate(changes):
        try:
            current = inspect(
                plan.contract.repository,
                (
                    next(
                        item
                        for item in plan.contract.managed_files
                        if item.target == operation.target
                    ),
                ),
            )[0]
            if current.status != operation.status or current.actual != operation.actual:
                raise StandardsError(
                    "target changed after planning; create a new synchronization plan"
                )
            _apply_operation(plan.contract.repository, operation)
        except (OSError, StandardsError) as exc:
            return ApplicationReport(
                tuple(completed),
                FailedOperation(operation.target, str(exc)),
                tuple(item.target for item in changes[index + 1 :]),
            )
        completed.append(operation.target)

    return ApplicationReport(tuple(completed), None, ())
