from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("claude"),
    "set RUN_FRESH_AGENT_TESTS=1 with Claude authentication to run fresh-agent tests",
)
class ClaudeAdapterFreshAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name).resolve() / "repository"
        canonical = self.repository / ".agents/skills/create-repository"
        adapter = self.repository / ".claude/skills/create-repository"
        canonical.mkdir(parents=True)
        adapter.mkdir(parents=True)
        shutil.copy2(
            ROOT / ".agents/skills/create-repository/SKILL.md",
            canonical / "SKILL.md",
        )
        shutil.copy2(
            ROOT
            / "profiles/common/files/.claude/skills/create-repository/SKILL.md",
            adapter / "SKILL.md",
        )
        (canonical / "scripts").mkdir()
        runner = canonical / "scripts/create"
        runner.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import sys
                from pathlib import Path

                Path(".claude-adapter-invoked").write_text(
                    "\\n".join(sys.argv[1:]), encoding="utf-8"
                )
                print("Prepared creation baseline; first publication required.")
                """
            ),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        (self.repository / "standards").mkdir()
        shutil.copy2(
            ROOT / "standards/repository-lifecycle.md",
            self.repository / "standards/repository-lifecycle.md",
        )
        shutil.copy2(
            ROOT / "profiles/common/files/AGENTS.md",
            self.repository / "AGENTS.md",
        )
        shutil.copy2(
            ROOT / "profiles/common/files/CLAUDE.md",
            self.repository / "CLAUDE.md",
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "init", "-q", "-b", "main"],
            check=True,
        )

    def test_claude_project_adapter_interprets_the_canonical_agent_skill(
        self,
    ) -> None:
        destination = self.repository.parent / "widget"
        result = subprocess.run(
            [
                "claude",
                "--print",
                (
                    "Use $create-repository to create private owner/widget at "
                    f"{destination}. Purpose: 'Exercise the Claude adapter.' "
                    "License: MIT. It is an unsupported Elixir repository, its "
                    "project kind is repository, and canonical validation is the "
                    "literal executable true with no arguments."
                ),
                "--no-session-persistence",
                "--setting-sources",
                "project",
                "--permission-mode",
                "bypassPermissions",
                "--tools",
                "Bash,Read",
            ],
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        invocation = (self.repository / ".claude-adapter-invoked").read_text(
            encoding="utf-8"
        )
        self.assertIn("--name\nwidget", invocation)
        self.assertIn("--validation-executable\ntrue", invocation)
        self.assertIn("ecosystem=elixir", invocation.lower())
        self.assertIn("first publication", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
