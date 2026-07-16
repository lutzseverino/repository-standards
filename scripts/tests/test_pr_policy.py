from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "profiles/common/files/.github/scripts/check-pr-policy.py"
)
SPEC = importlib.util.spec_from_file_location("check_pr_policy", POLICY_PATH)
assert SPEC is not None and SPEC.loader is not None
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class PullRequestPolicyTests(unittest.TestCase):
    def test_dependabot_author_is_exempt_after_maintainer_updates_branch(self) -> None:
        self.assertEqual(
            POLICY.validate(
                "dependabot/github_actions/example-2.0.0",
                "chore: bump example from 1.0.0 to 2.0.0",
                "Dependabot-generated body",
                "dependabot[bot]",
            ),
            [],
        )

    def test_human_pull_request_must_follow_the_contract(self) -> None:
        errors = POLICY.validate("feature/example", "Example", "", "maintainer")
        self.assertGreaterEqual(len(errors), 3)


if __name__ == "__main__":
    unittest.main()
