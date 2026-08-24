from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DISTRIBUTED_SKILLS = (
    ROOT / "profiles/repository-lifecycle-skills/files/.agents/skills"
)
ROOT_SKILLS = ROOT / ".agents/skills"


class LifecycleGoalSurfaceTests(unittest.TestCase):
    def test_standards_help_exposes_every_repository_goal(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts/standards"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        for goal in ("check", "repair", "create", "publish", "adopt", "deliver"):
            self.assertIn(goal, result.stdout)

    def test_goal_oriented_lifecycle_skills_have_identical_copies(self) -> None:
        names = (
            "create-repository",
            "publish-repository",
            "adopt-standards",
            "deliver-change",
        )

        for name in names:
            distributed = DISTRIBUTED_SKILLS / name
            root = ROOT_SKILLS / name
            self.assertTrue(distributed.is_dir(), name)
            self.assertTrue(root.is_dir(), name)
            distributed_files = sorted(
                path.relative_to(distributed) for path in distributed.rglob("*") if path.is_file()
            )
            root_files = sorted(
                path.relative_to(root) for path in root.rglob("*") if path.is_file()
            )
            self.assertEqual(root_files, distributed_files, name)
            for relative in distributed_files:
                self.assertEqual(
                    (root / relative).read_bytes(),
                    (distributed / relative).read_bytes(),
                    f"{name}/{relative}",
                )

    def test_lifecycle_profile_distributes_only_the_inventory_skills(self) -> None:
        profile = json.loads(
            (
                ROOT / "profiles/repository-lifecycle-skills/profile.json"
            ).read_text(encoding="utf-8")
        )
        inventory = json.loads(
            (
                DISTRIBUTED_SKILLS.parent / "repository-lifecycle-skills.json"
            ).read_text(encoding="utf-8")
        )

        distributed = sorted(
            entry["target"].removeprefix(".agents/skills/")
            for entry in profile["files"]
            if entry["target"].startswith(".agents/skills/")
        )
        self.assertEqual(distributed, inventory["bundle"]["skills"])

    def test_publication_skill_hides_proposal_persistence(self) -> None:
        skill = (
            DISTRIBUTED_SKILLS / "publish-repository/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("lifecycle proposal", skill)
        self.assertNotIn("--plan-file", skill)
        self.assertNotIn("Plan mode", skill)
        self.assertNotIn("Publish mode", skill)

    def test_canonical_change_validation_is_named_validate(self) -> None:
        validation = ROOT / "scripts/validate"
        workflows = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / ".github/workflows").glob("*.yml")
        )

        self.assertTrue(validation.is_file())
        self.assertIn("scripts/validate", workflows)

    def test_delivery_goal_preserves_the_agent_confirmation_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch=main"],
                cwd=repository,
                check=True,
            )
            before = subprocess.run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"],
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout

            result = subprocess.run(
                [str(ROOT / "scripts/standards"), "deliver", str(repository)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("deliver-change", result.stdout)
            self.assertIn("exact lifecycle proposal", result.stdout)
            self.assertIn("No mutation was performed", result.stdout)
            after = subprocess.run(
                ["git", "status", "--porcelain=v1", "--untracked-files=all"],
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
