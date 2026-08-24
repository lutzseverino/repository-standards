from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_SOURCE = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills"
    / "adopt-standards"
)


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("codex"),
    "set RUN_FRESH_AGENT_TESTS=1 with Codex authentication to run fresh-agent tests",
)
class AdoptionFreshAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name) / "repository"
        self.repository.mkdir()
        skill = self.repository / ".agents/skills/adopt-standards"
        shutil.copytree(SKILL_SOURCE, skill)
        runner = skill / "scripts/adopt"
        runner.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import pathlib
                import sys

                pathlib.Path(".adoption-invoked").write_text(
                    " ".join(sys.argv[1:]) + "\\n", encoding="utf-8"
                )
                print("Prepared fake standards adoption; changes remain uncommitted.")
                """
            ),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        (self.repository / "AGENTS.md").write_text(
            "# Agent guidance\n\nThe canonical validation command is `true`.\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "init", "-q", "-b", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repository),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(self.repository), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.repository), "commit", "-qm", "fixture"],
            check=True,
        )
        self.original_head = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_fresh_agent(self, prompt: str) -> subprocess.CompletedProcess[str]:
        final_message = self.repository / ".agent-final.txt"
        return subprocess.run(
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
            timeout=180,
        )

    def test_standalone_invocation_performs_only_adoption(self) -> None:
        result = self.run_fresh_agent(
            "Adopt standards release 2.0.0. Follow repository guidance to completion."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        invocation = (self.repository / ".adoption-invoked").read_text(
            encoding="utf-8"
        )
        self.assertIn("--validation-command true", invocation)
        self.assertIn("2.0.0", invocation)
        self.assertFalse((self.repository / ".workflow-invoked").exists())
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.original_head)

    def test_user_supplied_workflow_composes_without_becoming_part_of_adoption(
        self,
    ) -> None:
        workflow = self.repository / "user-workflow"
        workflow.write_text(
            "#!/bin/sh\nprintf 'user-selected\\n' > .workflow-invoked\n",
            encoding="utf-8",
        )
        workflow.chmod(0o755)
        self.git("add", "user-workflow")
        self.git("commit", "-qm", "add independent workflow")
        self.original_head = self.git("rev-parse", "HEAD").stdout.strip()

        result = self.run_fresh_agent(
            "Adopt standards release 2.0.0. After it succeeds, run the "
            "independently supplied ./user-workflow command."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        adoption_invocation = (self.repository / ".adoption-invoked").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("user-workflow", adoption_invocation)
        self.assertEqual(
            (self.repository / ".workflow-invoked").read_text(encoding="utf-8"),
            "user-selected\n",
        )
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.original_head)


if __name__ == "__main__":
    unittest.main()
