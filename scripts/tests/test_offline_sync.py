from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.offline_sync import (  # noqa: E402
    apply_synchronization_plan,
    plan_synchronization,
    render_synchronization_preview,
)
from lib.repository_contract import resolve_repository_contract  # noqa: E402
from lib.standards import sync_main  # noqa: E402


class OfflineSynchronizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.standards_root = Path(__file__).resolve().parents[2]

    def create_repository(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        manifest = {
            "standards-version": 5,
            "standards-release": (self.standards_root / "VERSION").read_text(
                encoding="utf-8"
            ).strip(),
            "profiles": ["common", "documentation"],
            "boundaries": [
                {"path": ".", "type": "repository", "title": "Example"}
            ],
            "dependency-updates": [
                {
                    "ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": "weekly",
                }
            ],
            "github": {
                "repository": "owner/example",
                "default-branch": "main",
                "settings": {
                    "delete-branch-on-merge": True,
                    "allow-squash-merge": True,
                    "allow-merge-commit": False,
                    "allow-rebase-merge": False,
                },
                "ruleset": None,
            },
            "variables": {},
            "local-fragments": {},
            "repository-owned": ["README.md"],
        }
        (repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return temporary, repository

    def resolve(self, repository: Path, *, retain_plan_blockers: bool = False):
        return resolve_repository_contract(
            repository,
            standards_root=self.standards_root,
            retain_plan_blockers=retain_plan_blockers,
        )

    def test_preview_describes_creations_updates_preservations_and_removals(self) -> None:
        temporary, repository = self.create_repository()
        self.addCleanup(temporary.cleanup)

        initial = plan_synchronization(self.resolve(repository))
        applied = apply_synchronization_plan(initial)
        self.assertTrue(applied.succeeded)

        editorconfig = repository / ".editorconfig"
        editorconfig.write_text("outdated\n", encoding="utf-8")
        (repository / ".gitattributes").unlink()
        retired = repository / ".github/pull_request_template.md"
        retired.parent.mkdir(parents=True, exist_ok=True)
        retired.write_text("retired\n", encoding="utf-8")

        plan = plan_synchronization(self.resolve(repository))
        preview = render_synchronization_preview(plan)

        self.assertIn("UPDATE   .editorconfig\n", preview)
        self.assertIn("CREATE   .gitattributes\n", preview)
        self.assertIn("PRESERVE AGENTS.md\n", preview)
        self.assertIn("DELETE   .github/pull_request_template.md\n", preview)

    def test_all_deterministic_filesystem_blockers_prevent_every_mutation(self) -> None:
        temporary, repository = self.create_repository()
        self.addCleanup(temporary.cleanup)
        manifest_path = repository / ".repository-standards.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repository-owned"].append(".gitattributes")
        manifest["local-fragments"] = {
            ".gitignore": ["missing/local-fragment"]
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main", str(repository)],
            check=True,
        )
        (repository / ".gitignore").write_text(
            ".github/pull_request_template.md\n", encoding="utf-8"
        )
        ignored_absence = repository / ".github/pull_request_template.md"
        ignored_absence.parent.mkdir(parents=True)
        ignored_absence.write_text("ignored retired policy\n", encoding="utf-8")
        (repository / ".editorconfig").mkdir()
        (repository / ".agents").symlink_to(
            repository / "linked-agents", target_is_directory=True
        )
        blocked_absence = repository / ".github/workflows/pr-policy.yml"
        blocked_absence.mkdir(parents=True)

        plan = plan_synchronization(
            self.resolve(repository, retain_plan_blockers=True)
        )

        self.assertGreaterEqual(len(plan.blockers), 3)
        diagnostics = "\n".join(blocker.message for blocker in plan.blockers)
        self.assertIn("not a regular file", diagnostics)
        self.assertIn("symlink", diagnostics)
        self.assertIn("managed absence", diagnostics)
        self.assertIn("ignored managed absence", diagnostics)
        self.assertIn("repository-owned pattern", diagnostics)
        self.assertIn("local fragment not found", diagnostics)

        output = StringIO()
        errors = StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            exit_code = sync_main(["--write", str(repository)])

        self.assertEqual(exit_code, 2)
        self.assertFalse((repository / ".github/dependabot.yml").exists())
        self.assertFalse((repository / ".gitattributes").exists())
        self.assertTrue((repository / ".editorconfig").is_dir())
        self.assertTrue(ignored_absence.is_file())
        preview = output.getvalue()
        self.assertIn("BLOCKED", preview)
        self.assertIn("CREATE   .gitattributes", preview)
        self.assertIn("UPDATE   .gitignore", preview)
        self.assertIn("DELETE   .github/pull_request_template.md", preview)

    def test_application_failure_reports_completed_failed_and_remaining_work(self) -> None:
        temporary, repository = self.create_repository()
        self.addCleanup(temporary.cleanup)
        plan = plan_synchronization(self.resolve(repository))
        changing = plan.changes
        self.assertGreaterEqual(len(changing), 3)

        from lib import offline_sync

        original_apply = offline_sync._apply_operation
        calls = 0

        def fail_second(target_repository: Path, operation) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected filesystem failure")
            original_apply(target_repository, operation)

        with patch("lib.offline_sync._apply_operation", side_effect=fail_second):
            report = apply_synchronization_plan(plan)

        self.assertFalse(report.succeeded)
        self.assertEqual(report.completed, (changing[0].target,))
        self.assertEqual(report.failed.target, changing[1].target)
        self.assertIn("injected filesystem failure", report.failed.message)
        self.assertEqual(
            report.remaining,
            tuple(operation.target for operation in changing[2:]),
        )
        self.assertTrue((repository / changing[0].target).is_file())
        self.assertFalse((repository / changing[1].target).exists())


if __name__ == "__main__":
    unittest.main()
