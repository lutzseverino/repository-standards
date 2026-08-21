from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.first_publication import (
    load_publication_plan,
    plan_first_publication,
    publish_first_publication,
    write_publication_plan,
)
from lib.live_reconciliation import GitHubAdapter
from lib.standards import StandardsError


class FakePublicationGitHub(GitHubAdapter):
    def __init__(self) -> None:
        self.mutations: list[tuple[str, str, dict[str, object]]] = []
        self.repository = {
            "full_name": "owner/example",
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
            "permissions": {"admin": True, "push": True},
        }
        self.labels = {
            "bug",
            "enhancement",
            "needs-triage",
            "needs-info",
            "ready-for-agent",
            "ready-for-human",
            "wontfix",
        }
        self.rulesets: list[dict[str, object]] = []
        self.branches: list[dict[str, object]] = []
        self.pulls: list[dict[str, object]] = []
        self.failure: str | None = None
        self.repository_observations = 0

    def request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, object] | None = None,
    ) -> object:
        if method != "GET":
            if self.failure == "default" and (payload or {}).get("default_branch"):
                raise StandardsError("default branch denied")
            if self.failure == "ruleset" and endpoint.endswith("/rulesets"):
                raise StandardsError("ruleset denied")
            self.mutations.append((method, endpoint, payload or {}))
            if method == "PATCH" and endpoint == "repos/owner/example":
                self.repository.update(payload or {})
                if (payload or {}).get("default_branch") == "main":
                    self.branches = [{"name": "main"}]
                return dict(self.repository)
            if method == "POST" and endpoint == "repos/owner/example/rulesets":
                ruleset = {
                    "id": 1,
                    "source_type": "Repository",
                    "source": "owner/example",
                    **(payload or {}),
                }
                self.rulesets.append(ruleset)
                if self.failure in {
                    "ruleset-response-lost",
                    "ruleset-response-and-observation-lost",
                }:
                    raise StandardsError("connection lost after ruleset creation")
                return dict(ruleset)
            return {}
        if endpoint == "repos/owner/example":
            self.repository_observations += 1
            if self.failure in {
                "verification",
                "verification-oserror",
                "ruleset-response-and-observation-lost",
            } and self.repository_observations >= 3:
                if self.failure == "verification-oserror":
                    raise OSError("verification transport failed")
                raise StandardsError("verification observation failed")
            return dict(self.repository)
        if endpoint.startswith("repos/owner/example/labels?"):
            return [{"name": name} for name in sorted(self.labels)]
        if endpoint.startswith("repos/owner/example/rulesets?"):
            return list(self.rulesets)
        if endpoint == "repos/owner/example/rulesets/1":
            return dict(self.rulesets[0])
        if endpoint.startswith("repos/owner/example/branches?"):
            return list(self.branches)
        if endpoint.startswith("repos/owner/example/pulls?"):
            return list(self.pulls)
        raise AssertionError(f"unexpected GitHub request: {method} {endpoint}")


class FirstPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template_directory = tempfile.TemporaryDirectory()
        template_root = Path(cls.template_directory.name).resolve()
        cls.template = template_root / "baseline"
        initialization = template_root / "initialization.json"
        initialization.write_text(
            json.dumps(
                {
                    "standards-release": (ROOT / "VERSION")
                    .read_text(encoding="utf-8")
                    .strip(),
                    "repository": "owner/example",
                    "title": "Example Repository",
                    "facts": {
                        "ecosystem": "none",
                        "package-manager": "none",
                        "project-kind": "repository",
                        "framework": "none",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        initialized = subprocess.run(
            [
                str(ROOT / "scripts/init"),
                "--input",
                str(initialization),
                "--write",
                str(cls.template),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if initialized.returncode != 0:
            raise AssertionError(initialized.stdout + initialized.stderr)
        files = {
            "README.md": (
                '<div align="center">\n  <h1>Example Repository</h1>\n'
                "</div>\n\nSee the [documentation](docs/README.md).\n"
            ),
            "LICENSE": "Test license.\n",
            "CONTEXT.md": "# Example Repository\n",
            "docs/README.md": "# Documentation\n",
            "docs/agents/domain.md": "# Domain docs\n",
        }
        for relative, content in files.items():
            target = cls.template / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        synchronized = subprocess.run(
            [str(ROOT / "scripts/sync"), "--write", str(cls.template)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if synchronized.returncode != 0:
            raise AssertionError(synchronized.stdout + synchronized.stderr)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.template_directory.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.repository = self.directory / "example"
        shutil.copytree(self.template, self.repository)
        self.remote = self.directory / "remote.git"
        subprocess.run(
            ["git", "init", "--quiet", "--bare", str(self.remote)], check=True
        )
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=main"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Publication Tester"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "publication@example.com"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                "https://github.com/owner/example.git",
            ],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "remote", "set-url", "--push", "origin", str(self.remote)],
            cwd=self.repository,
            check=True,
        )
        self.github = FakePublicationGitHub()

    def git_status(self) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def plan(self):
        return plan_first_publication(
            self.repository,
            self.github,
            standards_root=ROOT,
            now=datetime(2026, 8, 20, 12, 30, tzinfo=timezone.utc),
            _allow_local_push_for_testing=True,
        )

    def test_plan_previews_the_complete_transition_without_mutation(self) -> None:
        status_before = self.git_status()

        plan = self.plan()

        self.assertEqual(self.git_status(), status_before)
        self.assertEqual(self.github.mutations, [])
        self.assertFalse((self.repository / ".git/refs/heads/main").exists())
        self.assertFalse((self.repository / ".git/index").exists())
        self.assertEqual(plan.repository_name, "owner/example")
        self.assertEqual(plan.branch, "main")
        self.assertEqual(plan.commit.message, "chore: publish initial repository")
        self.assertEqual(plan.commit.author_name, "Publication Tester")
        self.assertEqual(plan.commit.author_email, "publication@example.com")
        self.assertIn("README.md", [item.path for item in plan.commit.files])
        self.assertTrue(plan.commit.tree_oid)
        self.assertEqual(
            plan.observed_github_state["repository"]["permissions"],
            {"admin": True, "push": True},
        )
        self.assertEqual(plan.observed_github_state["git-refs"], [])
        self.assertEqual(
            [operation.description for operation in plan.live_delta.operations],
            [
                "ESTABLISH default branch 'main'",
                "CREATE   ruleset 'Protect main'",
            ],
        )
        self.assertEqual(
            plan.steps,
            (
                "CREATE   initial commit",
                "INSTALL  initial Git index",
                "PUBLISH  main to origin",
                "ESTABLISH default branch 'main'",
                "CREATE   ruleset 'Protect main'",
                "VERIFY   committed content",
                "VERIFY   live GitHub state",
            ),
        )

    def test_plan_command_surfaces_complete_live_operations(self) -> None:
        subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "--push",
                "origin",
                "https://github.com/owner/example.git",
            ],
            cwd=self.repository,
            check=True,
        )
        git_exec_path = self.directory / "git-exec"
        git_exec_path.mkdir()
        remote_helper = git_exec_path / "git-remote-https"
        remote_helper.write_text(
            """#!/usr/bin/env python3
import sys

for command in sys.stdin:
    if command.strip() in {"capabilities", "list"}:
        print()
        sys.stdout.flush()
""",
            encoding="utf-8",
        )
        remote_helper.chmod(0o755)
        fake_gh = self.directory / "fake-gh"
        fake_gh.write_text(
            """#!/usr/bin/env python3
import json
import os
import sys

responses = json.loads(os.environ["FAKE_GITHUB_RESPONSES"])
endpoint = sys.argv[2]
if endpoint not in responses:
    print(f"unexpected endpoint: {endpoint}", file=sys.stderr)
    raise SystemExit(1)
print(json.dumps(responses[endpoint]))
""",
            encoding="utf-8",
        )
        fake_gh.chmod(0o755)
        plan_path = self.directory / "publication-plan.json"
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        plan_path.symlink_to(victim)
        responses = {
            "repos/owner/example": self.github.repository,
            "repos/owner/example/labels?per_page=100&page=1": [
                {"name": name} for name in sorted(self.github.labels)
            ],
            "repos/owner/example/rulesets?includes_parents=false&per_page=100&page=1": [],
            "repos/owner/example/branches?per_page=100&page=1": [],
            "repos/owner/example/pulls?state=all&per_page=100&page=1": [],
        }
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_GH": str(fake_gh),
                "FAKE_GITHUB_RESPONSES": json.dumps(responses),
                "GIT_EXEC_PATH": str(git_exec_path),
            }
        )

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/first-publication"),
                "plan",
                str(self.repository),
                "--plan-file",
                str(plan_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Live desired-state operations:", result.stdout)
        self.assertIn('"method": "PATCH"', result.stdout)
        self.assertIn('"endpoint": "repos/owner/example"', result.stdout)
        self.assertIn('"default_branch": "main"', result.stdout)
        self.assertIn('"required_approving_review_count": 0', result.stdout)
        self.assertEqual(
            victim.read_text(encoding="utf-8"), "unrelated content\n"
        )
        self.assertFalse(plan_path.is_symlink())
        self.assertTrue(plan_path.is_file())

    def test_publish_completes_the_planned_transition_and_proves_conformance(
        self,
    ) -> None:
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        self.assertTrue(report.standards_complete)
        self.assertEqual(report.completed, plan.steps)
        self.assertIsNone(report.failed)
        self.assertIsNone(report.uncertain)
        self.assertEqual(report.remaining, ())
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(report.commit_oid, head)
        self.assertEqual(
            subprocess.run(
                ["git", "show", "-s", "--format=%s", "HEAD"],
                cwd=self.repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "chore: publish initial repository",
        )
        remote_head = subprocess.run(
            ["git", "--git-dir", str(self.remote), "rev-parse", "refs/heads/main"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(remote_head, head)
        self.assertEqual(self.github.repository["default_branch"], "main")
        self.assertEqual(len(self.github.rulesets), 1)
        self.assertEqual(self.github.pulls, [])

    def test_plan_rejects_nonempty_remote_and_unexpected_local_commits(self) -> None:
        self.github.branches = [{"name": "main"}]
        with self.assertRaisesRegex(Exception, "remote branches already exist"):
            self.plan()

        self.github.branches = []
        subprocess.run(["git", "add", "--all"], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--message", "unexpected"],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "must have no commits"):
            self.plan()

    def test_plan_rejects_multiple_origin_push_destinations(self) -> None:
        second_remote = self.directory / "second-remote.git"
        subprocess.run(
            ["git", "init", "--quiet", "--bare", str(second_remote)], check=True
        )
        subprocess.run(
            [
                "git",
                "config",
                "--add",
                "remote.origin.pushurl",
                str(second_remote),
            ],
            cwd=self.repository,
            check=True,
        )

        with self.assertRaisesRegex(Exception, "exactly one push URL"):
            self.plan()

        self.assertEqual(self.github.mutations, [])
        for remote in (self.remote, second_remote):
            refs = subprocess.run(
                ["git", "--git-dir", str(remote), "show-ref"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refs.returncode, 1, refs.stderr)

    def test_plan_rejects_nonbranch_remote_refs_and_non_head_local_refs(self) -> None:
        seed = self.directory / "seed"
        seed.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=seed"],
            cwd=seed,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Publication Tester"],
            cwd=seed,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "publication@example.com"],
            cwd=seed,
            check=True,
        )
        (seed / "tag.txt").write_text("tag\n", encoding="utf-8")
        subprocess.run(["git", "add", "tag.txt"], cwd=seed, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--message", "tag object"],
            cwd=seed,
            check=True,
        )
        subprocess.run(["git", "tag", "--no-sign", "v1"], cwd=seed, check=True)
        subprocess.run(
            ["git", "push", "--quiet", str(self.remote), "refs/tags/v1"],
            cwd=seed,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "Git remote is not empty.*refs/tags/v1"):
            self.plan()

        subprocess.run(
            ["git", "--git-dir", str(self.remote), "update-ref", "-d", "refs/tags/v1"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "fetch",
                "--quiet",
                str(seed),
                "refs/tags/v1:refs/tags/unexpected",
            ],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "must have no local refs"):
            self.plan()

    def test_plan_rejects_missing_identity_permissions_and_prepared_drift(self) -> None:
        subprocess.run(
            ["git", "config", "--unset", "user.email"],
            cwd=self.repository,
            check=True,
        )
        empty_global_config = self.directory / "empty.gitconfig"
        empty_global_config.write_text("", encoding="utf-8")
        with patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(empty_global_config),
                "GIT_CONFIG_NOSYSTEM": "1",
            },
        ):
            with self.assertRaisesRegex(Exception, "effective Git user.email"):
                self.plan()

        subprocess.run(
            ["git", "config", "user.email", "publication@example.com"],
            cwd=self.repository,
            check=True,
        )
        self.github.repository["permissions"] = {"admin": False, "push": True}
        with self.assertRaisesRegex(Exception, "permissions: admin"):
            self.plan()

        self.github.repository["permissions"] = {"admin": True, "push": True}
        self.github.repository["has_issues"] = False
        with self.assertRaisesRegex(Exception, "prepared GitHub state has applicable drift"):
            self.plan()

    def test_plan_uses_effective_identity_without_writing_local_config(self) -> None:
        subprocess.run(
            ["git", "config", "--local", "--unset-all", "user.name"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "--local", "--unset-all", "user.email"],
            cwd=self.repository,
            check=True,
        )
        global_config = self.directory / "global.gitconfig"
        subprocess.run(
            [
                "git",
                "config",
                "--file",
                str(global_config),
                "user.name",
                "Effective Publication Tester",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "config",
                "--file",
                str(global_config),
                "user.email",
                "effective-publication@example.com",
            ],
            check=True,
        )

        with patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(global_config),
                "GIT_CONFIG_NOSYSTEM": "1",
            },
        ):
            plan = self.plan()

        self.assertEqual(plan.commit.author_name, "Effective Publication Tester")
        self.assertEqual(
            plan.commit.author_email, "effective-publication@example.com"
        )
        local_name = subprocess.run(
            ["git", "config", "--local", "--get", "user.name"],
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
        )
        local_email = subprocess.run(
            ["git", "config", "--local", "--get", "user.email"],
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(local_name.returncode, 0)
        self.assertNotEqual(local_email.returncode, 0)

    def test_publish_rejects_stale_local_and_remote_inputs_before_mutation(self) -> None:
        plan = self.plan()
        (self.repository / "README.md").write_text(
            "changed after Plan\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(Exception, "stale"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        self.assertEqual(self.github.mutations, [])
        self.assertNotEqual(self.git_status(), "")
        self.assertNotEqual(
            subprocess.run(
                ["git", "rev-parse", "--verify", "HEAD"],
                cwd=self.repository,
                check=False,
                capture_output=True,
                text=True,
            ).returncode,
            0,
        )

    def test_publish_rejects_changed_remote_identity_and_permissions(self) -> None:
        plan = self.plan()
        self.github.repository["permissions"] = {"admin": False, "push": True}

        with self.assertRaisesRegex(Exception, "stale.*permissions"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        self.assertEqual(self.github.mutations, [])

    def test_publish_rejects_any_changed_observed_github_state(self) -> None:
        plan = self.plan()
        self.github.labels.add("repository-specific")

        with self.assertRaisesRegex(Exception, "stale"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        self.assertEqual(self.github.mutations, [])

    def test_publish_rejects_changed_repository_identity_and_local_commits(self) -> None:
        plan = self.plan()
        subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                "https://github.com/owner/other.git",
            ],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "stale.*origin identifies"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        subprocess.run(
            [
                "git",
                "remote",
                "set-url",
                "origin",
                "https://github.com/owner/example.git",
            ],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(["git", "add", "--all"], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--message", "unexpected"],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "stale.*must have no commits"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )
        self.assertEqual(self.github.mutations, [])

    def test_plan_record_round_trips_and_rejects_tampering(self) -> None:
        plan = self.plan()
        path = self.directory / "publication-plan.json"

        write_publication_plan(plan, path)
        loaded = load_publication_plan(
            path, _allow_local_push_for_testing=True
        )

        self.assertEqual(loaded, plan)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["commit"]["message"] = "changed"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "identity does not match"):
            load_publication_plan(path, _allow_local_push_for_testing=True)

        write_publication_plan(plan, path)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["steps"][0] = "SKIP     initial commit"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "steps do not match"):
            load_publication_plan(path, _allow_local_push_for_testing=True)

    def test_plan_record_uses_a_private_exclusive_temporary_file(self) -> None:
        plan = self.plan()
        path = self.directory / "publication-plan.json"
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        predictable_temporary = self.directory / ".publication-plan.json.tmp"
        predictable_temporary.symlink_to(victim)

        write_publication_plan(plan, path)

        self.assertEqual(
            victim.read_text(encoding="utf-8"), "unrelated content\n"
        )
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(predictable_temporary.is_symlink())
        self.assertEqual(
            list(self.directory.glob(".publication-plan.json.*.tmp")), []
        )

    def test_plan_record_replaces_a_destination_symlink_without_following_it(
        self,
    ) -> None:
        plan = self.plan()
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        path = self.directory / "publication-plan.json"
        path.symlink_to(victim)

        write_publication_plan(plan, path)

        self.assertEqual(
            victim.read_text(encoding="utf-8"), "unrelated content\n"
        )
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            load_publication_plan(path, _allow_local_push_for_testing=True),
            plan,
        )

    def test_publish_requires_exact_confirmation_before_any_revalidation(self) -> None:
        plan = self.plan()
        observations = self.github.repository_observations

        with self.assertRaisesRegex(Exception, "exact confirmation"):
            publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.plan_id,
            )

        self.assertEqual(self.github.repository_observations, observations)
        self.assertEqual(self.github.mutations, [])

    def test_commit_failure_retains_exact_partial_state_without_rollback(self) -> None:
        plan = self.plan()
        ref_lock = self.repository / ".git/refs/heads/main.lock"
        ref_lock.parent.mkdir(parents=True, exist_ok=True)
        ref_lock.write_text("occupied\n", encoding="utf-8")

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertFalse(report.complete)
        self.assertEqual(report.completed, ())
        self.assertEqual(report.failed, "CREATE   initial commit")
        self.assertEqual(report.remaining, plan.steps[1:])
        self.assertEqual(self.github.mutations, [])
        self.assertTrue(self.git_status())
        self.assertTrue(
            all(line.startswith("?? ") for line in self.git_status().splitlines())
        )
        self.assertFalse((self.repository / ".git/index").exists())

    def test_unobservable_commit_ref_failure_reports_unknown_completion(self) -> None:
        plan = self.plan()
        real_run = subprocess.run
        update_attempted = False

        def run_with_unobservable_ref(command, *args, **kwargs):
            nonlocal update_attempted
            if "update-ref" in command:
                update_attempted = True
                return subprocess.CompletedProcess(
                    command,
                    1,
                    stdout="",
                    stderr="simulated ref update failure",
                )
            if update_attempted and (
                "show-ref" in command
                or "for-each-ref" in command
                or (
                    "rev-parse" in command
                    and f"refs/heads/{plan.branch}" in command
                )
            ):
                return subprocess.CompletedProcess(
                    command,
                    128,
                    stdout="",
                    stderr="simulated ref observation failure",
                )
            return real_run(command, *args, **kwargs)

        with patch(
            "lib.first_publication.subprocess.run",
            side_effect=run_with_unobservable_ref,
        ):
            report = publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        self.assertEqual(report.completed, ())
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "CREATE   initial commit")
        self.assertEqual(report.remaining, plan.steps[1:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertFalse((self.repository / ".git/index.lock").exists())
        self.assertEqual(self.github.mutations, [])

    def test_commit_hooks_cannot_change_planned_metadata(self) -> None:
        plan = self.plan()
        hook = self.repository / ".git/hooks/prepare-commit-msg"
        hook.write_text(
            "#!/bin/sh\nprintf 'changed message\\n' > \"$1\"\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        message = subprocess.run(
            ["git", "show", "-s", "--format=%s", "HEAD"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(message, plan.commit.message)

    def test_preexisting_staged_content_is_preserved(self) -> None:
        subprocess.run(
            ["git", "add", "README.md"], cwd=self.repository, check=True
        )
        staged_before = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

        plan = self.plan()

        staged_after_plan = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(staged_after_plan, staged_before)
        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )
        self.assertTrue(report.complete, report.error)
        self.assertEqual(self.git_status(), "")

    def test_index_install_failure_reports_the_established_commit(self) -> None:
        plan = self.plan()

        with patch(
            "lib.first_publication.os.replace",
            side_effect=OSError("index destination denied"),
        ):
            report = publish_first_publication(
                plan,
                self.github,
                standards_root=ROOT,
                confirmation=plan.confirmation,
            )

        self.assertEqual(report.completed, ("CREATE   initial commit",))
        self.assertEqual(report.failed, "INSTALL  initial Git index")
        self.assertIsNone(report.uncertain)
        self.assertEqual(report.remaining, plan.steps[2:])
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            report.commit_oid,
        )
        self.assertFalse((self.repository / ".git/index.lock").exists())
        self.assertEqual(self.github.mutations, [])

    def test_push_failure_retains_the_initial_commit_without_rollback(self) -> None:
        plan = self.plan()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:2])
        self.assertEqual(report.failed, "PUBLISH  main to origin")
        self.assertEqual(report.remaining, plan.steps[3:])
        self.assertIsNotNone(report.commit_oid)
        self.assertEqual(self.github.mutations, [])

    def test_unobservable_push_failure_reports_unknown_completion(self) -> None:
        plan = self.plan()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text(
            "#!/bin/sh\nmv \"$PWD\" \"$PWD.unavailable\"\nexit 1\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:2])
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "PUBLISH  main to origin")
        self.assertEqual(report.remaining, plan.steps[3:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertEqual(self.github.mutations, [])

    def test_default_branch_and_live_failures_report_completed_and_remaining_work(
        self,
    ) -> None:
        self.github.failure = "default"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:3])
        self.assertEqual(report.failed, "ESTABLISH default branch 'main'")
        self.assertEqual(report.remaining, plan.steps[4:])
        self.assertEqual(self.github.rulesets, [])

    def test_live_application_failure_preserves_the_published_default_branch(self) -> None:
        self.github.failure = "ruleset"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:4])
        self.assertEqual(report.failed, "CREATE   ruleset 'Protect main'")
        self.assertEqual(report.remaining, plan.steps[5:])
        self.assertEqual(self.github.repository["default_branch"], "main")

    def test_lost_live_write_response_is_reobserved_before_classification(self) -> None:
        self.github.failure = "ruleset-response-lost"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        self.assertEqual(report.completed, plan.steps)
        self.assertEqual(len(self.github.rulesets), 1)

    def test_unobservable_live_write_reports_unknown_completion(self) -> None:
        self.github.failure = "ruleset-response-and-observation-lost"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:4])
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "CREATE   ruleset 'Protect main'")
        self.assertEqual(report.remaining, plan.steps[5:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertEqual(len(self.github.rulesets), 1)

    def test_committed_content_verification_failure_reports_retained_work(self) -> None:
        plan = self.plan()
        hook = self.repository / ".git/hooks/pre-push"
        hook.write_text(
            "#!/bin/sh\nprintf 'changed during push\\n' > README.md\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:-2])
        self.assertEqual(report.failed, "VERIFY   committed content")
        self.assertEqual(report.remaining, ("VERIFY   live GitHub state",))
        self.assertIn("working tree changed", report.error or "")

    def test_final_verification_failure_reports_all_completed_mutations(self) -> None:
        self.github.failure = "verification"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:-1])
        self.assertEqual(report.failed, "VERIFY   live GitHub state")
        self.assertEqual(report.remaining, ())
        self.assertIn("verification observation failed", report.error or "")

    def test_final_verification_transport_failure_reports_retained_work(self) -> None:
        self.github.failure = "verification-oserror"
        plan = self.plan()

        report = publish_first_publication(
            plan,
            self.github,
            standards_root=ROOT,
            confirmation=plan.confirmation,
        )

        self.assertEqual(report.completed, plan.steps[:-1])
        self.assertEqual(report.failed, "VERIFY   live GitHub state")
        self.assertEqual(report.remaining, ())
        self.assertIn("verification transport failed", report.error or "")


if __name__ == "__main__":
    unittest.main()
