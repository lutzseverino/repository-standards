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
    def test_valid_human_pull_request_passes(self) -> None:
        self.assertEqual(
            POLICY.validate(
                "ci/42-align-validation-gate",
                "ci(checks): align validation gate",
                """Closes #42

## Summary

Complete the gate.

## Motivation

Keep local and CI validation aligned.

## Impact

None.

## Validation

- [x] `canonical check command`
""",
                "maintainer",
            ),
            [],
        )

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
        self.assertEqual(len(errors), 7)
        self.assertIn(
            "branch must match <type>/<issue-number>-<short-kebab-slug> with an allowed type",
            errors,
        )
        self.assertIn("pull-request title must be a Conventional Commit subject", errors)
        self.assertIn(
            "pull-request body must contain a line in the form: Closes #123", errors
        )
        for heading in POLICY.HEADINGS:
            self.assertIn(f"pull-request body is missing: ## {heading}", errors)


if __name__ == "__main__":
    unittest.main()
