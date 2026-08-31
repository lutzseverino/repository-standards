from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_required_ci_fetches_the_immutable_migration_tag(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("fetch-depth: 0", workflow)

    def test_canonical_validation_checks_the_changelog_unconditionally(self) -> None:
        canonical_check = (ROOT / "scripts/validate").read_text(encoding="utf-8")

        self.assertIn("scripts/changelog validate", canonical_check)
        self.assertIn("scripts/standards check --scope content --json", canonical_check)

    def test_supported_platform_acceptance_is_exercised_without_native_windows(
        self,
    ) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(
            encoding="utf-8"
        )
        acceptance = (ROOT / "docs/consumer-acceptance.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("runs-on: ubuntu-24.04", workflow)
        self.assertIn("runs-on: macos-15", workflow)
        self.assertIn("scripts/tests/test_bootstrap_creation.py", workflow)
        self.assertNotIn("windows-", workflow.casefold())
        for platform in ("Linux", "macOS", "WSL", "Native Windows"):
            self.assertIn(platform, acceptance)

    def test_scheduled_assessment_keeps_demonstration_evidence_observable(
        self,
    ) -> None:
        workflow = (ROOT / ".github/workflows/standards-check.yml").read_text(
            encoding="utf-8"
        )
        acceptance = (ROOT / "docs/consumer-acceptance.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("lutzseverino/repository-standards-demo", workflow)
        self.assertIn("GH_TOKEN: ${{ secrets.STANDARDS_CHECK_TOKEN }}", workflow)
        self.assertNotIn("GH_TOKEN: ${{ github.token }}", workflow)
        self.assertIn(
            "python3 ../adopted-standards/profiles/common/files/.github/"
            + "scripts/"
            + "check-workflows.py",
            workflow,
        )
        self.assertIn(
            "`STANDARDS_CHECK_TOKEN` Actions secret",
            (ROOT / "standards/maintenance-and-rollout.md").read_text(
                encoding="utf-8"
            ),
        )
        self.assertIn("deterministic consumer journeys remain required", acceptance)

    def test_stable_tag_publishes_matching_changelog_notes(self) -> None:
        workflow = (ROOT / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            workflow,
            re.compile(
                r'(?m)^    tags:\n      - "v\[0-9\]\+\.\[0-9\]\+\.\[0-9\]\+"$'
            ),
        )
        self.assertRegex(workflow, re.compile(r"(?m)^  contents: write$"))
        self.assertRegex(workflow, re.compile(r"(?m)^  checks: read$"))
        self.assertIn("jobs:\n  release:", workflow)
        self.assertNotRegex(workflow, re.compile(r"(?m)^    if:"))

        self.assertRegex(
            workflow,
            re.compile(
                r'(?m)^        run: scripts/publish-release "\$RELEASE_TAG"$'
            ),
        )
        self.assertNotIn("gh release create", workflow)


if __name__ == "__main__":
    unittest.main()
