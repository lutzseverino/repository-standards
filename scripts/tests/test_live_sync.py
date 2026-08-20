from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SYNC_LIVE = ROOT / "scripts/sync-live"
AUDIT_LIVE = ROOT / "scripts/audit-live"


class LiveSyncCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        self.repository.mkdir()
        self.state_path = self.directory / "github.json"
        self.gh_path = self.directory / "gh"
        self.gh_path.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                from urllib.parse import unquote

                state_path = os.environ["FAKE_GITHUB_STATE"]
                with open(state_path, encoding="utf-8") as handle:
                    state = json.load(handle)
                args = sys.argv[1:]
                method = "GET"
                if "--method" in args:
                    index = args.index("--method")
                    method = args[index + 1]
                    del args[index:index + 2]
                endpoint = args[args.index("api") + 1]
                payload = json.load(sys.stdin) if method != "GET" else None
                if method == "GET" and state.get("fail_on_read"):
                    print(state["failure_message"], file=sys.stderr)
                    raise SystemExit(1)
                if method != "GET":
                    write_number = state.get("write_count", 0) + 1
                    if write_number == state.get("fail_on_write"):
                        print(
                            state.get(
                                "failure_message",
                                "gh: Resource not accessible by personal access token (HTTP 403)",
                            ),
                            file=sys.stderr,
                        )
                        raise SystemExit(1)
                    state["write_count"] = write_number
                if method == "GET" and endpoint == "repos/owner/example":
                    response = state["repository"]
                elif method == "GET" and endpoint.startswith("repos/owner/example/labels?"):
                    response = state["labels"]
                elif method == "GET" and endpoint.startswith("repos/owner/example/rulesets?"):
                    response = [
                        {"id": item["id"], "name": item["name"]}
                        for item in state["rulesets"]
                    ]
                elif method == "GET" and endpoint.startswith("repos/owner/example/rulesets/"):
                    ruleset_id = int(endpoint.rsplit("/", 1)[1])
                    response = next(
                        item for item in state["rulesets"] if item["id"] == ruleset_id
                    )
                elif method == "PATCH" and endpoint == "repos/owner/example":
                    state["repository"].update(payload)
                    response = state["repository"]
                elif method == "POST" and endpoint == "repos/owner/example/labels":
                    state["labels"].append(payload)
                    response = payload
                elif method == "PATCH" and endpoint.startswith("repos/owner/example/labels/"):
                    label_name = unquote(endpoint.rsplit("/", 1)[1])
                    label = next(
                        item
                        for item in state["labels"]
                        if item["name"].casefold() == label_name.casefold()
                    )
                    label["name"] = payload["new_name"]
                    response = label
                elif method == "POST" and endpoint == "repos/owner/example/rulesets":
                    response = {"id": 100 + len(state["rulesets"]), **payload}
                    state["rulesets"].append(response)
                elif method == "PUT" and endpoint.startswith("repos/owner/example/rulesets/"):
                    ruleset_id = int(endpoint.rsplit("/", 1)[1])
                    response = {"id": ruleset_id, **payload}
                    state["rulesets"] = [
                        response if item["id"] == ruleset_id else item
                        for item in state["rulesets"]
                    ]
                else:
                    raise SystemExit(f"unexpected request: {method} {endpoint}")
                with open(state_path, "w", encoding="utf-8") as handle:
                    json.dump(state, handle)
                json.dump(response, sys.stdout)
                """
            ),
            encoding="utf-8",
        )
        self.gh_path.chmod(0o755)
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(self.manifest()), encoding="utf-8"
        )

    def manifest(self) -> dict[str, Any]:
        return {
            "standards-version": 5,
            "standards-release": (ROOT / "VERSION").read_text(
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
                "ruleset": {
                    "name": "Protect main",
                    "required-status-checks": ["CI / Required"],
                    "require-current-branch": True,
                    "required-approvals": 0,
                    "allowed-merge-methods": ["squash"],
                    "prevent-deletion": True,
                    "prevent-force-push": True,
                    "allow-bypass-actors": False,
                },
            },
            "variables": {},
            "local-fragments": {},
            "repository-owned": ["README.md"],
        }

    def run_sync_live(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["REPOSITORY_STANDARDS_GH"] = str(self.gh_path)
        environment["FAKE_GITHUB_STATE"] = str(self.state_path)
        return subprocess.run(
            [str(SYNC_LIVE), *arguments, str(self.repository)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def run_audit_live(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["REPOSITORY_STANDARDS_GH"] = str(self.gh_path)
        environment["FAKE_GITHUB_STATE"] = str(self.state_path)
        return subprocess.run(
            [str(AUDIT_LIVE), *arguments, str(self.repository)],
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_prepared_lifecycle_validates_applicable_state_and_reports_publication_pending(
        self,
    ) -> None:
        manifest = self.manifest()
        manifest["github"]["ruleset"] = None
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        required_labels = [
            "bug",
            "enhancement",
            "needs-triage",
            "needs-info",
            "ready-for-agent",
            "ready-for-human",
            "wontfix",
        ]
        state = {
            "repository": {
                "default_branch": None,
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False,
            },
            "labels": [{"name": name} for name in required_labels],
            "rulesets": [],
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        preview = self.run_sync_live("--lifecycle", "prepared")
        audit = self.run_audit_live("--lifecycle", "prepared")

        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("pending first publication", preview.stdout)
        self.assertNotIn("UPDATE", preview.stdout)
        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertIn("pending first publication", audit.stdout)
        self.assertNotIn("conform", audit.stdout)

    def test_manifest_rejects_bypass_actors_before_github_access(self) -> None:
        manifest = self.manifest()
        manifest["github"]["ruleset"]["allow-bypass-actors"] = True
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        result = self.run_sync_live()

        self.assertEqual(result.returncode, 2)
        self.assertIn("does not support bypass actors", result.stderr)
        self.assertIn("set allow-bypass-actors to false", result.stderr)
        self.assertNotIn("FAKE_GITHUB_STATE", result.stderr)

    def test_preview_reports_declared_changes_without_writing(self) -> None:
        extra_ruleset = {
            "id": 8,
            "name": "Repository local",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/dev"], "exclude": []}},
            "bypass_actors": [],
            "rules": [],
        }
        state = {
            "repository": {
                "default_branch": "trunk",
                "delete_branch_on_merge": False,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
            },
            "labels": [
                {"name": "bug"},
                {"name": "repository-specific"},
            ],
            "rulesets": [extra_ruleset],
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.run_sync_live()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("CREATE   label 'enhancement'", result.stdout)
        self.assertIn("UPDATE   repository settings", result.stdout)
        self.assertIn("CREATE   ruleset 'Protect main'", result.stdout)
        self.assertNotIn("repository-specific", result.stdout)
        self.assertNotIn("Repository local", result.stdout)
        self.assertEqual(
            json.loads(self.state_path.read_text(encoding="utf-8")), state
        )

    def test_write_applies_declared_changes_and_an_immediate_rerun_is_a_no_op(
        self,
    ) -> None:
        extra_ruleset = {
            "id": 8,
            "name": "Repository local",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/dev"], "exclude": []}},
            "bypass_actors": [],
            "rules": [],
        }
        state = {
            "repository": {
                "default_branch": "trunk",
                "delete_branch_on_merge": False,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
            },
            "labels": [{"name": "repository-specific"}],
            "rulesets": [extra_ruleset],
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        written = self.run_sync_live("--write")

        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertIn("Applied 10 live operation(s)", written.stdout)
        updated = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertIn("repository-specific", {item["name"] for item in updated["labels"]})
        self.assertEqual(updated["repository"]["default_branch"], "main")
        self.assertTrue(updated["repository"]["delete_branch_on_merge"])
        self.assertEqual(
            {item["name"] for item in updated["rulesets"]},
            {"Repository local", "Protect main"},
        )

        rerun = self.run_sync_live("--write")

        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertIn("Live GitHub contract is current", rerun.stdout)
        self.assertEqual(
            json.loads(self.state_path.read_text(encoding="utf-8")), updated
        )

    def test_partial_failure_reports_completed_and_remaining_operations(self) -> None:
        state = {
            "repository": {
                "default_branch": "trunk",
                "delete_branch_on_merge": False,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
            },
            "labels": [],
            "rulesets": [],
            "fail_on_write": 2,
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.run_sync_live("--write")

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "Completed operations:\n- ESTABLISH default branch 'main'",
            result.stderr,
        )
        self.assertIn("Failed operation:\n- UPDATE   repository settings", result.stderr)
        self.assertIn(
            "Remaining operations:\n- CREATE   label 'bug'", result.stderr
        )
        self.assertIn("- CREATE   ruleset 'Protect main'", result.stderr)
        self.assertIn("gh auth login", result.stderr)
        self.assertIn("Administration (write)", result.stderr)
        updated = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["repository"]["default_branch"], "main")
        self.assertEqual(updated["labels"], [])

        updated.pop("fail_on_write")
        self.state_path.write_text(json.dumps(updated), encoding="utf-8")
        retry = self.run_sync_live("--write")

        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertIn("Applied 9 live operation(s)", retry.stdout)
        rerun = self.run_sync_live("--write")
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertIn("Live GitHub contract is current", rerun.stdout)

    def test_write_updates_only_the_named_ruleset(self) -> None:
        required_labels = [
            "bug",
            "enhancement",
            "needs-triage",
            "needs-info",
            "ready-for-agent",
            "ready-for-human",
            "wontfix",
        ]
        local_ruleset = {
            "id": 8,
            "name": "Repository local",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/dev"], "exclude": []}},
            "bypass_actors": [],
            "rules": [],
        }
        drifted_ruleset = {
            "id": 9,
            "name": "Protect main",
            "target": "branch",
            "enforcement": "disabled",
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "bypass_actors": [],
            "rules": [
                {"type": "required_signatures"},
                {
                    "type": "pull_request",
                    "parameters": {
                        "dismiss_stale_reviews_on_push": True,
                        "require_code_owner_review": True,
                        "require_last_push_approval": True,
                        "required_approving_review_count": 2,
                        "required_review_thread_resolution": True,
                        "allowed_merge_methods": ["merge"],
                    },
                },
            ],
        }
        state = {
            "repository": {
                "default_branch": "main",
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
            },
            "labels": [{"name": name} for name in required_labels],
            "rulesets": [local_ruleset, drifted_ruleset],
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        result = self.run_sync_live("--write")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UPDATE   ruleset 'Protect main'", result.stdout)
        updated = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["rulesets"][0], local_ruleset)
        self.assertEqual(updated["rulesets"][1]["name"], "Protect main")
        self.assertEqual(updated["rulesets"][1]["enforcement"], "active")
        rules = updated["rulesets"][1]["rules"]
        self.assertIn({"type": "required_signatures"}, rules)
        pull_request = next(rule for rule in rules if rule["type"] == "pull_request")
        self.assertTrue(pull_request["parameters"]["require_code_owner_review"])
        self.assertTrue(
            pull_request["parameters"]["required_review_thread_resolution"]
        )
        self.assertEqual(
            pull_request["parameters"]["required_approving_review_count"], 0
        )

    def test_write_renames_required_label_case_collisions_and_reruns_cleanly(
        self,
    ) -> None:
        state = {
            "repository": {
                "default_branch": "main",
                "delete_branch_on_merge": True,
                "allow_squash_merge": True,
                "allow_merge_commit": False,
                "allow_rebase_merge": False,
                "squash_merge_commit_title": "PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False,
            },
            "labels": [
                {"name": name}
                for name in (
                    "Bug",
                    "enhancement",
                    "needs-triage",
                    "needs-info",
                    "ready-for-agent",
                    "ready-for-human",
                    "wontfix",
                    "repository-specific",
                )
            ],
            "rulesets": [],
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        written = self.run_sync_live("--write")

        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertIn("UPDATE   label 'Bug' to 'bug'", written.stdout)
        updated = json.loads(self.state_path.read_text(encoding="utf-8"))
        label_names = {item["name"] for item in updated["labels"]}
        self.assertIn("bug", label_names)
        self.assertIn("repository-specific", label_names)
        rerun = self.run_sync_live("--write")
        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertIn("Live GitHub contract is current", rerun.stdout)

    def test_authentication_failures_include_recovery_guidance(self) -> None:
        messages = (
            "gh: Bad credentials (HTTP 401)",
            "gh: Unauthorized",
            "gh: Not Found (HTTP 404)",
        )
        for message in messages:
            with self.subTest(message=message):
                state = {
                    "repository": {
                        "default_branch": "trunk",
                        "delete_branch_on_merge": False,
                        "allow_squash_merge": True,
                        "allow_merge_commit": False,
                        "allow_rebase_merge": False,
                    },
                    "labels": [],
                    "rulesets": [],
                    "fail_on_write": 1,
                    "failure_message": message,
                }
                self.state_path.write_text(json.dumps(state), encoding="utf-8")

                result = self.run_sync_live("--write")

                self.assertEqual(result.returncode, 2)
                self.assertIn("gh auth login", result.stderr)
                self.assertIn("Issues (write)", result.stderr)
                self.assertIn("Administration (write)", result.stderr)

    def test_observation_authentication_and_permission_failures_include_guidance(
        self,
    ) -> None:
        for message in (
            "gh: Bad credentials (HTTP 401)",
            "gh: Resource not accessible by personal access token (HTTP 403)",
        ):
            with self.subTest(message=message):
                self.state_path.write_text(
                    json.dumps(
                        {
                            "fail_on_read": True,
                            "failure_message": message,
                        }
                    ),
                    encoding="utf-8",
                )

                result = self.run_sync_live()

                self.assertEqual(result.returncode, 2)
                self.assertIn("gh auth login", result.stderr)
                self.assertIn("Issues (read)", result.stderr)
                self.assertIn("Administration (read)", result.stderr)


if __name__ == "__main__":
    unittest.main()
