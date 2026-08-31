from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.tests.lifecycle_support import LifecycleTestCase


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


if __name__ == "__main__":
    import unittest

    unittest.main()
