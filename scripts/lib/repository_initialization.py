"""Plan and write a validated initial repository contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .repository_contract import (
    ContractError,
    InitialRepositoryContract,
    build_initial_repository_contract,
)


class InitializationError(Exception):
    """Raised when an initial repository contract cannot be planned safely."""


@dataclass(frozen=True)
class InitializationPlan:
    """A validated initial contract and its still-empty local destination."""

    destination: Path
    contract: InitialRepositoryContract


def _destination_path(value: Path) -> Path:
    requested = value.expanduser()
    if not requested.is_absolute():
        requested = Path.cwd() / requested
    if requested == Path(requested.anchor):
        raise InitializationError("repository destination must not be a filesystem root")

    for candidate in (requested, *requested.parents):
        if candidate == Path(candidate.anchor):
            break
        if candidate.is_symlink():
            raise InitializationError(
                f"repository destination traverses a symbolic link: {candidate}"
            )

    destination = requested.resolve(strict=False)
    if destination.exists():
        if not destination.is_dir():
            raise InitializationError(
                f"repository destination is not an empty directory: {destination}"
            )
        try:
            occupied = next(destination.iterdir(), None)
        except OSError as exc:
            raise InitializationError(
                f"cannot inspect repository destination {destination}: {exc}"
            ) from exc
        if occupied is not None:
            raise InitializationError(
                f"repository destination is not empty: {destination}"
            )
    return destination


def plan_repository_initialization(
    destination: Path,
    initialization: Mapping[str, Any],
    *,
    standards_root: Path,
) -> InitializationPlan:
    """Return a complete validated contract without mutating its destination."""

    target = _destination_path(destination)
    try:
        contract = build_initial_repository_contract(
            initialization,
            standards_root=standards_root,
        )
    except ContractError as exc:
        raise InitializationError(str(exc)) from exc
    return InitializationPlan(target, contract)


def apply_repository_initialization(plan: InitializationPlan) -> Path:
    """Write a prevalidated contract after rechecking the empty destination."""

    destination = _destination_path(plan.destination)
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path = destination / ".repository-standards.json"
    manifest_path.write_text(
        json.dumps(plan.contract.as_mapping(), indent=2) + "\n", encoding="utf-8"
    )
    return manifest_path
