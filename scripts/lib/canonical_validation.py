#!/usr/bin/env python3
"""Execute a repository's declared canonical validation without a shell."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.repository_contract import (  # noqa: E402
    ContractError,
    RepositoryContract,
    resolve_repository_contract,
)


def _working_directory(contract: RepositoryContract) -> Path:
    declared = contract.repository / contract.canonical_validation.working_directory
    try:
        working_directory = declared.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise ContractError(
            "canonical validation working directory is unavailable: "
            f"{contract.canonical_validation.working_directory!r}: {exc}"
        ) from exc
    if not working_directory.is_dir():
        raise ContractError(
            "canonical validation working directory is not a directory: "
            f"{contract.canonical_validation.working_directory!r}"
        )
    try:
        working_directory.relative_to(contract.repository)
    except ValueError as exc:
        raise ContractError(
            "canonical validation working directory escapes the repository: "
            f"{contract.canonical_validation.working_directory!r}"
        ) from exc
    return working_directory


def execute_canonical_validation(contract: RepositoryContract) -> int:
    """Execute the normalized declaration and return its exact process status."""

    validation = contract.canonical_validation
    command = [validation.executable, *validation.arguments]
    try:
        result = subprocess.run(
            command,
            cwd=_working_directory(contract),
            check=False,
        )
    except FileNotFoundError:
        print(
            "error: canonical validation executable is unavailable: "
            f"{validation.executable!r}",
            file=sys.stderr,
        )
        return 127
    except PermissionError as exc:
        print(
            "error: canonical validation executable cannot be invoked: "
            f"{validation.executable!r}: {exc}",
            file=sys.stderr,
        )
        return 126
    except OSError as exc:
        print(
            "error: canonical validation could not start "
            f"{validation.executable!r}: {exc}",
            file=sys.stderr,
        )
        return 126

    if result.returncode < 0:
        signal = -result.returncode
        print(
            f"error: canonical validation terminated by signal {signal}: "
            f"{validation.executable!r}",
            file=sys.stderr,
        )
        return min(128 + signal, 255)
    if result.returncode != 0:
        print(
            f"error: canonical validation exited with status {result.returncode}: "
            f"{validation.executable!r}",
            file=sys.stderr,
        )
    return result.returncode


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute a repository's structured canonical validation"
    )
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--standards-root", required=True)
    args = parser.parse_args(arguments)
    try:
        contract = resolve_repository_contract(
            Path(args.repository), standards_root=Path(args.standards_root)
        )
        return execute_canonical_validation(contract)
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
