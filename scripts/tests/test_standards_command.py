from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.github_reconciliation import GitHubAdapter, GitHubSnapshot
from lib.repository_assessment_cli import standards_main
from lib.repository_content import StandardsError


class ConformanceGitHub(GitHubAdapter):
    def __init__(self, *, drift: bool = False, unavailable: bool = False) -> None:
        self.drift = drift
        self.unavailable = unavailable
        self.applied: list[str] = []

    def observe(self, contract, *, lifecycle=None):
        if self.unavailable:
            raise StandardsError("GitHub evidence is unavailable")
        github = contract.github.as_mapping()
        settings = github["settings"]
        features = github["features"]
        return GitHubSnapshot(
            repository={
                "full_name": github["repository"],
                "default_branch": github["default-branch"],
                "delete_branch_on_merge": (
                    not settings["delete-branch-on-merge"]
                    if self.drift
                    else settings["delete-branch-on-merge"]
                ),
                "allow_squash_merge": settings["allow-squash-merge"],
                "allow_merge_commit": settings["allow-merge-commit"],
                "allow_rebase_merge": settings["allow-rebase-merge"],
                "squash_merge_commit_title": settings[
                    "squash-merge-commit-title"
                ],
                "squash_merge_commit_message": settings[
                    "squash-merge-commit-message"
                ],
                "has_issues": features["issues"],
                "has_projects": features["projects"],
                "has_wiki": features["wiki"],
                "permissions": {"admin": True, "push": True},
            },
            branches=({"name": github["default-branch"]},),
            label_names=frozenset(contract.required_labels),
            rulesets=(),
        )

    def apply(self, operation):
        self.applied.append(operation.description)
        self.drift = False


class StandardsCommandTests(unittest.TestCase):
    def run_command(self, *arguments: str, adapter: GitHubAdapter):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = standards_main(list(arguments), github_adapter=adapter)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_check_maps_the_three_conclusions_to_stable_exit_statuses(self) -> None:
        complete = self.run_command(
            "check", str(ROOT), adapter=ConformanceGitHub()
        )
        incomplete = self.run_command(
            "check", str(ROOT), adapter=ConformanceGitHub(drift=True)
        )
        unverified = self.run_command(
            "check", str(ROOT), adapter=ConformanceGitHub(unavailable=True)
        )

        self.assertEqual(complete[0], 0, complete)
        self.assertIn("Conclusion: standards-complete", complete[1])
        self.assertRegex(
            complete[1],
            r"Counts: \d+ satisfied, 0 differences, 0 evidence gaps, "
            r"0 automatic corrections, 0 required maintainer actions, "
            r"\d+ preservation items",
        )
        self.assertNotIn("Satisfied requirements:", complete[1])
        self.assertNotIn("Preservation evidence:", complete[1])
        self.assertEqual(incomplete[0], 1, incomplete)
        self.assertIn("Conclusion: not-standards-complete", incomplete[1])
        self.assertIn("Differences:", incomplete[1])
        self.assertIn("repository settings", incomplete[1])
        self.assertEqual(unverified[0], 2, unverified)
        self.assertIn("Conclusion: unverified", unverified[1])
        self.assertIn("Evidence gaps:", unverified[1])
        self.assertIn("GitHub evidence is unavailable", unverified[1])

    def test_verbose_human_output_restores_complete_evidence(self) -> None:
        status, stdout, stderr = self.run_command(
            "check", "--verbose", str(ROOT), adapter=ConformanceGitHub()
        )

        self.assertEqual(status, 0, stderr)
        self.assertIn("Satisfied requirements:", stdout)
        self.assertIn("Preservation evidence:", stdout)
        self.assertIn("[repository-content]", stdout)

    def test_json_remains_complete_and_keeps_the_same_exit_meaning(self) -> None:
        status, stdout, stderr = self.run_command(
            "check", "--json", str(ROOT), adapter=ConformanceGitHub()
        )

        self.assertEqual(status, 0, stderr)
        assessment = json.loads(stdout)
        self.assertEqual(
            set(assessment),
            {
                "conclusion",
                "scope",
                "lifecycle",
                "satisfied-requirements",
                "differences",
                "evidence-gaps",
                "automatic-corrections",
                "required-maintainer-work",
                "preservation-evidence",
                "application",
            },
        )
        self.assertTrue(assessment["satisfied-requirements"])
        self.assertTrue(assessment["preservation-evidence"])
        self.assertIn("differences", assessment)
        self.assertIn("evidence-gaps", assessment)

    def test_create_keeps_contract_construction_behind_the_selected_executable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "creation.json"
            input_path.write_text(
                json.dumps(
                    {
                        "standards-release": (ROOT / "VERSION")
                        .read_text(encoding="utf-8")
                        .strip(),
                        "repository": "owner/example",
                        "title": "Example",
                        "canonical-validation": {
                            "executable": "scripts/validate",
                            "arguments": [],
                            "working-directory": ".",
                        },
                        "facts": {
                            "ecosystem": "none",
                            "package-manager": "none",
                            "project-kind": "repository",
                            "framework": "none",
                        },
                    }
                ),
                encoding="utf-8",
            )

            status, stdout, stderr = self.run_command(
                "create",
                "--contract-input",
                str(input_path),
                adapter=ConformanceGitHub(),
            )

        self.assertEqual(status, 0, stderr)
        contract = json.loads(stdout)
        self.assertEqual(contract["github"]["repository"], "owner/example")
        self.assertEqual(contract["profiles"], ["common", "documentation"])
        self.assertEqual(
            contract["canonical-validation"]["executable"], "scripts/validate"
        )

    def test_check_is_read_only_and_restricted_check_is_unverified(self) -> None:
        adapter = ConformanceGitHub(drift=True)

        status, stdout, stderr = self.run_command(
            "check", "--scope", "content", str(ROOT), adapter=adapter
        )

        self.assertEqual(status, 2, (stdout, stderr))
        self.assertEqual(adapter.applied, [])
        self.assertIn("content-only assessment", stdout)

    def test_repair_renders_the_actionable_preview_before_github_mutation(self) -> None:
        adapter = ConformanceGitHub(drift=True)
        stdout = io.StringIO()
        observed_before_apply: list[str] = []
        original_apply = adapter.apply

        def apply(operation):
            observed_before_apply.append(stdout.getvalue())
            original_apply(operation)

        adapter.apply = apply
        with redirect_stdout(stdout):
            status = standards_main(
                ["repair", str(ROOT)], github_adapter=adapter
            )

        self.assertEqual(status, 0, stdout.getvalue())
        self.assertEqual(adapter.applied, ["UPDATE   repository settings"])
        self.assertIn(
            "UPDATE   repository settings", observed_before_apply[0]
        )
        self.assertIn("Counts:", observed_before_apply[0])
        self.assertNotIn("Satisfied requirements:", observed_before_apply[0])
        self.assertIn("Conclusion: standards-complete", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
