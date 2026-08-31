from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from collections.abc import Mapping, Sequence
from pathlib import Path


class LifecycleTestCase(unittest.TestCase):
    workspace: Path

    def setUp(self) -> None:
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name).resolve()

    def write_executable(self, relative_path: str, source: str) -> Path:
        executable = self.workspace / relative_path
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(textwrap.dedent(source), encoding="utf-8")
        executable.chmod(0o755)
        return executable

    def isolated_environment(
        self,
        overrides: Mapping[str, str] | None = None,
        *,
        executable_directory: Path | None = None,
    ) -> dict[str, str]:
        home = self.workspace / "home"
        home.mkdir(exist_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "XDG_STATE_HOME": str(home / ".local/state"),
            }
        )
        if executable_directory is not None:
            environment["PATH"] = (
                str(executable_directory) + os.pathsep + environment["PATH"]
            )
        if overrides:
            environment.update(overrides)
        return environment

    def seal_release(self, release: Path, version: str) -> Path:
        commands = (
            ["git", "-C", str(release), "init", "-q", "-b", "main"],
            ["git", "-C", str(release), "config", "user.name", "Test User"],
            [
                "git",
                "-C",
                str(release),
                "config",
                "user.email",
                "test@example.com",
            ],
            ["git", "-C", str(release), "add", "."],
            ["git", "-C", str(release), "commit", "-qm", "release fixture"],
            [
                "git",
                "-c",
                "tag.gpgSign=false",
                "-C",
                str(release),
                "tag",
                "-a",
                f"v{version}",
                "-m",
                f"release {version}",
            ],
        )
        for command in commands:
            subprocess.run(command, check=True, capture_output=True, text=True)
        return release

    def invoke_lifecycle(
        self,
        arguments: Sequence[str],
        *,
        environment: Mapping[str, str],
        cwd: Path | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
