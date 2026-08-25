from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_SOURCE = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills"
    / "deliver-change"
)


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("codex"),
    "set RUN_FRESH_AGENT_TESTS=1 with Codex authentication to run fresh-agent tests",
)
class DeliveryFreshAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.repository = self.directory / "repository"
        self.repository.mkdir()
        self.github_state = self.directory / "fake-github.json"
        self.github_log_path = self.directory / "gh.log"
        self.validation_log = self.directory / "validation.log"
        self.remote = self.directory / "remote.git"
        shutil.copytree(
            SKILL_SOURCE,
            self.repository / ".agents/skills/deliver-change",
        )
        policy = self.repository / "standards/repository-lifecycle.md"
        policy.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "standards/repository-lifecycle.md", policy)
        self.write_fixture_guidance()
        self.write_validation_command()
        self.write_fake_github_cli()
        self.initialize_repository()
        self.github_state.write_text(
            json.dumps(self.default_github_state()) + "\n",
            encoding="utf-8",
        )

    def write_fixture_guidance(self) -> None:
        (self.repository / "AGENTS.md").write_text(
            textwrap.dedent(
                """\
                # Agent guidance

                The canonical validation command is `./validate`. GitHub delivery
                uses a ready pull request, a Conventional Commit title, and squash
                merge. Preserve unrelated local state. The GitHub repository is
                `owner/example`, its default branch is `main`, and tracked work is
                linked without a closing keyword until confirmed delivery completes.
                """
            ),
            encoding="utf-8",
        )
        for startup_file in (".zshenv", ".zprofile"):
            (self.repository / startup_file).write_text(
                'export PATH="$PWD/.fake-bin:$PATH"\n',
                encoding="utf-8",
            )

    def write_validation_command(self) -> None:
        validation = self.repository / "validate"
        validation.write_text(
            textwrap.dedent(
                """\
                #!/bin/sh
                set -eu
                validation_head=$(git rev-parse HEAD)
                if test "$validation_head" != "$FAKE_VALIDATION_EXPECTED_HEAD"; then
                    echo "validation ran outside the candidate worktree" >&2
                    exit 43
                fi
                printf '%s\n' "$validation_head" >>"$FAKE_VALIDATION_LOG"
                if test -e "$FAKE_VALIDATION_FAILURE"; then
                    echo "canonical validation failed by fixture" >&2
                    exit 42
                fi
                """
            ),
            encoding="utf-8",
        )
        validation.chmod(0o755)

    def write_fake_github_cli(self) -> None:
        fake_bin = self.repository / ".fake-bin"
        fake_bin.mkdir()
        gh = fake_bin / "gh"
        gh.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import subprocess
                import sys
                from pathlib import Path


                state_path = Path(os.environ["FAKE_GITHUB_STATE"])
                log_path = Path(os.environ["FAKE_GITHUB_LOG"])
                arguments = sys.argv[1:]
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(arguments) + "\\n")
                state = json.loads(state_path.read_text(encoding="utf-8"))


                def option(name, default=None):
                    try:
                        return arguments[arguments.index(name) + 1]
                    except (ValueError, IndexError):
                        return default


                def fields(value):
                    requested = option("--json")
                    if not requested:
                        return value
                    return {
                        key: value.get(key)
                        for key in requested.split(",")
                        if key in value
                    }


                def emit(value):
                    expression = option("--jq")
                    if expression and isinstance(value, dict):
                        current = value
                        for component in expression.lstrip(".").split("."):
                            if not isinstance(current, dict):
                                break
                            current = current.get(component)
                        if isinstance(current, (dict, list)):
                            print(json.dumps(current))
                        elif current is not None:
                            print(str(current).lower() if isinstance(current, bool) else current)
                        return
                    print(json.dumps(value) if isinstance(value, (dict, list)) else value)


                def require_target(*expected):
                    target = (
                        arguments[2]
                        if len(arguments) > 2 and not arguments[2].startswith("-")
                        else None
                    )
                    if target not in expected:
                        print(f"unexpected target: {target}", file=sys.stderr)
                        raise SystemExit(2)


                if arguments[:2] == ["auth", "status"]:
                    print("Logged in to github.com as test-user", file=sys.stderr)
                    raise SystemExit(0)

                if arguments[:2] == ["repo", "view"]:
                    if len(arguments) > 2 and arguments[2] != "owner/example":
                        print(f"unexpected repository: {arguments[2]}", file=sys.stderr)
                        raise SystemExit(2)
                    emit(fields({
                        "nameWithOwner": "owner/example",
                        "url": "https://github.com/owner/example",
                        "defaultBranchRef": {"name": "main"},
                        "deleteBranchOnMerge": True,
                        "mergeCommitAllowed": False,
                        "rebaseMergeAllowed": False,
                        "squashMergeAllowed": True,
                    }))
                    raise SystemExit(0)

                if arguments[:2] == ["pr", "list"]:
                    pull_request = state.get("pull_request")
                    emit([] if pull_request is None else [fields(pull_request)])
                    raise SystemExit(0)

                if arguments[:2] == ["pr", "create"]:
                    pull_request = {
                        "number": 17,
                        "url": "https://github.com/owner/example/pull/17",
                        "title": option("--title"),
                        "body": option("--body", ""),
                        "headRefName": option("--head", "test/delivery-candidate"),
                        "headRefOid": state["candidate_head"],
                        "baseRefName": option("--base", "main"),
                        "isDraft": False,
                        "mergeable": state["mergeable"],
                        "mergeStateStatus": "CLEAN",
                        "state": "OPEN",
                        "statusCheckRollup": state["checks"],
                        "reviews": state["reviews"],
                    }
                    state["pull_request"] = pull_request
                    state_path.write_text(json.dumps(state) + "\\n", encoding="utf-8")
                    emit(pull_request["url"])
                    raise SystemExit(0)

                if arguments[:2] == ["pr", "edit"]:
                    require_target("17", "https://github.com/owner/example/pull/17")
                    pull_request = state["pull_request"]
                    if option("--title"):
                        pull_request["title"] = option("--title")
                    if option("--body") is not None:
                        pull_request["body"] = option("--body")
                    state_path.write_text(json.dumps(state) + "\\n", encoding="utf-8")
                    emit(pull_request["url"])
                    raise SystemExit(0)

                if arguments[:2] == ["pr", "view"]:
                    require_target("17", "https://github.com/owner/example/pull/17")
                    pull_request = state["pull_request"]
                    pull_request["mergeable"] = state["mergeable"]
                    pull_request["mergeStateStatus"] = state["merge_state_status"]
                    pull_request["statusCheckRollup"] = state["checks"]
                    pull_request["reviews"] = state["reviews"]
                    emit(fields(pull_request))
                    raise SystemExit(0)

                if arguments[:2] == ["pr", "checks"]:
                    require_target("17", "https://github.com/owner/example/pull/17")
                    emit(state["checks"])
                    raise SystemExit(0 if state["checks_pass"] else 1)

                if arguments[:2] == ["pr", "merge"]:
                    require_target("17", "https://github.com/owner/example/pull/17")
                    if state.get("merge_failure"):
                        print("merge failed", file=sys.stderr)
                        raise SystemExit(1)
                    state["pull_request"]["state"] = "MERGED"
                    state["pull_request"]["mergedAt"] = "2026-08-24T12:00:00Z"
                    state["pull_request"]["mergeCommit"] = {
                        "oid": state["candidate_head"]
                    }
                    state["merged"] = True
                    state_path.write_text(json.dumps(state) + "\\n", encoding="utf-8")
                    subprocess.run(
                        [
                            "git",
                            f"--git-dir={os.environ['FAKE_REMOTE']}",
                            "update-ref",
                            "refs/heads/main",
                            state["candidate_head"],
                        ],
                        check=True,
                    )
                    if "--delete-branch" in arguments:
                        subprocess.run(
                            [
                                "git",
                                f"--git-dir={os.environ['FAKE_REMOTE']}",
                                "update-ref",
                                "-d",
                                f"refs/heads/{state['pull_request']['headRefName']}",
                            ],
                            check=True,
                        )
                    raise SystemExit(0)

                if arguments[:2] == ["issue", "view"]:
                    require_target("28", "https://github.com/owner/example/issues/28")
                    emit(fields({
                        "number": 28,
                        "state": state["issue_state"],
                        "title": "Forward-test GitHub delivery",
                        "url": "https://github.com/owner/example/issues/28",
                    }))
                    raise SystemExit(0)

                if arguments[:2] == ["issue", "close"]:
                    require_target("28", "https://github.com/owner/example/issues/28")
                    if state.get("tracker_failure"):
                        print("tracker reconciliation failed", file=sys.stderr)
                        raise SystemExit(1)
                    state["issue_state"] = "CLOSED"
                    state_path.write_text(json.dumps(state) + "\\n", encoding="utf-8")
                    raise SystemExit(0)

                if arguments[:2] == ["api", "graphql"]:
                    emit({"data": {"repository": {"pullRequest": {
                        "reviewThreads": {"nodes": state["review_threads"]}
                    }}}})
                    raise SystemExit(0)

                if arguments and arguments[0] == "api":
                    endpoint = arguments[1] if len(arguments) > 1 else ""
                    if endpoint == "repos/owner/example/pulls/17":
                        emit({
                            "state": "closed",
                            "merged": state["merged"],
                            "merged_at": state["pull_request"].get("mergedAt"),
                            "merge_commit_sha": state["candidate_head"],
                            "head": {"sha": state["candidate_head"]},
                            "base": {"sha": state["candidate_head"]},
                        })
                        raise SystemExit(0)
                    if endpoint == "repos/owner/example/commits/main":
                        emit({
                            "sha": state["candidate_head"],
                            "commit": {
                                "message": state["pull_request"]["title"]
                            },
                        })
                        raise SystemExit(0)
                    if endpoint == "repos/owner/example":
                        emit({
                            "default_branch": "main",
                            "delete_branch_on_merge": True,
                            "allow_squash_merge": True,
                            "allow_merge_commit": False,
                            "allow_rebase_merge": False,
                        })
                        raise SystemExit(0)
                    if endpoint == "repos/owner/example/branches/main/protection":
                        emit({
                            "required_status_checks": {
                                "contexts": ["CI / Required"]
                            },
                            "required_pull_request_reviews": {},
                        })
                        raise SystemExit(0)

                print(f"unsupported fake gh command: {arguments}", file=sys.stderr)
                raise SystemExit(2)
                """
            ),
            encoding="utf-8",
        )
        gh.chmod(0o755)

    def initialize_repository(self) -> None:
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.com")
        (self.repository / "caller-state.txt").write_text(
            "committed caller state\n", encoding="utf-8"
        )
        self.git("add", ".")
        self.git("commit", "-qm", "chore: create delivery fixture")
        subprocess.run(
            ["git", "init", "-q", "--bare", str(self.remote)],
            check=True,
        )
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-qu", "origin", "main")
        self.git("switch", "-qc", "test/delivery-candidate")
        (self.repository / "change.txt").write_text(
            "candidate change\n", encoding="utf-8"
        )
        self.git("add", "change.txt")
        self.git("commit", "-qm", "test(delivery): exercise forward workflow")
        self.candidate_head = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("switch", "-qc", "scratch/context", "main")
        (self.repository / "caller-state.txt").write_text(
            "staged caller state\n", encoding="utf-8"
        )
        self.git("add", "caller-state.txt")
        (self.repository / "caller-state.txt").write_text(
            "staged caller state\nunstaged caller state\n", encoding="utf-8"
        )
        (self.repository / "notes.txt").write_text(
            "unrelated local notes\n", encoding="utf-8"
        )

    def default_github_state(self) -> dict:
        return {
            "candidate_head": self.candidate_head,
            "checks": [
                {
                    "name": "CI / Required",
                    "status": "COMPLETED",
                    "conclusion": "SUCCESS",
                }
            ],
            "checks_pass": True,
            "issue_state": "OPEN",
            "merge_failure": False,
            "merge_state_status": "CLEAN",
            "mergeable": "MERGEABLE",
            "merged": False,
            "pull_request": None,
            "review_threads": [],
            "reviews": [],
            "tracker_failure": False,
        }

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_fresh_agent(self, prompt: str) -> tuple[subprocess.CompletedProcess[str], str]:
        final_message = self.repository / ".git/agent-final.txt"
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_GITHUB_LOG": str(self.github_log_path),
                "FAKE_GITHUB_STATE": str(self.github_state),
                "FAKE_REMOTE": str(self.remote),
                "FAKE_VALIDATION_FAILURE": str(self.directory / "fail-validation"),
                "FAKE_VALIDATION_EXPECTED_HEAD": self.state()["candidate_head"],
                "FAKE_VALIDATION_LOG": str(self.validation_log),
                "GH_REPO": "owner/example",
                "PATH": (
                    f"{self.repository / '.fake-bin'}"
                    f"{os.pathsep}{environment['PATH']}"
                ),
                "ZDOTDIR": str(self.repository),
            }
        )
        result = subprocess.run(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--sandbox",
                "danger-full-access",
                "--color",
                "never",
                "--output-last-message",
                str(final_message),
                "--cd",
                str(self.repository),
                prompt,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=360,
            env=environment,
        )
        final = (
            final_message.read_text(encoding="utf-8")
            if final_message.is_file()
            else ""
        )
        return result, final

    def github_log(self) -> list[list[str]]:
        log = self.github_log_path
        if not log.is_file():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]

    def state(self) -> dict:
        return json.loads(self.github_state.read_text(encoding="utf-8"))

    def local_state(self) -> tuple[str, str, str, str, bytes, bytes]:
        return (
            self.git("branch", "--show-current").stdout,
            self.git("rev-parse", "HEAD").stdout,
            self.git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            self.git("rev-parse", ":caller-state.txt").stdout,
            (self.repository / "caller-state.txt").read_bytes(),
            (self.repository / "notes.txt").read_bytes(),
        )

    def seed_pull_request(self, *, push: bool = True) -> dict:
        if push:
            self.git("push", "-qu", "origin", "test/delivery-candidate")
        state = self.state()
        state["pull_request"] = {
            "number": 17,
            "url": "https://github.com/owner/example/pull/17",
            "title": "test(delivery): exercise forward workflow",
            "body": "## Summary\n\nExercise delivery.\n\nTracked work: Refs #28",
            "headRefName": "test/delivery-candidate",
            "headRefOid": self.candidate_head,
            "baseRefName": "main",
            "isDraft": False,
            "mergeable": state["mergeable"],
            "mergeStateStatus": state["merge_state_status"],
            "state": "OPEN",
            "statusCheckRollup": state["checks"],
            "reviews": state["reviews"],
        }
        self.github_state.write_text(
            json.dumps(state) + "\n",
            encoding="utf-8",
        )
        return state["pull_request"]

    def advance_pull_request_head(self) -> str:
        worktree = self.directory / "candidate-worktree"
        self.git("worktree", "add", "-q", str(worktree), "test/delivery-candidate")
        try:
            (worktree / "change.txt").write_text(
                "candidate change\nfollow-up change\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(worktree), "add", "change.txt"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(worktree),
                    "commit",
                    "-qm",
                    "test(delivery): advance candidate",
                ],
                check=True,
            )
            new_head = subprocess.run(
                ["git", "-C", str(worktree), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(worktree),
                    "push",
                    "-q",
                    "origin",
                    "test/delivery-candidate",
                ],
                check=True,
            )
        finally:
            self.git("worktree", "remove", "--force", str(worktree))
        state = self.state()
        state["candidate_head"] = new_head
        state["pull_request"]["headRefOid"] = new_head
        self.github_state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        return new_head

    def diagnostics(
        self,
        result: subprocess.CompletedProcess[str],
        final: str,
    ) -> str:
        return "\n".join(
            (
                f"agent stdout:\n{result.stdout}",
                f"agent stderr:\n{result.stderr}",
                f"agent final:\n{final}",
                f"GitHub log:\n{self.github_log()}",
            )
        )

    def test_preparation_validates_pushes_and_restores_before_confirmation(
        self,
    ) -> None:
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to prepare branch test/delivery-candidate for "
            "GitHub delivery. Link https://github.com/owner/example/issues/28 "
            "without closing it. Do not merge."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        pull_request = state["pull_request"]
        self.assertIsNotNone(
            pull_request,
            self.diagnostics(result, final),
        )
        self.assertFalse(pull_request["isDraft"])
        self.assertTrue(
            "https://github.com/owner/example/issues/28" in pull_request["body"]
            or "refs #28" in pull_request["body"].casefold(),
            pull_request["body"],
        )
        self.assertNotIn("closes #28", pull_request["body"].casefold())
        self.assertEqual(
            self.git(
                f"--git-dir={self.remote}",
                "rev-parse",
                "refs/heads/test/delivery-candidate",
            ).stdout.strip(),
            self.candidate_head,
        )
        self.assertTrue(
            self.validation_log.is_file(),
            self.diagnostics(result, final),
        )
        validation_heads = self.validation_log.read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(
            set(validation_heads),
            {self.candidate_head},
            self.diagnostics(result, final),
        )
        self.assertEqual(
            self.local_state(),
            local_state_before,
            self.diagnostics(result, final),
        )
        self.assertFalse(state["merged"])
        self.assertFalse(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        confirmation = (
            "Exact confirmation required: Confirm delivery of "
            f"{self.candidate_head} via {pull_request['url']}"
        )
        for evidence in (
            pull_request["url"],
            self.candidate_head,
            "validation",
            "squash",
            "#28",
            "warning",
            "caller-state.txt",
            "notes.txt",
            confirmation,
        ):
            self.assertIn(evidence.casefold(), final.casefold())

    def test_existing_pull_request_is_reused_but_does_not_authorize_merge(
        self,
    ) -> None:
        pull_request = self.seed_pull_request()
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change for the existing ready pull request "
            "https://github.com/owner/example/pull/17. Reuse it, preserve the "
            "non-closing issue #28 link."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state()["pull_request"]["number"], 17)
        self.assertFalse(
            any(arguments[:2] == ["pr", "create"] for arguments in self.github_log())
        )
        self.assertFalse(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        self.assertIn(
            self.candidate_head,
            self.validation_log.read_text(encoding="utf-8").splitlines(),
            self.diagnostics(result, final),
        )
        self.assertEqual(self.local_state(), local_state_before)
        confirmation = (
            "Exact confirmation required: Confirm delivery of "
            f"{self.candidate_head} via {pull_request['url']}"
        )
        for evidence in (pull_request["url"], self.candidate_head, confirmation):
            self.assertIn(evidence.casefold(), final.casefold())

    def test_exact_confirmation_completes_and_reconciles_delivery(self) -> None:
        pull_request = self.seed_pull_request()
        state = self.state()
        state["reviews"] = [{"state": "APPROVED", "author": {"login": "reviewer"}}]
        state["pull_request"]["reviews"] = state["reviews"]
        self.github_state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        local_state_before = self.local_state()
        confirmation = (
            f"Confirm delivery of {self.candidate_head} via {pull_request['url']}"
        )

        result, final = self.run_fresh_agent(
            "Use $deliver-change to complete the previously prepared lifecycle "
            f"proposal for {pull_request['url']}. The prepared head was "
            f"{self.candidate_head}, validation passed, issue #28 was linked, "
            "and squash merge with branch cleanup was proposed. My exact reply "
            f"is: {confirmation}"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertTrue(state["merged"], self.diagnostics(result, final))
        self.assertEqual(
            state["issue_state"],
            "CLOSED",
            self.diagnostics(result, final),
        )
        log = self.github_log()
        merge_index, merge = next(
            (index, arguments)
            for index, arguments in enumerate(log)
            if arguments[:2] == ["pr", "merge"]
        )
        evidence_queries = {
            "checks": [
                index
                for index, arguments in enumerate(log)
                if arguments[:2] == ["pr", "checks"]
                or (
                    arguments[:2] == ["pr", "view"]
                    and any("statusCheckRollup" in value for value in arguments)
                )
            ],
            "reviews": [
                index
                for index, arguments in enumerate(log)
                if arguments[:2] == ["pr", "view"]
                and any("reviews" in value for value in arguments)
            ],
            "threads": [
                index
                for index, arguments in enumerate(log)
                if arguments[:2] == ["api", "graphql"]
            ],
        }
        for evidence, indices in evidence_queries.items():
            self.assertTrue(indices, f"missing {evidence}: {self.diagnostics(result, final)}")
            self.assertTrue(
                all(index < merge_index for index in indices),
                f"late {evidence}: {self.diagnostics(result, final)}",
            )
        policy_indices = [
            index
            for index, arguments in enumerate(log)
            if arguments[:3] == ["repo", "view", "owner/example"]
            or arguments[:2] == ["api", "repos/owner/example"]
        ]
        self.assertTrue(policy_indices, self.diagnostics(result, final))
        self.assertLess(max(policy_indices), merge_index)
        self.assertIn(
            merge[2],
            ("17", "https://github.com/owner/example/pull/17"),
        )
        self.assertIn("--squash", merge)
        self.assertIn("--delete-branch", merge)
        remote_branch = subprocess.run(
            [
                "git",
                f"--git-dir={self.remote}",
                "show-ref",
                "--verify",
                "refs/heads/test/delivery-candidate",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(remote_branch.returncode, 0, remote_branch.stdout)
        issue_close = next(
            arguments for arguments in log if arguments[:2] == ["issue", "close"]
        )
        self.assertIn(
            issue_close[2],
            ("28", "https://github.com/owner/example/issues/28"),
        )
        self.assertEqual(self.local_state(), local_state_before)
        for evidence in (pull_request["url"], "merged", "closed", "caller"):
            self.assertIn(evidence.casefold(), final.casefold())

    def test_inexact_confirmation_does_not_authorize_delivery(self) -> None:
        pull_request = self.seed_pull_request()
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change for the prepared proposal at "
            f"{pull_request['url']}. The prepared head was {self.candidate_head}. "
            "My reply is: The review looks good; please merge it."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state()["merged"], self.diagnostics(result, final))
        self.assertFalse(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        self.assertEqual(self.local_state(), local_state_before)
        confirmation = (
            "Confirm delivery of "
            f"{self.candidate_head} via {pull_request['url']}"
        )
        for evidence in ("exact", confirmation):
            self.assertIn(evidence.casefold(), final.casefold())

    def test_confirmed_delivery_blockers_return_unchanged_work_to_implementation(
        self,
    ) -> None:
        pull_request = self.seed_pull_request()
        state = self.state()
        state.update(
            {
                "checks": [
                    {
                        "name": "CI / Required",
                        "status": "COMPLETED",
                        "conclusion": "FAILURE",
                    },
                    {
                        "name": "Review preview",
                        "status": "IN_PROGRESS",
                        "conclusion": None,
                    },
                ],
                "checks_pass": False,
                "merge_state_status": "DIRTY",
                "mergeable": "CONFLICTING",
                "review_threads": [
                    {
                        "isResolved": False,
                        "comments": {
                            "nodes": [
                                {
                                    "body": "Correct the failing edge case.",
                                    "author": {"login": "reviewer"},
                                }
                            ]
                        },
                    }
                ],
                "reviews": [
                    {
                        "state": "CHANGES_REQUESTED",
                        "author": {"login": "reviewer"},
                    }
                ],
            }
        )
        state["pull_request"].update(
            {
                "mergeable": state["mergeable"],
                "mergeStateStatus": state["merge_state_status"],
                "reviews": state["reviews"],
                "statusCheckRollup": state["checks"],
            }
        )
        self.github_state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        content_before = self.git("show", f"{self.candidate_head}:change.txt").stdout
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to complete the prepared proposal. My exact "
            f"reply is: Confirm delivery of {self.candidate_head} via "
            f"{pull_request['url']}"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertFalse(state["merged"], self.diagnostics(result, final))
        self.assertEqual(state["issue_state"], "OPEN")
        self.assertFalse(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        self.assertEqual(
            self.git("show", f"{self.candidate_head}:change.txt").stdout,
            content_before,
        )
        self.assertEqual(self.local_state(), local_state_before)
        lowered = final.casefold()
        for evidence in (
            "fail",
            "unresolved",
            "conflict",
        ):
            self.assertIn(evidence, lowered, self.diagnostics(result, final))
        self.assertTrue(
            "fresh" in lowered or "new lifecycle proposal" in lowered,
            self.diagnostics(result, final),
        )
        self.assertTrue(
            "changes requested" in lowered or "requested changes" in lowered,
            self.diagnostics(result, final),
        )
        self.assertTrue(
            "pending" in lowered or "still running" in lowered,
            self.diagnostics(result, final),
        )

    def test_changed_head_is_revalidated_but_old_confirmation_is_rejected(
        self,
    ) -> None:
        pull_request = self.seed_pull_request()
        prepared_head = self.candidate_head
        current_head = self.advance_pull_request_head()
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to complete the previously prepared proposal. "
            f"My exact reply is: Confirm delivery of {prepared_head} via "
            f"{pull_request['url']}"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.state()["merged"], self.diagnostics(result, final))
        self.assertFalse(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        self.assertTrue(
            self.validation_log.is_file(),
            self.diagnostics(result, final),
        )
        self.assertIn(
            current_head,
            self.validation_log.read_text(encoding="utf-8").splitlines(),
        )
        self.assertEqual(self.local_state(), local_state_before)
        lowered = final.casefold()
        for evidence in (current_head, "confirmation", "stale"):
            self.assertIn(evidence.casefold(), lowered, self.diagnostics(result, final))

    def test_merge_failure_reports_remaining_work_without_tracker_mutation(
        self,
    ) -> None:
        pull_request = self.seed_pull_request()
        state = self.state()
        state["merge_failure"] = True
        self.github_state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        content_before = self.git("show", f"{self.candidate_head}:change.txt").stdout
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to complete the prepared proposal. My exact "
            f"reply is: Confirm delivery of {self.candidate_head} via "
            f"{pull_request['url']}"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertFalse(state["merged"], self.diagnostics(result, final))
        self.assertEqual(state["issue_state"], "OPEN")
        self.assertTrue(
            any(arguments[:2] == ["pr", "merge"] for arguments in self.github_log())
        )
        self.assertFalse(
            any(arguments[:2] == ["issue", "close"] for arguments in self.github_log())
        )
        self.assertEqual(
            self.git("show", f"{self.candidate_head}:change.txt").stdout,
            content_before,
        )
        self.assertEqual(self.local_state(), local_state_before)
        lowered = final.casefold()
        self.assertIn("merge", lowered)
        self.assertTrue("fail" in lowered or "not completed" in lowered)
        for evidence in ("issue", "open"):
            self.assertIn(evidence, lowered, self.diagnostics(result, final))

    def test_tracker_failure_reports_partial_delivery_without_rollback(
        self,
    ) -> None:
        pull_request = self.seed_pull_request()
        state = self.state()
        state["tracker_failure"] = True
        self.github_state.write_text(json.dumps(state) + "\n", encoding="utf-8")
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to complete the prepared proposal. My exact "
            f"reply is: Confirm delivery of {self.candidate_head} via "
            f"{pull_request['url']}"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.state()
        self.assertTrue(state["merged"], self.diagnostics(result, final))
        self.assertEqual(state["issue_state"], "OPEN")
        self.assertTrue(
            any(arguments[:2] == ["issue", "close"] for arguments in self.github_log())
        )
        self.assertEqual(self.local_state(), local_state_before)
        lowered = final.casefold()
        for evidence in ("merged", "issue", "fail"):
            self.assertIn(evidence, lowered, self.diagnostics(result, final))

    def test_failed_candidate_validation_prevents_push_and_pull_request(
        self,
    ) -> None:
        (self.directory / "fail-validation").write_text("fail\n", encoding="utf-8")
        content_before = self.git("show", f"{self.candidate_head}:change.txt").stdout
        local_state_before = self.local_state()

        result, final = self.run_fresh_agent(
            "Use $deliver-change to prepare branch test/delivery-candidate for "
            "GitHub delivery and link issue #28 without closing it."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(
            self.state()["pull_request"],
            self.diagnostics(result, final),
        )
        self.assertFalse(
            any(arguments[:2] == ["pr", "create"] for arguments in self.github_log())
        )
        remote_branch = subprocess.run(
            [
                "git",
                f"--git-dir={self.remote}",
                "show-ref",
                "--verify",
                "refs/heads/test/delivery-candidate",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(remote_branch.returncode, 0, remote_branch.stdout)
        self.assertIn(
            self.candidate_head,
            self.validation_log.read_text(encoding="utf-8").splitlines(),
        )
        self.assertEqual(
            self.git("show", f"{self.candidate_head}:change.txt").stdout,
            content_before,
        )
        self.assertEqual(self.local_state(), local_state_before)
        lowered = final.casefold()
        for evidence in ("validation", "fail"):
            self.assertIn(evidence, lowered, self.diagnostics(result, final))


if __name__ == "__main__":
    unittest.main()
