from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StandardsAuditWorkflowTests(unittest.TestCase):
    def test_unreleased_source_uses_current_tooling_while_targets_use_adopted_tooling(
        self,
    ) -> None:
        workflow = (ROOT / ".github/workflows/standards-audit.yml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            workflow,
            re.compile(
                r"(?m)^      - name: Audit repository standards source\n"
                r"        if: matrix\.repository == github\.repository\n"
                r"        run: scripts/audit target\n"
            ),
        )
        self.assertRegex(
            workflow,
            re.compile(
                r"(?m)^      - name: Audit managed standards\n"
                r"        if: matrix\.repository != github\.repository\n"
                r"        run: adopted-standards/scripts/audit target\n"
            ),
        )
        self.assertRegex(
            workflow,
            re.compile(
                r"(?m)^      - name: Audit source live GitHub settings\n"
                r"        if: matrix\.repository == github\.repository\n"
                r"        env:\n"
                r"          GH_TOKEN: \$\{\{ github\.token \}\}\n"
                r"        run: scripts/audit-live target\n"
            ),
        )

    def test_live_audit_receives_the_github_actions_token(self) -> None:
        workflow = (ROOT / ".github/workflows/standards-audit.yml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            workflow,
            re.compile(
                r"(?m)^      - name: Audit live GitHub settings\n"
                r"        if: matrix\.repository != github\.repository && "
                r"\(steps\.manifest\.outputs\.version == '4' \|\| "
                r"steps\.manifest\.outputs\.version == '5'\)\n"
                r"        env:\n"
                r"          GH_TOKEN: \$\{\{ github\.token \}\}\n"
            ),
        )

    def test_live_audit_runs_from_the_adopted_standards_release(self) -> None:
        workflow = (ROOT / ".github/workflows/standards-audit.yml").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            workflow,
            re.compile(
                r"(?m)^      - name: Audit live GitHub settings\n"
                r"(?:        .*\n)*"
                r"        run: adopted-standards/scripts/audit-live target\n"
            ),
        )
