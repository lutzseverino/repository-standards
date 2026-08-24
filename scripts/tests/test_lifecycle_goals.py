from __future__ import annotations

import json
import os
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
            if entry["mode"] == "tree"
            and entry["target"].startswith(".agents/skills/")
        )
        self.assertEqual(distributed, inventory["bundle"]["skills"])

    def test_distributed_skills_invoke_bundled_adapters(self) -> None:
        for name in (
            "create-repository",
            "publish-repository",
            "adopt-standards",
            "deliver-change",
        ):
            skill = (DISTRIBUTED_SKILLS / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("scripts/standards", skill, name)

        for name, runner in (
            ("create-repository", "create"),
            ("publish-repository", "publish"),
            ("adopt-standards", "adopt"),
        ):
            skill = (DISTRIBUTED_SKILLS / name / "SKILL.md").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                f"python3 .agents/skills/{name}/scripts/{runner}",
                skill,
            )

        self.assertTrue(
            (
                DISTRIBUTED_SKILLS
                / "publish-repository/scripts/publish"
            ).is_file()
        )

    def test_publication_adapter_invokes_the_selected_release_goal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release = root / "release"
            scripts = release / "scripts"
            scripts.mkdir(parents=True)
            (release / "VERSION").write_text("1.2.3\n", encoding="utf-8")
            log = root / "publication.log"
            standards = scripts / "standards"
            standards.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$FAKE_PUBLICATION_LOG\"\n",
                encoding="utf-8",
            )
            standards.chmod(0o755)
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch=main"],
                cwd=release,
                check=True,
            )
            subprocess.run(["git", "add", "."], cwd=release, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test User",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "--quiet",
                    "--message",
                    "release",
                ],
                cwd=release,
                check=True,
            )
            subprocess.run(
                ["git", "tag", "--no-sign", "v1.2.3"],
                cwd=release,
                check=True,
            )
            repository = root / "repository"
            repository.mkdir()
            repository = repository.resolve()
            (repository / ".repository-standards.json").write_text(
                '{"standards-release":"1.2.3"}\n', encoding="utf-8"
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "FAKE_PUBLICATION_LOG": str(log),
                    "REPOSITORY_STANDARDS_CHECKOUT": str(release),
                }
            )
            runner = (
                DISTRIBUTED_SKILLS / "publish-repository/scripts/publish"
            )

            preview = subprocess.run(
                [str(runner), str(repository)],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            confirmed = subprocess.run(
                [str(runner), str(repository), "--confirm", "exact phrase"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
            self.assertEqual(
                log.read_text(encoding="utf-8").splitlines(),
                [
                    f"publish {repository}",
                    f"publish {repository} --confirm exact phrase",
                ],
            )

    def test_publication_skill_hides_proposal_persistence(self) -> None:
        skill = (
            DISTRIBUTED_SKILLS / "publish-repository/SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertIn("lifecycle proposal", skill)

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
