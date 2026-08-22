from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills/first-publication"
)
RUNNER = SKILL_ROOT / "scripts/publish"


class FirstPublicationSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.repository = self.directory / "repository"
        self.repository.mkdir()
        (self.repository / ".repository-standards.json").write_text(
            json.dumps({"standards-release": "4.0.0"}) + "\n",
            encoding="utf-8",
        )
        self.release = self.directory / "release"
        scripts = self.release / "scripts"
        scripts.mkdir(parents=True)
        tool = scripts / "first-publication"
        tool.write_text(
            """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

arguments = sys.argv[1:]
with open(os.environ["FAKE_PUBLICATION_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(arguments) + "\\n")
if arguments[0] == "plan":
    plan_path = pathlib.Path(arguments[arguments.index("--plan-file") + 1])
    plan_path.write_text(json.dumps({"repository": arguments[1]}) + "\\n", encoding="utf-8")
""",
            encoding="utf-8",
        )
        tool.chmod(0o755)
        (self.release / "VERSION").write_text("4.0.0\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main"],
            cwd=self.release,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Skill Tester"],
            cwd=self.release,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "skill@example.com"],
            cwd=self.release,
            check=True,
        )
        subprocess.run(["git", "add", "--all"], cwd=self.release, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--message", "release"],
            cwd=self.release,
            check=True,
        )
        subprocess.run(
            ["git", "tag", "--no-sign", "v4.0.0"],
            cwd=self.release,
            check=True,
        )
        self.plan_file = self.directory / "plan.json"
        self.log = self.directory / "publication.log"

    def run_runner(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_CHECKOUT": str(self.release),
                "FAKE_PUBLICATION_LOG": str(self.log),
            }
        )
        return subprocess.run(
            ["python3", str(RUNNER), *arguments],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_skill_preserves_plan_confirmation_publish_as_separate_actions(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Stop and ask the human for explicit confirmation", skill)
        self.assertIn("Do not enter Publish", skill)
        self.assertIn("execution adapter", skill)
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        self.plan_file.symlink_to(victim)

        planned = self.run_runner(
            "plan",
            "--plan-file",
            str(self.plan_file),
            str(self.repository),
        )
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertTrue(self.plan_file.is_file())

        unconfirmed = self.run_runner(
            "publish", "--plan-file", str(self.plan_file)
        )
        self.assertEqual(unconfirmed.returncode, 2)
        self.assertIn("--confirm", unconfirmed.stderr)

        confirmed = self.run_runner(
            "publish",
            "--plan-file",
            str(self.plan_file),
            "--confirm",
            "Publish owner/example from plan test",
        )
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        operations = [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(operations[0][0], "plan")
        self.assertEqual(operations[1][0], "publish")
        self.assertIn("--confirm", operations[1])
        for operation in operations:
            plan_path = operation[operation.index("--plan-file") + 1]
            self.assertEqual(plan_path, str(self.plan_file))


if __name__ == "__main__":
    unittest.main()
