from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.repository_publication import (
    load_publication_proposal,
    prepare_publication_proposal,
    execute_publication,
    write_publication_proposal,
)
from lib.github_reconciliation import GitHubAdapter
from lib.repository_assessment_cli import standards_main
from lib.repository_content import StandardsError
from lib.repository_content_reconciliation import (
    apply_content_reconciliation,
    calculate_content_reconciliation,
)
from lib.repository_contract import (
    build_initial_repository_contract,
    resolve_repository_contract,
)


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


class RepositoryPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template_directory = tempfile.TemporaryDirectory()
        template_root = Path(cls.template_directory.name).resolve()
        cls.template = template_root / "baseline"
        initial = build_initial_repository_contract(
            {
                "standards-release": (ROOT / "VERSION")
                .read_text(encoding="utf-8")
                .strip(),
                "repository": "owner/example",
                "title": "Example Repository",
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
            },
            standards_root=ROOT,
        )
        cls.template.mkdir()
        (cls.template / ".repository-standards.json").write_text(
            json.dumps(initial.as_mapping(), indent=2) + "\n",
            encoding="utf-8",
        )
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
        contract = resolve_repository_contract(
            cls.template,
            standards_root=ROOT,
            retain_content_blockers=True,
        )
        report = apply_content_reconciliation(
            calculate_content_reconciliation(contract)
        )
        if not report.succeeded:
            raise AssertionError(report.failed)

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

    def proposal(self):
        return prepare_publication_proposal(
            self.repository,
            self.github,
            standards_root=ROOT,
            now=datetime(2026, 8, 20, 12, 30, tzinfo=timezone.utc),
            _allow_local_push_for_testing=True,
        )

    def test_proposal_previews_the_complete_transition_without_mutation(self) -> None:
        status_before = self.git_status()

        proposal = self.proposal()

        self.assertEqual(self.git_status(), status_before)
        self.assertEqual(self.github.mutations, [])
        self.assertFalse((self.repository / ".git/refs/heads/main").exists())
        self.assertFalse((self.repository / ".git/index").exists())
        self.assertEqual(proposal.repository_name, "owner/example")
        self.assertEqual(proposal.branch, "main")
        self.assertEqual(proposal.commit.message, "chore: publish initial repository")
        self.assertEqual(proposal.commit.author_name, "Publication Tester")
        self.assertEqual(proposal.commit.author_email, "publication@example.com")
        self.assertIn("README.md", [item.path for item in proposal.commit.files])
        self.assertTrue(proposal.commit.tree_oid)
        self.assertEqual(
            proposal.observed_github_state["repository"]["permissions"],
            {"admin": True, "push": True},
        )
        self.assertEqual(proposal.observed_github_state["git-refs"], [])
        self.assertEqual(
            [operation.description for operation in proposal.github_reconciliation.operations],
            [
                "ESTABLISH default branch 'main'",
                "CREATE   ruleset 'Protect main'",
            ],
        )
        self.assertEqual(
            proposal.steps,
            (
                "CREATE   initial commit",
                "INSTALL  initial Git index",
                "PUBLISH  main to origin",
                "ESTABLISH default branch 'main'",
                "CREATE   ruleset 'Protect main'",
                "VERIFY   committed content",
                "VERIFY   declared GitHub state",
            ),
        )

    def test_proposal_disables_git_hooks_while_constructing_the_preview(self) -> None:
        marker = self.repository / ".git/hook-ran"
        hook = self.repository / ".git/hooks/post-index-change"
        hook.write_text(
            "#!/bin/sh\n" f"touch {shlex.quote(str(marker))}\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        self.proposal()

        self.assertFalse(marker.exists())

    def test_proposal_establishes_named_default_branch_when_remote_is_empty(self) -> None:
        self.github.repository["default_branch"] = "main"

        proposal = self.proposal()

        operation = proposal.github_reconciliation.operations[0]
        self.assertEqual(operation.description, "ESTABLISH default branch 'main'")
        self.assertEqual(operation.method, "PATCH")
        self.assertEqual(operation.endpoint, "repos/owner/example")
        self.assertEqual(operation.payload, {"default_branch": "main"})


    def test_publish_completes_the_proposed_transition_and_proves_conformance(
        self,
    ) -> None:
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        self.assertTrue(report.standards_complete)
        self.assertEqual(report.completed, proposal.steps)
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

    def test_goal_interface_hides_proposal_state_and_publishes_after_confirmation(
        self,
    ) -> None:
        state_home = self.directory / "private-state"
        preview = StringIO()
        with redirect_stdout(preview), redirect_stderr(StringIO()):
            preview_status = standards_main(
                ["publish", str(self.repository)],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(preview_status, 0, preview.getvalue())
        self.assertIn("Lifecycle proposal", preview.getvalue())
        self.assertNotIn(str(state_home), preview.getvalue())
        proposal_files = [path for path in state_home.rglob("*") if path.is_file()]
        self.assertEqual(len(proposal_files), 1)
        self.assertEqual(proposal_files[0].stat().st_mode & 0o777, 0o600)
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in preview.getvalue().splitlines()
            if line.startswith("Exact confirmation required: ")
        )

        published = StringIO()
        publish_errors = StringIO()
        with redirect_stdout(published), redirect_stderr(publish_errors):
            publish_status = standards_main(
                ["publish", str(self.repository), "--confirm", confirmation],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(
            publish_status, 0, published.getvalue() + publish_errors.getvalue()
        )
        self.assertIn("Standards-complete repository: owner/example", published.getvalue())
        self.assertFalse(proposal_files[0].exists())

    def test_goal_interface_invalidates_a_stale_confirmed_proposal(self) -> None:
        state_home = self.directory / "private-state"
        preview = StringIO()
        with redirect_stdout(preview), redirect_stderr(StringIO()):
            self.assertEqual(
                standards_main(
                    ["publish", str(self.repository)],
                    github_adapter=self.github,
                    _publication_state_home=state_home,
                    _allow_local_push_for_testing=True,
                ),
                0,
            )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in preview.getvalue().splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        (self.repository / "README.md").write_text(
            "changed after proposal\n", encoding="utf-8"
        )

        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            status = standards_main(
                ["publish", str(self.repository), "--confirm", confirmation],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(status, 2)
        self.assertIn("is stale", errors.getvalue())
        self.assertEqual(self.github.mutations, [])
        self.assertFalse(any(path.is_file() for path in state_home.rglob("*")))

    def test_goal_interface_reports_partial_execution_and_invalidates_proposal(
        self,
    ) -> None:
        state_home = self.directory / "private-state"
        preview = StringIO()
        with redirect_stdout(preview), redirect_stderr(StringIO()):
            self.assertEqual(
                standards_main(
                    ["publish", str(self.repository)],
                    github_adapter=self.github,
                    _publication_state_home=state_home,
                    _allow_local_push_for_testing=True,
                ),
                0,
            )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in preview.getvalue().splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        self.github.failure = "ruleset"

        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            status = standards_main(
                ["publish", str(self.repository), "--confirm", confirmation],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(status, 2)
        self.assertIn("Completed work:", errors.getvalue())
        self.assertIn("Failed work:\n- CREATE   ruleset", errors.getvalue())
        self.assertIn("Remaining work:", errors.getvalue())
        self.assertIn("No destructive rollback was attempted", errors.getvalue())
        self.assertFalse(any(path.is_file() for path in state_home.rglob("*")))

    def test_goal_interface_reports_unknown_transition_completion(self) -> None:
        state_home = self.directory / "private-state"
        preview = StringIO()
        with redirect_stdout(preview), redirect_stderr(StringIO()):
            self.assertEqual(
                standards_main(
                    ["publish", str(self.repository)],
                    github_adapter=self.github,
                    _publication_state_home=state_home,
                    _allow_local_push_for_testing=True,
                ),
                0,
            )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in preview.getvalue().splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        self.github.failure = "ruleset-response-and-observation-lost"

        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            status = standards_main(
                ["publish", str(self.repository), "--confirm", confirmation],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(status, 2)
        self.assertIn("Completion unknown:\n- CREATE   ruleset", errors.getvalue())
        self.assertFalse(any(path.is_file() for path in state_home.rglob("*")))

    def test_goal_interface_reports_final_reobservation_failure(self) -> None:
        state_home = self.directory / "private-state"
        preview = StringIO()
        with redirect_stdout(preview), redirect_stderr(StringIO()):
            self.assertEqual(
                standards_main(
                    ["publish", str(self.repository)],
                    github_adapter=self.github,
                    _publication_state_home=state_home,
                    _allow_local_push_for_testing=True,
                ),
                0,
            )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in preview.getvalue().splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        self.github.failure = "verification"

        errors = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(errors):
            status = standards_main(
                ["publish", str(self.repository), "--confirm", confirmation],
                github_adapter=self.github,
                _publication_state_home=state_home,
                _allow_local_push_for_testing=True,
            )

        self.assertEqual(status, 2)
        self.assertIn("Failed work:\n- VERIFY   declared GitHub state", errors.getvalue())
        self.assertFalse(any(path.is_file() for path in state_home.rglob("*")))

    def test_proposal_rejects_nonempty_remote_and_unexpected_local_commits(self) -> None:
        self.github.branches = [{"name": "main"}]
        with self.assertRaisesRegex(Exception, "remote branches already exist"):
            self.proposal()

        self.github.branches = []
        subprocess.run(["git", "add", "--all"], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--message", "unexpected"],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(Exception, "must have no commits"):
            self.proposal()

    def test_proposal_rejects_required_managed_content_missing_from_initial_tree(
        self,
    ) -> None:
        (self.repository / ".git/info/exclude").write_text(
            "AGENTS.md\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(Exception, "AGENTS.md: missing"):
            self.proposal()

    def test_proposal_rejects_contract_manifest_missing_from_initial_tree(self) -> None:
        (self.repository / ".git/info/exclude").write_text(
            ".repository-standards.json\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(Exception, "no repository standards manifest"):
            self.proposal()

    def test_proposal_rejects_a_staged_contract_that_differs_from_the_worktree(
        self,
    ) -> None:
        manifest = self.repository / ".repository-standards.json"
        worktree_content = manifest.read_text(encoding="utf-8")
        staged_contract = json.loads(worktree_content)
        staged_contract["github"]["repository"] = "owner/other"
        manifest.write_text(
            json.dumps(staged_contract, indent=2) + "\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", ".repository-standards.json"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "update-index", "--assume-unchanged", ".repository-standards.json"],
            cwd=self.repository,
            check=True,
        )
        manifest.write_text(worktree_content, encoding="utf-8")

        with self.assertRaisesRegex(Exception, "committed repository contract differs"):
            self.proposal()

    def test_proposal_rejects_an_external_clean_filter_without_running_it(self) -> None:
        marker = self.repository / ".git/filter-ran"
        (self.repository / ".git/info/attributes").write_text(
            "*.md filter=proposal-side-effect\n", encoding="utf-8"
        )
        subprocess.run(
            [
                "git",
                "config",
                "filter.proposal-side-effect.clean",
                f"touch {shlex.quote(str(marker))}; cat",
            ],
            cwd=self.repository,
            check=True,
        )

        with self.assertRaisesRegex(Exception, "external Git clean filter"):
            self.proposal()

        self.assertFalse(marker.exists())

    def test_proposal_rejects_an_external_process_filter_without_running_it(self) -> None:
        marker = self.repository / ".git/filter-ran"
        (self.repository / ".git/info/attributes").write_text(
            "*.md filter=proposal-side-effect\n", encoding="utf-8"
        )
        subprocess.run(
            [
                "git",
                "config",
                "filter.proposal-side-effect.process",
                f"touch {shlex.quote(str(marker))}; cat",
            ],
            cwd=self.repository,
            check=True,
        )

        with self.assertRaisesRegex(Exception, "external Git process filter"):
            self.proposal()

        self.assertFalse(marker.exists())

    def test_proposal_rejects_a_filter_named_like_an_attribute_state(self) -> None:
        marker = self.repository / ".git/filter-ran"
        (self.repository / ".git/info/attributes").write_text(
            "*.md filter=set\n", encoding="utf-8"
        )
        subprocess.run(
            [
                "git",
                "config",
                "filter.set.clean",
                f"touch {shlex.quote(str(marker))}; cat",
            ],
            cwd=self.repository,
            check=True,
        )

        with self.assertRaisesRegex(Exception, "external Git clean filter"):
            self.proposal()

        self.assertFalse(marker.exists())

    def test_proposal_rejects_multiple_origin_push_destinations(self) -> None:
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
            self.proposal()

        self.assertEqual(self.github.mutations, [])
        for remote in (self.remote, second_remote):
            refs = subprocess.run(
                ["git", "--git-dir", str(remote), "show-ref"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refs.returncode, 1, refs.stderr)

    def test_proposal_rejects_nonbranch_remote_refs_and_non_head_local_refs(self) -> None:
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
            self.proposal()

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
            self.proposal()

    def test_proposal_rejects_missing_identity_permissions_and_prepared_drift(self) -> None:
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
                self.proposal()

        subprocess.run(
            ["git", "config", "user.email", "publication@example.com"],
            cwd=self.repository,
            check=True,
        )
        self.github.repository["permissions"] = {"admin": False, "push": True}
        with self.assertRaisesRegex(Exception, "permissions: admin"):
            self.proposal()

        self.github.repository["permissions"] = {"admin": True, "push": True}
        self.github.repository["has_issues"] = False
        with self.assertRaisesRegex(Exception, "prepared GitHub state has applicable drift"):
            self.proposal()

    def test_proposal_rejects_identity_characters_git_strips(self) -> None:
        invalid_identities = [
            ("user.name", "Publication <Tester"),
            ("user.name", "Publication >Tester"),
            ("user.email", "publication<@example.com"),
            ("user.email", "publication>@example.com"),
        ]
        for character in ",:;\"\\'":
            invalid_identities.extend(
                (
                    ("user.name", f"Publication Tester{character}"),
                    ("user.email", f"publication@example.com{character}"),
                )
            )

        for field, value in invalid_identities:
            with self.subTest(field=field, value=value):
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
                    ["git", "config", field, value],
                    cwd=self.repository,
                    check=True,
                )

                with self.assertRaisesRegex(Exception, "characters Git strips"):
                    self.proposal()

    def test_proposal_uses_effective_identity_without_writing_local_config(self) -> None:
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
            proposal = self.proposal()

        self.assertEqual(proposal.commit.author_name, "Effective Publication Tester")
        self.assertEqual(
            proposal.commit.author_email, "effective-publication@example.com"
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
        proposal = self.proposal()
        (self.repository / "README.md").write_text(
            "changed after Proposal\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(Exception, "stale"):
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
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
        proposal = self.proposal()
        self.github.repository["permissions"] = {"admin": False, "push": True}

        with self.assertRaisesRegex(Exception, "stale.*permissions"):
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
            )

        self.assertEqual(self.github.mutations, [])

    def test_publish_rejects_any_changed_observed_github_state(self) -> None:
        proposal = self.proposal()
        self.github.labels.add("repository-specific")

        with self.assertRaisesRegex(Exception, "stale"):
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
            )

        self.assertEqual(self.github.mutations, [])

    def test_publish_rejects_changed_repository_identity_and_local_commits(self) -> None:
        proposal = self.proposal()
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
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
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
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
            )
        self.assertEqual(self.github.mutations, [])

    def test_proposal_record_round_trips_and_rejects_tampering(self) -> None:
        proposal = self.proposal()
        path = self.directory / "publication-proposal.json"

        write_publication_proposal(proposal, path)
        loaded = load_publication_proposal(
            path, _allow_local_push_for_testing=True
        )

        self.assertEqual(loaded, proposal)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["commit"]["message"] = "changed"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "identity does not match"):
            load_publication_proposal(path, _allow_local_push_for_testing=True)

        write_publication_proposal(proposal, path)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["steps"][0] = "SKIP     initial commit"
        path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(Exception, "steps do not match"):
            load_publication_proposal(path, _allow_local_push_for_testing=True)


    def test_proposal_record_uses_a_private_exclusive_temporary_file(self) -> None:
        proposal = self.proposal()
        path = self.directory / "publication-proposal.json"
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        predictable_temporary = self.directory / ".publication-proposal.json.tmp"
        predictable_temporary.symlink_to(victim)

        write_publication_proposal(proposal, path)

        self.assertEqual(
            victim.read_text(encoding="utf-8"), "unrelated content\n"
        )
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(predictable_temporary.is_symlink())
        self.assertEqual(
            list(self.directory.glob(".publication-proposal.json.*.tmp")), []
        )

    def test_proposal_record_replaces_a_destination_symlink_without_following_it(
        self,
    ) -> None:
        proposal = self.proposal()
        victim = self.directory / "unrelated.json"
        victim.write_text("unrelated content\n", encoding="utf-8")
        path = self.directory / "publication-proposal.json"
        path.symlink_to(victim)

        write_publication_proposal(proposal, path)

        self.assertEqual(
            victim.read_text(encoding="utf-8"), "unrelated content\n"
        )
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            load_publication_proposal(path, _allow_local_push_for_testing=True),
            proposal,
        )

    def test_publish_requires_exact_confirmation_before_any_revalidation(self) -> None:
        proposal = self.proposal()
        observations = self.github.repository_observations

        with self.assertRaisesRegex(Exception, "exact confirmation"):
            execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.proposal_id,
            )

        self.assertEqual(self.github.repository_observations, observations)
        self.assertEqual(self.github.mutations, [])

    def test_commit_failure_retains_exact_partial_state_without_rollback(self) -> None:
        proposal = self.proposal()
        ref_lock = self.repository / ".git/refs/heads/main.lock"
        ref_lock.parent.mkdir(parents=True, exist_ok=True)
        ref_lock.write_text("occupied\n", encoding="utf-8")

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertFalse(report.complete)
        self.assertEqual(report.completed, ())
        self.assertEqual(report.failed, "CREATE   initial commit")
        self.assertEqual(report.remaining, proposal.steps[1:])
        self.assertEqual(self.github.mutations, [])
        self.assertTrue(self.git_status())
        self.assertTrue(
            all(line.startswith("?? ") for line in self.git_status().splitlines())
        )
        self.assertFalse((self.repository / ".git/index").exists())

    def test_unobservable_commit_ref_failure_reports_unknown_completion(self) -> None:
        proposal = self.proposal()
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
                    and f"refs/heads/{proposal.branch}" in command
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
            "lib.repository_publication.subprocess.run",
            side_effect=run_with_unobservable_ref,
        ):
            report = execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
            )

        self.assertEqual(report.completed, ())
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "CREATE   initial commit")
        self.assertEqual(report.remaining, proposal.steps[1:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertFalse((self.repository / ".git/index.lock").exists())
        self.assertEqual(self.github.mutations, [])

    def test_commit_hooks_cannot_change_proposed_metadata(self) -> None:
        proposal = self.proposal()
        hook = self.repository / ".git/hooks/prepare-commit-msg"
        hook.write_text(
            "#!/bin/sh\nprintf 'changed message\\n' > \"$1\"\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        message = subprocess.run(
            ["git", "show", "-s", "--format=%s", "HEAD"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(message, proposal.commit.message)

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

        proposal = self.proposal()

        staged_after_proposal = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(staged_after_proposal, staged_before)
        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )
        self.assertTrue(report.complete, report.error)
        self.assertEqual(self.git_status(), "")

    def test_index_install_failure_reports_the_established_commit(self) -> None:
        proposal = self.proposal()

        with patch(
            "lib.repository_publication.os.replace",
            side_effect=OSError("index destination denied"),
        ):
            report = execute_publication(
                proposal,
                self.github,
                standards_root=ROOT,
                confirmation=proposal.confirmation,
            )

        self.assertEqual(report.completed, ("CREATE   initial commit",))
        self.assertEqual(report.failed, "INSTALL  initial Git index")
        self.assertIsNone(report.uncertain)
        self.assertEqual(report.remaining, proposal.steps[2:])
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
        proposal = self.proposal()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:2])
        self.assertEqual(report.failed, "PUBLISH  main to origin")
        self.assertEqual(report.remaining, proposal.steps[3:])
        self.assertIsNotNone(report.commit_oid)
        self.assertEqual(self.github.mutations, [])

    def test_unobservable_push_failure_reports_unknown_completion(self) -> None:
        proposal = self.proposal()
        hook = self.remote / "hooks/pre-receive"
        hook.write_text(
            "#!/bin/sh\nmv \"$PWD\" \"$PWD.unavailable\"\nexit 1\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:2])
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "PUBLISH  main to origin")
        self.assertEqual(report.remaining, proposal.steps[3:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertEqual(self.github.mutations, [])

    def test_default_branch_and_github_failures_report_completed_and_remaining_work(
        self,
    ) -> None:
        self.github.failure = "default"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:3])
        self.assertEqual(report.failed, "ESTABLISH default branch 'main'")
        self.assertEqual(report.remaining, proposal.steps[4:])
        self.assertEqual(self.github.rulesets, [])

    def test_github_application_failure_preserves_the_published_default_branch(self) -> None:
        self.github.failure = "ruleset"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:4])
        self.assertEqual(report.failed, "CREATE   ruleset 'Protect main'")
        self.assertEqual(report.remaining, proposal.steps[5:])
        self.assertEqual(self.github.repository["default_branch"], "main")

    def test_lost_github_write_response_is_reobserved_before_classification(self) -> None:
        self.github.failure = "ruleset-response-lost"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertTrue(report.complete, report.error)
        self.assertEqual(report.completed, proposal.steps)
        self.assertEqual(len(self.github.rulesets), 1)

    def test_unobservable_github_write_reports_unknown_completion(self) -> None:
        self.github.failure = "ruleset-response-and-observation-lost"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:4])
        self.assertIsNone(report.failed)
        self.assertEqual(report.uncertain, "CREATE   ruleset 'Protect main'")
        self.assertEqual(report.remaining, proposal.steps[5:])
        self.assertIn("completion is unknown", report.error or "")
        self.assertEqual(len(self.github.rulesets), 1)

    def test_committed_content_verification_failure_reports_retained_work(self) -> None:
        proposal = self.proposal()
        hook = self.repository / ".git/hooks/pre-push"
        hook.write_text(
            "#!/bin/sh\nprintf 'changed during push\\n' > README.md\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:-2])
        self.assertEqual(report.failed, "VERIFY   committed content")
        self.assertEqual(report.remaining, ("VERIFY   declared GitHub state",))
        self.assertIn("working tree changed", report.error or "")

    def test_final_verification_failure_reports_all_completed_mutations(self) -> None:
        self.github.failure = "verification"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:-1])
        self.assertEqual(report.failed, "VERIFY   declared GitHub state")
        self.assertEqual(report.remaining, ())
        self.assertIn("verification observation failed", report.error or "")

    def test_final_verification_transport_failure_reports_retained_work(self) -> None:
        self.github.failure = "verification-oserror"
        proposal = self.proposal()

        report = execute_publication(
            proposal,
            self.github,
            standards_root=ROOT,
            confirmation=proposal.confirmation,
        )

        self.assertEqual(report.completed, proposal.steps[:-1])
        self.assertEqual(report.failed, "VERIFY   declared GitHub state")
        self.assertEqual(report.remaining, ())
        self.assertIn("verification transport failed", report.error or "")


if __name__ == "__main__":
    unittest.main()
