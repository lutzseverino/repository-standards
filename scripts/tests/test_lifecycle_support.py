from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if __package__:
    from .lifecycle_support import LifecycleTestCase
else:
    from lifecycle_support import LifecycleTestCase


class LifecycleTestSupportTests(LifecycleTestCase):
    def test_workspace_environment_executable_and_release_are_one_small_interface(
        self,
    ) -> None:
        executable = self.write_executable(
            "bin/tool",
            """\
            #!/bin/sh
            printf '%s' "$FIXTURE_VALUE"
            """,
        )
        environment = self.isolated_environment(
            {"FIXTURE_VALUE": "observable"},
            executable_directory=executable.parent,
        )
        release = self.workspace / "release"
        release.mkdir()
        (release / "VERSION").write_text("6.0.0\n", encoding="utf-8")

        self.seal_release(release, "6.0.0")
        result = self.invoke_lifecycle(
            [str(executable)], environment=environment
        )

        self.assertEqual(result.stdout, "observable")
        self.assertEqual(environment["HOME"], str(self.workspace / "home"))
        self.assertNotEqual(environment["HOME"], os.environ.get("HOME"))
        tag = subprocess.run(
            ["git", "-C", str(release), "describe", "--exact-match", "--tags"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(tag.stdout.strip(), "v6.0.0")

    def test_bootstrap_journey_remains_directly_executable(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/tests/test_bootstrap_creation.py",
                "BootstrapCreationJourneyTests."
                "test_quick_start_installs_only_the_two_user_scoped_bootstrap_skills",
            ],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_adoption_fresh_agent_helpers_preserve_their_process_contracts(
        self,
    ) -> None:
        if __package__:
            from .test_adoption_fresh_agents import AdoptionFreshAgentTests
        else:
            from test_adoption_fresh_agents import AdoptionFreshAgentTests

        repository = self.workspace / "repository"
        repository.mkdir()
        subprocess.run(["git", "-C", str(repository), "init", "-q"], check=True)
        case = object.__new__(AdoptionFreshAgentTests)
        case.repository = repository
        case.workspace = self.workspace
        case.release = self.workspace / "release"
        case.gh = self.workspace / "gh"
        case.isolated_environment = lambda overrides: {**overrides}
        observed: dict[str, object] = {}

        def invoke(arguments, **options):
            observed.update({"arguments": arguments, **options})
            return subprocess.CompletedProcess(arguments, 0, "", "")

        case.invoke_lifecycle = invoke

        status = case.git("status", "--short")
        result = case.run_fresh_agent("probe")

        self.assertEqual(status.returncode, 0)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            observed["environment"]["REPOSITORY_STANDARDS_GH"], str(case.gh)
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
