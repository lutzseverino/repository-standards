from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path

from scripts.tests.lifecycle_support import LifecycleTestCase


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SKILL_SOURCE = ROOT / "bootstrap/adopt-standards"
INSTALLER_VERSION = "1.5.23"


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("codex"),
    "set RUN_FRESH_AGENT_TESTS=1 with Codex authentication to run fresh-agent tests",
)
class AdoptionFreshAgentTests(LifecycleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repository = self.workspace / "repository"
        self.repository.mkdir()
        install_environment = self.isolated_environment(
            {
                "npm_config_cache": str(self.workspace / "npm-cache"),
                "npm_config_update_notifier": "false",
            }
        )
        installed = subprocess.run(
            [
                "npx",
                "--yes",
                f"skills@{INSTALLER_VERSION}",
                "add",
                str(BOOTSTRAP_SKILL_SOURCE.parent),
                "--skill",
                "adopt-standards",
                "--agent",
                "universal",
                "--yes",
                "--copy",
            ],
            cwd=self.workspace,
            check=False,
            capture_output=True,
            text=True,
            env=install_environment,
        )
        self.assertEqual(
            installed.returncode, 0, installed.stdout + installed.stderr
        )
        self.assertTrue(
            (self.workspace / ".agents/skills/adopt-standards/SKILL.md").is_file()
        )
        (self.workspace / "AGENTS.md").write_text(
            "# Agent guidance\n\nUse only the installed bootstrap skill and the "
            "selected immutable release. Stop at explicit confirmation boundaries.\n",
            encoding="utf-8",
        )
        self.release = self.workspace / "release"
        shutil.copytree(
            ROOT,
            self.release,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        (self.release / "VERSION").write_text("6.0.0\n", encoding="utf-8")
        self.gh = self.workspace / "gh"
        self.gh.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import sys

                arguments = sys.argv[1:]
                if not arguments or arguments[0] != "api":
                    print(f"unexpected gh invocation: {arguments}", file=sys.stderr)
                    raise SystemExit(2)
                endpoint = arguments[1]
                labels = [
                    "bug", "enhancement", "needs-triage", "needs-info",
                    "ready-for-agent", "ready-for-human", "wontfix",
                ]
                if endpoint == "repos/owner/example":
                    print(json.dumps({
                        "full_name": "owner/example",
                        "default_branch": "main",
                        "delete_branch_on_merge": True,
                        "allow_squash_merge": True,
                        "allow_merge_commit": False,
                        "allow_rebase_merge": False,
                        "squash_merge_commit_title": "PR_TITLE",
                        "squash_merge_commit_message": "PR_BODY",
                        "has_issues": True,
                        "has_projects": False,
                        "has_wiki": False,
                        "permissions": {"admin": True, "push": True},
                    }))
                elif endpoint.startswith("repos/owner/example/labels"):
                    print(json.dumps([{"name": name} for name in labels]))
                elif endpoint.startswith("repos/owner/example/rulesets"):
                    print("[]")
                elif endpoint.startswith("repos/owner/example/branches"):
                    print(json.dumps([{"name": "main"}]))
                else:
                    print(f"unexpected gh endpoint: {endpoint}", file=sys.stderr)
                    raise SystemExit(2)
                """
            ),
            encoding="utf-8",
        )
        self.gh.chmod(0o755)
        self.seal_release(self.release, "6.0.0")
        (self.repository / "docs").mkdir()
        (self.repository / "README.md").write_text(
            '<div align="center">\n  <h1>example</h1>\n</div>\n\n'
            "See the [documentation](docs/README.md).\n",
            encoding="utf-8",
        )
        (self.repository / "docs/README.md").write_text(
            "# Documentation\n\nExisting project documentation.\n",
            encoding="utf-8",
        )
        (self.repository / "product.txt").write_text(
            "repository-owned product content\n",
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
        (self.workspace / ".gitignore").write_text(
            "/.agent-final.txt\n/gh\n/npm-cache/\n/release/\n/repository/\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.workspace), "init", "-q", "-b", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.workspace), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.workspace),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.workspace),
                "add",
                ".agents",
                ".gitignore",
                "AGENTS.md",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.workspace), "commit", "-qm", "isolated harness"],
            check=True,
        )

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.invoke_lifecycle(
            ["git", "-C", str(self.repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_fresh_agent(self, prompt: str) -> subprocess.CompletedProcess[str]:
        final_message = self.workspace / ".agent-final.txt"
        environment = self.isolated_environment(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(self.release),
                "REPOSITORY_STANDARDS_GH": str(self.gh),
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
                str(self.workspace),
                prompt,
            ],
            timeout=180,
            environment=environment,
        )

    def final_message(self) -> str:
        return (self.workspace / ".agent-final.txt").read_text(encoding="utf-8")

    def test_standalone_initial_adoption_stops_at_the_complete_proposal(self) -> None:
        result = self.run_fresh_agent(
            f"Use $adopt-standards to begin initial adoption of {self.repository} "
            "at exact release 6.0.0 for owner/example. The boundary title is "
            "example, this is an unsupported Elixir repository, canonical "
            "validation is the literal executable true with no arguments, and "
            "the repository deliberately declares no ruleset. Follow repository "
            "guidance and stop at any required confirmation boundary."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            (self.repository / ".repository-standards.json").exists()
        )
        self.assertFalse((self.repository / ".agents/standard-skills.json").exists())
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), self.original_head)
        final = self.final_message()
        self.assertIn("initial-adoption proposal", final.lower())
        self.assertIn("exact release", final.lower())
        self.assertIn("6.0.0", final)
        self.assertRegex(final, r"Adopt initial standards proposal [0-9a-f]{16}")

    def test_only_genuinely_unresolved_applicability_is_requested(self) -> None:
        result = self.run_fresh_agent(
            f"Use $adopt-standards to begin initial adoption of {self.repository} "
            "at exact release 6.0.0 for owner/example. The boundary title is "
            "example, canonical validation is the literal executable true with "
            "no arguments, and the repository deliberately declares no ruleset."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            (self.repository / ".repository-standards.json").exists()
        )
        final = self.final_message().lower()
        self.assertTrue("ecosystem" in final or "applicability" in final)
        for settled in ("validation", "github", "title", "ruleset"):
            self.assertNotIn(f"what is the {settled}", final)

    def test_exact_confirmation_resumes_only_the_current_initial_proposal(
        self,
    ) -> None:
        proposed = self.run_fresh_agent(
            f"Use $adopt-standards to begin initial adoption of {self.repository} "
            "at exact release 6.0.0 for owner/example. The boundary title is "
            "example, this is an unsupported Elixir repository, canonical "
            "validation is the literal executable true with no arguments, and "
            "the repository deliberately declares no ruleset. Stop at the "
            "confirmation boundary."
        )
        self.assertEqual(proposed.returncode, 0, proposed.stderr)
        match = re.search(
            r"Adopt initial standards proposal [0-9a-f]{16}",
            self.final_message(),
        )
        self.assertIsNotNone(match, self.final_message())
        confirmation = match.group(0)

        confirmed = self.run_fresh_agent(
            "I reviewed the current complete proposal. Confirm it exactly with: "
            f"{confirmation}. Continue the same initial adoption of "
            f"{self.repository} with every previously settled argument and report "
            "its lifecycle boundary accurately."
        )

        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        self.assertTrue(
            (self.repository / ".repository-standards.json").is_file()
        )
        self.assertTrue((self.repository / ".agents/standard-skills.json").is_file())
        self.assertTrue(
            (self.repository / ".claude/skills/adopt-standards/SKILL.md").is_file()
        )
        self.assertEqual(
            (self.repository / "product.txt").read_text(encoding="utf-8"),
            "repository-owned product content\n",
        )
        self.assertNotEqual(
            self.git("rev-parse", "HEAD").stdout.strip(), self.original_head
        )
        self.assertEqual(self.git("status", "--porcelain=v1").stdout, "")
        manifest = json.loads(
            (self.repository / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["standards-release"], "6.0.0")
        self.assertEqual(
            manifest["canonical-validation"],
            {"executable": "true", "arguments": [], "working-directory": "."},
        )
        final = self.final_message().lower()
        self.assertIn("validated adoption commit", final)
        self.assertIn("github delivery", final)
        self.assertIn("separate", final)


if __name__ == "__main__":
    unittest.main()
