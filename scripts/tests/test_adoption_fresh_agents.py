from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SKILL_SOURCE = ROOT / "bootstrap/adopt-standards"
RELEASE_SKILL_SOURCE = (
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
        shutil.copytree(BOOTSTRAP_SKILL_SOURCE, skill)
        self.release = Path(self.temporary.name) / "release"
        release_skill = self.release / ".agents/skills/adopt-standards"
        shutil.copytree(RELEASE_SKILL_SOURCE, release_skill)
        runner = release_skill / "scripts/adopt"
        runner.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import pathlib
                import sys

                arguments = sys.argv[1:]
                with open(os.environ["FAKE_ADOPTION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("\\0".join(arguments) + "\\n")
                confirmation = "Adopt initial standards proposal deterministic"
                if "--confirm" not in arguments:
                    print("Initial standards adoption proposal deterministic")
                    print("Selected exact release: 6.0.0")
                    print("Complete repository contract: {}")
                    print("Managed environment and declared GitHub assessment: {}")
                    print("Conflicts and differences: none")
                    print("Automatic corrections: install release-pinned skills")
                    print("Required maintainer work: none")
                    print(f"Exact confirmation required: {confirmation}")
                    print("No repository or GitHub mutation was performed.")
                    raise SystemExit(0)
                supplied = arguments[arguments.index("--confirm") + 1]
                if supplied != confirmation:
                    print("error: proposal is stale", file=sys.stderr)
                    raise SystemExit(2)
                print("Prepared initial standards adoption for 6.0.0; validated adoption commit: fake.")
                print("GitHub delivery remains a separate lifecycle transition.")
                """
            ),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        (self.release / "VERSION").write_text("6.0.0\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.release), "init", "-q", "-b", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.release), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.release),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(self.release), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.release), "commit", "-qm", "release fixture"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "tag.gpgSign=false",
                "-C",
                str(self.release),
                "tag",
                "-a",
                "v6.0.0",
                "-m",
                "release 6.0.0",
            ],
            check=True,
        )
        self.adoption_log = Path(self.temporary.name) / "adoption.log"
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
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repository),
                "remote",
                "add",
                "origin",
                "https://github.com/owner/example.git",
            ],
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
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(self.release),
                "FAKE_ADOPTION_LOG": str(self.adoption_log),
            }
        )
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
            env=environment,
        )

    def invocations(self) -> list[list[str]]:
        return [
            line.split("\0")
            for line in self.adoption_log.read_text(encoding="utf-8").splitlines()
        ]

    def final_message(self) -> str:
        return (self.repository / ".agent-final.txt").read_text(encoding="utf-8")

    def test_standalone_initial_adoption_stops_at_the_complete_proposal(self) -> None:
        result = self.run_fresh_agent(
            "Begin initial adoption of exact standards release 6.0.0 for "
            "owner/example. This is an unsupported Elixir repository. Follow "
            "repository guidance and stop at any required confirmation boundary."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = self.invocations()
        self.assertEqual(len(invocations), 1)
        invocation = invocations[0]
        self.assertIn("--validation-executable", invocation)
        self.assertIn("true", invocation)
        self.assertIn("ecosystem=elixir", [item.lower() for item in invocation])
        self.assertIn("6.0.0", invocation)
        self.assertNotIn("--confirm", invocation)
        self.assertFalse((self.repository / ".workflow-invoked").exists())
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.original_head)
        self.assertIn("exact confirmation", self.final_message().lower())

    def test_exact_confirmation_resumes_only_the_current_initial_proposal(
        self,
    ) -> None:
        proposed = self.run_fresh_agent(
            "Begin initial adoption of exact standards release 6.0.0 for "
            "owner/example. This is an unsupported Elixir repository. Follow "
            "repository guidance and stop at the confirmation boundary."
        )
        self.assertEqual(proposed.returncode, 0, proposed.stderr)

        confirmed = self.run_fresh_agent(
            "I reviewed the current complete proposal. Confirm it exactly with: "
            "Adopt initial standards proposal deterministic. Continue the same "
            "initial adoption and report its lifecycle boundary accurately."
        )

        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        invocations = self.invocations()
        self.assertEqual(len(invocations), 2)
        self.assertNotIn("--confirm", invocations[0])
        self.assertIn("--confirm", invocations[1])
        self.assertIn(
            "Adopt initial standards proposal deterministic", invocations[1]
        )
        final = self.final_message().lower()
        self.assertIn("validated adoption commit", final)
        self.assertIn("github delivery", final)
        self.assertIn("separate", final)


if __name__ == "__main__":
    unittest.main()
