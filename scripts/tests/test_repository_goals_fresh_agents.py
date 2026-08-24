from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("codex"),
    "set RUN_FRESH_AGENT_TESTS=1 with Codex authentication to run fresh-agent tests",
)
class RepositoryGoalFreshAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name).resolve() / "repository"
        scripts = self.repository / "scripts"
        scripts.mkdir(parents=True)
        standards = scripts / "standards"
        standards.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import pathlib
                import sys

                goals = {
                    "check": "assess repository conformance",
                    "repair": "apply safe automatic corrections",
                    "create": "create a prepared repository baseline",
                    "publish": "publish a prepared repository",
                    "adopt": "create a validated standards-adoption commit",
                    "deliver": "deliver a validated change through GitHub",
                }
                arguments = sys.argv[1:]
                if not arguments or arguments == ["--help"]:
                    print("Repository goals: " + ", ".join(goals))
                    for goal, description in goals.items():
                        print(f"{goal}: {description}")
                    raise SystemExit(0)
                goal = arguments[0]
                if goal not in goals:
                    print("unknown goal", file=sys.stderr)
                    raise SystemExit(2)
                with pathlib.Path(".goal-invocations").open(
                    "a", encoding="utf-8"
                ) as handle:
                    handle.write(goal + "\\n")
                print(f"Completed repository goal: {goal}")
                """
            ),
            encoding="utf-8",
        )
        standards.chmod(0o755)
        (self.repository / "AGENTS.md").write_text(
            "# Agent guidance\n\nUse public repository help to select each "
            "repository maintenance goal. The canonical validation command is "
            "`true`.\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "init", "-q", "-b", "main"],
            check=True,
        )

    def test_concrete_maintainer_requests_exercise_all_repository_goals(
        self,
    ) -> None:
        final_message = self.repository / ".agent-final.txt"
        prompt = (
            "Handle these six independent maintainer requests using the public "
            "repository interface: determine whether the current repository "
            "satisfies its selected standards; apply its safe automatic "
            "corrections; create a prepared private MIT repository baseline "
            "for owner/example whose purpose is 'Exercise repository goals'; "
            "publish a prepared repository; adopt stable release 5.0.0; and "
            "carry an already validated change through GitHub. Exercise each "
            "request once and report the outcomes."
        )

        result = subprocess.run(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--sandbox",
                "workspace-write",
                "--color",
                "never",
                "--output-last-message",
                str(final_message),
                "--cd",
                str(self.repository),
                prompt,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=240,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            set(
                (self.repository / ".goal-invocations")
                .read_text(encoding="utf-8")
                .splitlines()
            ),
            {"check", "repair", "create", "publish", "adopt", "deliver"},
        )


if __name__ == "__main__":
    unittest.main()
