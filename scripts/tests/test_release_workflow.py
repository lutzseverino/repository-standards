from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_canonical_validation_checks_the_changelog_unconditionally(self) -> None:
        canonical_check = (ROOT / "scripts/validate").read_text(encoding="utf-8")

        self.assertIn("scripts/changelog validate", canonical_check)
        self.assertIn("scripts/standards check --scope content --json", canonical_check)
        self.assertNotIn("scripts/audit", canonical_check)

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
