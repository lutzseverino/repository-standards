from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CREATE = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills"
    / "create-repository/scripts/create"
)


class RepositoryCreationCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.destination = self.directory / "example"
        self.log = self.directory / "operations.log"
        self.github_state = self.directory / "github.json"
        self.github_state.write_text('{"created": false}\n', encoding="utf-8")
        self.release = self.create_release()
        self.gh = self.create_fake_gh()

    def create_release(self) -> Path:
        release = self.directory / "release"
        scripts = release / "scripts"
        scripts.mkdir(parents=True)
        licenses = (
            release / ".agents/skills/create-repository/licenses"
        )
        licenses.mkdir(parents=True)
        (licenses / "catalog.json").write_text(
            json.dumps(
                {
                    "licenses": [
                        {
                            "key": "mit",
                            "spdx-id": "MIT",
                            "file": "MIT.txt",
                            "replacements": {"{{ owner }}": "owner"},
                        },
                        {
                            "key": "apache-2.0",
                            "spdx-id": "Apache-2.0",
                            "file": "Apache-2.0.txt",
                        },
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (licenses / "MIT.txt").write_text(
            "Selected release MIT license for {{ owner }}.\n",
            encoding="utf-8",
        )
        (licenses / "Apache-2.0.txt").write_text(
            "Apache License 2.0\n", encoding="utf-8"
        )
        (release / "VERSION").write_text("4.0.0\n", encoding="utf-8")
        tools = {
            "init": """\
                #!/usr/bin/env python3
                import json
                import os
                import pathlib
                import sys

                arguments = sys.argv[1:]
                destination = pathlib.Path(arguments[-1])
                mode = "write" if "--write" in arguments else "preview"
                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"init {mode}\\n")
                input_path = pathlib.Path(arguments[arguments.index("--input") + 1])
                facts = json.loads(input_path.read_text(encoding="utf-8"))
                if facts.get("facts", {}).get("ambiguous") == "true":
                    print("error: multiple selectable ecosystem profiles match", file=sys.stderr)
                    raise SystemExit(2)
                default_ruleset = {
                    "name": "Protect main",
                    "required-status-checks": ["CI / Required"],
                    "require-current-branch": True,
                    "required-approvals": 0,
                    "allowed-merge-methods": ["squash"],
                    "prevent-deletion": True,
                    "prevent-force-push": True,
                    "allow-bypass-actors": False,
                }
                ruleset = facts.get("github", {}).get("ruleset", default_ruleset)
                manifest = {
                    "standards-version": 5,
                    "standards-release": facts["standards-release"],
                    "profiles": ["common", "documentation"],
                    "repository-owned": ["README.md", "LICENSE", "CONTEXT.md", "docs/README.md", "docs/agents/domain.md"],
                    "github": {"repository": facts["repository"], "default-branch": "main", "ruleset": ruleset},
                    "variables": facts.get("variables", {}),
                }
                if mode == "preview":
                    print(json.dumps(manifest))
                    raise SystemExit(1)
                destination.mkdir(parents=True)
                (destination / ".repository-standards.json").write_text(
                    json.dumps(manifest) + "\\n", encoding="utf-8"
                )
                if os.environ.get("FAKE_REPOSITORY_CONTENT_FAILURE"):
                    if os.environ.get("FAKE_CONCURRENT_REMOTE"):
                        state_path = os.environ["FAKE_GITHUB_STATE"]
                        with open(state_path, encoding="utf-8") as handle:
                            state = json.load(handle)
                        state["created"] = True
                        with open(state_path, "w", encoding="utf-8") as handle:
                            json.dump(state, handle)
                    (destination / "LICENSE").mkdir()
                print("initialized")
            """,
            "sync": """\
                #!/usr/bin/env python3
                import os
                import pathlib
                import sys

                mode = "write" if "--write" in sys.argv else "preview"
                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"sync {mode}\\n")
                if mode == "preview":
                    print("CREATE managed.txt")
                    raise SystemExit(1)
                repository = pathlib.Path(sys.argv[-1])
                (repository / "managed.txt").write_text("managed\\n", encoding="utf-8")
            """,
            "audit": """\
                #!/usr/bin/env python3
                import os
                import pathlib
                import sys

                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("audit offline\\n")
                repository = pathlib.Path(sys.argv[-1])
                required = [".repository-standards.json", "managed.txt", "README.md", "LICENSE", "CONTEXT.md", "docs/README.md", "docs/agents/domain.md"]
                raise SystemExit(0 if all((repository / path).is_file() for path in required) else 1)
            """,
            "sync-live": """\
                #!/usr/bin/env python3
                import json
                import os
                import sys

                mode = "write" if "--write" in sys.argv else "preview"
                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"sync-live {mode} {' '.join(sys.argv[1:])}\\n")
                if mode == "write" and os.environ.get("FAKE_LIVE_WRITE_FAILURE"):
                    if os.environ.get("FAKE_DELETE_DURING_LIVE_FAILURE"):
                        with open(os.environ["FAKE_GITHUB_STATE"], encoding="utf-8") as handle:
                            state = json.load(handle)
                        state["created"] = False
                        with open(os.environ["FAKE_GITHUB_STATE"], "w", encoding="utf-8") as handle:
                            json.dump(state, handle)
                    print("injected live write failure", file=sys.stderr)
                    raise SystemExit(2)
                if mode == "write":
                    with open(os.environ["FAKE_GITHUB_STATE"], encoding="utf-8") as handle:
                        state = json.load(handle)
                    state["live_applied"] = True
                    with open(os.environ["FAKE_GITHUB_STATE"], "w", encoding="utf-8") as handle:
                        json.dump(state, handle)
                raise SystemExit(0 if mode == "write" else 1)
            """,
            "audit-live": """\
                #!/usr/bin/env python3
                import json
                import os
                import sys

                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"audit-live {' '.join(sys.argv[1:])}\\n")
                if "--json" in sys.argv:
                    with open(os.environ["FAKE_GITHUB_STATE"], encoding="utf-8") as handle:
                        state = json.load(handle)
                    errors = [] if state.get("live_applied") else [
                        "github label enhancement is missing"
                    ]
                    print(json.dumps({
                        "applicable-clean": not errors,
                        "errors": errors,
                        "pending": ["github.ruleset awaits first publication"],
                    }))
                    raise SystemExit(1 if errors else 0)
                print("Prepared live contract validated; first publication pending.")
            """,
        }
        for name, source in tools.items():
            path = scripts / name
            path.write_text(textwrap.dedent(source), encoding="utf-8")
            path.chmod(0o755)
        subprocess.run(["git", "-C", str(release), "init", "-q", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(release), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(release), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(["git", "-C", str(release), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(release), "commit", "-qm", "release fixture"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "tag.gpgSign=false",
                "-C",
                str(release),
                "tag",
                "-a",
                "v4.0.0",
                "-m",
                "release 4.0.0",
            ],
            check=True,
        )
        return release

    def create_fake_gh(self) -> Path:
        gh = self.directory / "gh"
        gh.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys

                state_path = os.environ["FAKE_GITHUB_STATE"]
                with open(state_path, encoding="utf-8") as handle:
                    state = json.load(handle)
                arguments = sys.argv[1:]
                if arguments[:2] == ["auth", "status"]:
                    raise SystemExit(0)
                if arguments[:2] == ["api", "user"]:
                    if state["created"] and os.environ.get("FAKE_REVOKE_AFTER_CREATE"):
                        print("authentication revoked", file=sys.stderr)
                        raise SystemExit(1)
                    print(json.dumps({
                        "login": "owner",
                        "plan": {
                            "name": os.environ.get("FAKE_USER_PLAN", "free")
                        },
                    }))
                    raise SystemExit(0)
                if arguments[:2] == ["api", "graphql"]:
                    requested_owner = next(
                        value.split("=", 1)[1]
                        for value in arguments
                        if value.startswith("login=")
                    )
                    organization = None
                    if requested_owner == os.environ.get("FAKE_ORGANIZATION"):
                        organization = {
                            "viewerCanAdminister": os.environ.get(
                                "FAKE_ORGANIZATION_ADMIN"
                            ) == "1",
                            "viewerCanCreateRepositories": os.environ.get(
                                "FAKE_ORGANIZATION_CAN_CREATE"
                            ) == "1",
                        }
                    print(json.dumps({"data": {"organization": organization}}))
                    raise SystemExit(0)
                if (
                    len(arguments) >= 2
                    and arguments[0] == "api"
                    and arguments[1].startswith("orgs/")
                ):
                    print(json.dumps({
                        "plan": {
                            "name": os.environ.get(
                                "FAKE_ORGANIZATION_PLAN", "free"
                            )
                        },
                        "members_can_create_public_repositories": os.environ.get(
                            "FAKE_ORGANIZATION_CAN_CREATE_PUBLIC"
                        ) == "1",
                        "members_can_create_private_repositories": os.environ.get(
                            "FAKE_ORGANIZATION_CAN_CREATE_PRIVATE"
                        ) == "1",
                        "members_can_create_internal_repositories": os.environ.get(
                            "FAKE_ORGANIZATION_CAN_CREATE_INTERNAL"
                        ) == "1",
                    }))
                    raise SystemExit(0)
                if (
                    len(arguments) >= 2
                    and arguments[0] == "api"
                    and arguments[1].startswith("repos/")
                    and arguments[1].endswith("/branches")
                ):
                    print("[]")
                    raise SystemExit(0)
                if (
                    len(arguments) >= 2
                    and arguments[0] == "api"
                    and arguments[1].startswith("repos/")
                ):
                    if os.environ.get("FAKE_PREFLIGHT_OBSERVATION_FAILURE"):
                        print("network unavailable", file=sys.stderr)
                        raise SystemExit(2)
                    if state["created"] and os.environ.get("FAKE_OBSERVATION_FAILURE"):
                        print("network unavailable", file=sys.stderr)
                        raise SystemExit(2)
                    if state["created"] and os.environ.get("FAKE_REVOKE_AFTER_CREATE"):
                        print("HTTP 404: Not Found", file=sys.stderr)
                        raise SystemExit(1)
                    if not state["created"]:
                        print("HTTP 404: Not Found", file=sys.stderr)
                        raise SystemExit(1)
                    print(json.dumps({"full_name": "owner/example"}))
                    raise SystemExit(0)
                if arguments[:2] == ["repo", "create"]:
                    state["created"] = True
                    with open(state_path, "w", encoding="utf-8") as handle:
                        json.dump(state, handle)
                    with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                        handle.write("github create\\n")
                    if os.environ.get("FAKE_CONCURRENT_CREATE_COLLISION"):
                        print("repository already exists", file=sys.stderr)
                        raise SystemExit(1)
                    if os.environ.get("FAKE_CREATE_RESPONSE_FAILURE"):
                        print("connection lost after creation", file=sys.stderr)
                        raise SystemExit(1)
                    print("https://github.com/owner/example")
                    raise SystemExit(0)
                print(f"unexpected gh invocation: {arguments}", file=sys.stderr)
                raise SystemExit(2)
                """
            ),
            encoding="utf-8",
        )
        gh.chmod(0o755)
        return gh

    def run_create(
        self,
        *arguments: str,
        extra_environment: dict[str, str] | None = None,
        use_reusable_checkout: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_SOURCE": str(self.release),
                "REPOSITORY_STANDARDS_GH": str(self.gh),
                "FAKE_GITHUB_STATE": str(self.github_state),
                "FAKE_CREATION_LOG": str(self.log),
            }
        )
        if use_reusable_checkout:
            environment["REPOSITORY_STANDARDS_CHECKOUT"] = str(self.release)
        else:
            environment.pop("REPOSITORY_STANDARDS_CHECKOUT", None)
        if extra_environment:
            environment.update(extra_environment)
        return subprocess.run(
            [
                "python3",
                str(CREATE),
                "--name",
                "example",
                "--purpose",
                "Exercise prepared repository creation.",
                "--visibility",
                "private",
                "--license",
                "MIT",
                "--owner",
                "owner",
                "--destination",
                str(self.destination),
                "--version",
                "4.0.0",
                *arguments,
            ],
            cwd=self.directory,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_success_validates_locally_before_creating_an_empty_remote(self) -> None:
        result = self.run_create(
            "--fact",
            "ecosystem=unsupported",
            "--fact",
            "project-kind=application",
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Prepared creation baseline", output)
        self.assertIn("first publication", output)
        self.assertTrue((self.destination / ".repository-standards.json").is_file())
        self.assertTrue((self.destination / "README.md").is_file())
        self.assertTrue((self.destination / "LICENSE").is_file())
        manifest = json.loads(
            (self.destination / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIsNone(manifest["github"]["ruleset"])
        self.assertEqual(manifest["variables"]["license"], "MIT")
        self.assertEqual(
            (self.destination / "LICENSE").read_text(encoding="utf-8"),
            "Selected release MIT license for owner.\n",
        )
        head = subprocess.run(
            ["git", "-C", str(self.destination), "rev-parse", "--verify", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(head.returncode, 0)
        branch = subprocess.run(
            ["git", "-C", str(self.destination), "symbolic-ref", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(branch.stdout.strip(), "main")
        remote = subprocess.run(
            ["git", "-C", str(self.destination), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(remote.stdout.strip(), "https://github.com/owner/example.git")
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])
        resolved_destination = self.destination.resolve()
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(),
            [
                "init preview",
                "init write",
                "sync preview",
                "sync write",
                "audit offline",
                "github create",
                f"sync-live preview --lifecycle prepared {resolved_destination}",
                f"sync-live write --lifecycle prepared --write {resolved_destination}",
                f"audit-live --lifecycle prepared {resolved_destination}",
            ],
        )

    def test_live_failure_retains_both_repositories_and_reports_exact_state(self) -> None:
        result = self.run_create(
            extra_environment={"FAKE_LIVE_WRITE_FAILURE": "1"},
            use_reusable_checkout=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared live synchronization write failed", result.stderr)
        self.assertIn("local destination: present", result.stderr)
        self.assertIn(
            "GitHub repository: creation confirmed; repository currently exists",
            result.stderr,
        )
        self.assertIn("origin: configured", result.stderr)
        self.assertIn(
            "prepared live reconciliation: re-observed with applicable drift",
            result.stderr,
        )
        self.assertIn(
            "applicable drift: github label enhancement is missing",
            result.stderr,
        )
        self.assertIn("no automatic deletion or rollback", result.stderr)
        self.assertTrue((self.destination / "managed.txt").is_file())
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

    def test_deleted_repository_is_reobserved_after_live_failure(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_LIVE_WRITE_FAILURE": "1",
                "FAKE_DELETE_DURING_LIVE_FAILURE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared live synchronization write failed", result.stderr)
        self.assertIn(
            "GitHub repository: creation was confirmed; repository is now absent",
            result.stderr,
        )
        self.assertIn(
            "prepared live reconciliation: not retained; GitHub repository is "
            "confirmed absent",
            result.stderr,
        )
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
        )

    def test_revoked_access_is_not_reported_as_a_retained_repository(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_LIVE_WRITE_FAILURE": "1",
                "FAKE_REVOKE_AFTER_CREATE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared live synchronization write failed", result.stderr)
        self.assertIn("GitHub repository: state unknown", result.stderr)
        self.assertNotIn("repository currently exists", result.stderr)
        self.assertIn(
            "prepared live reconciliation: state unknown; GitHub repository "
            "could not be observed",
            result.stderr,
        )

    def test_local_content_failure_reports_observed_retained_state(self) -> None:
        result = self.run_create(
            extra_environment={"FAKE_REPOSITORY_CONTENT_FAILURE": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("initial contract: present", result.stderr)
        self.assertIn(
            "local Git repository: initialized; branch: main; HEAD: unborn",
            result.stderr,
        )
        self.assertIn("README.md (file)", result.stderr)
        self.assertIn("LICENSE (directory)", result.stderr)
        self.assertIn("no automatic deletion or rollback", result.stderr)
        self.assertTrue((self.destination / "README.md").is_file())
        self.assertTrue((self.destination / "LICENSE").is_dir())
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
        )

    def test_local_failure_reobserves_a_concurrent_remote(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_REPOSITORY_CONTENT_FAILURE": "1",
                "FAKE_CONCURRENT_REMOTE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "GitHub repository: now exists; creation was not attempted by this "
            "operation",
            result.stderr,
        )
        self.assertNotIn("creation confirmed", result.stderr)

    def test_local_and_remote_collisions_stop_before_creation_mutation(self) -> None:
        collision = self.destination / "existing.txt"
        collision.parent.mkdir()
        collision.write_text("keep\n", encoding="utf-8")

        local = self.run_create()

        self.assertEqual(local.returncode, 2)
        self.assertIn("local destination collision", local.stderr)
        self.assertEqual(collision.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse(self.log.exists())
        self.assertFalse(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

        collision.unlink()
        self.destination.rmdir()
        self.github_state.write_text('{"created": true}\n', encoding="utf-8")

        remote = self.run_create()

        self.assertEqual(remote.returncode, 2)
        self.assertIn("GitHub identity collision", remote.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.log.exists())

    def test_invalid_or_ineligible_owner_stops_before_local_mutation(self) -> None:
        cases = (
            (
                "missing-owner",
                {},
                "does not identify the authenticated user or an organization",
            ),
            (
                "restricted-organization",
                {"FAKE_ORGANIZATION": "restricted-organization"},
                "cannot create repositories for GitHub organization",
            ),
        )
        for owner, environment, diagnostic in cases:
            with self.subTest(owner=owner):
                result = self.run_create(
                    "--owner",
                    owner,
                    extra_environment=environment,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())
                self.assertFalse(
                    json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
                )

    def test_github_metadata_limits_stop_before_local_mutation(self) -> None:
        cases = (
            (
                ("--name", "n" * 101),
                "repository name must not exceed 100 characters",
            ),
            (
                ("--purpose", "p" * 351),
                "purpose must not exceed 350 characters",
            ),
        )
        for arguments, diagnostic in cases:
            with self.subTest(arguments=arguments):
                result = self.run_create(*arguments)

                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())

    def test_explicit_license_is_resolved_recorded_and_written(self) -> None:
        result = self.run_create("--license", "apache-2.0")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifest = json.loads(
            (self.destination / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["variables"]["license"], "Apache-2.0")
        self.assertEqual(
            (self.destination / "LICENSE").read_text(encoding="utf-8"),
            "Apache License 2.0\n",
        )

    def test_unknown_license_stops_before_local_mutation(self) -> None:
        result = self.run_create("--license", "Unknown-1.0")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported license identifier", result.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.log.exists())

    def test_purpose_line_separators_stop_before_local_mutation(self) -> None:
        separators = (
            "\n",
            "\r",
            "\v",
            "\f",
            "\x1c",
            "\x1d",
            "\x1e",
            "\x85",
            "\u2028",
            "\u2029",
        )
        for separator in separators:
            with self.subTest(separator=ascii(separator)):
                result = self.run_create(
                    "--purpose", f"first{separator}second"
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    "purpose must be one explicit non-empty line", result.stderr
                )
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())

    def test_repository_content_escapes_html_in_the_explicit_purpose(self) -> None:
        purpose = 'Use <widgets> & "things" safely.'
        result = self.run_create("--purpose", purpose)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        readme = (self.destination / "README.md").read_text(encoding="utf-8")
        context = (self.destination / "CONTEXT.md").read_text(encoding="utf-8")
        escaped = "Use &lt;widgets&gt; &amp; &quot;things&quot; safely."
        self.assertIn(f"<p>{escaped}</p>", readme)
        self.assertIn(escaped.rstrip(".").lower(), context)
        self.assertNotIn(purpose, readme)

    def test_internal_visibility_requires_an_eligible_enterprise_organization(
        self,
    ) -> None:
        cases = (
            (
                "owner",
                {},
                "internal visibility requires an enterprise-owned GitHub organization",
            ),
            (
                "team-organization",
                {
                    "FAKE_ORGANIZATION": "team-organization",
                    "FAKE_ORGANIZATION_ADMIN": "1",
                    "FAKE_ORGANIZATION_CAN_CREATE": "1",
                    "FAKE_ORGANIZATION_PLAN": "team",
                },
                "does not support internal repositories",
            ),
        )
        for owner, environment, diagnostic in cases:
            with self.subTest(owner=owner):
                result = self.run_create(
                    "--owner",
                    owner,
                    "--visibility",
                    "internal",
                    extra_environment=environment,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())

    def test_organization_visibility_permission_is_checked_before_mutation(
        self,
    ) -> None:
        for visibility in ("public", "private"):
            with self.subTest(visibility=visibility):
                result = self.run_create(
                    "--owner",
                    "restricted-organization",
                    "--visibility",
                    visibility,
                    extra_environment={
                        "FAKE_ORGANIZATION": "restricted-organization",
                        "FAKE_ORGANIZATION_CAN_CREATE": "1",
                        "FAKE_ORGANIZATION_PLAN": "team",
                    },
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn(
                    f"cannot create {visibility} repositories", result.stderr
                )
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())

    def test_inaccessible_organization_repository_is_not_treated_as_absent(
        self,
    ) -> None:
        result = self.run_create(
            "--owner",
            "member-organization",
            extra_environment={
                "FAKE_ORGANIZATION": "member-organization",
                "FAKE_ORGANIZATION_CAN_CREATE": "1",
                "FAKE_ORGANIZATION_CAN_CREATE_PRIVATE": "1",
                "FAKE_ORGANIZATION_PLAN": "team",
            },
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot prove GitHub identity", result.stderr)
        self.assertIn("administrator visibility is required", result.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.log.exists())
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
        )

    def test_preflight_observation_failure_is_not_misreported_as_visibility(
        self,
    ) -> None:
        result = self.run_create(
            extra_environment={"FAKE_PREFLIGHT_OBSERVATION_FAILURE": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot verify GitHub identity owner/example", result.stderr)
        self.assertNotIn("administrator visibility", result.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.log.exists())

    def test_ruleset_default_follows_proven_target_support(self) -> None:
        cases = (
            ("public", {}, True),
            ("private", {"FAKE_USER_PLAN": "pro"}, True),
        )
        for visibility, environment, expected_ruleset in cases:
            with self.subTest(visibility=visibility):
                self.destination = self.directory / visibility
                self.github_state.write_text(
                    '{"created": false}\n', encoding="utf-8"
                )
                result = self.run_create(
                    "--visibility",
                    visibility,
                    extra_environment=environment,
                )

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                manifest = json.loads(
                    (self.destination / ".repository-standards.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    manifest["github"]["ruleset"] is not None,
                    expected_ruleset,
                )

    def test_unknown_plan_does_not_disable_the_canonical_ruleset(self) -> None:
        cases = (
            (
                (),
                {"FAKE_USER_PLAN": "future-personal-plan"},
                "unknown GitHub user plan",
            ),
            (
                ("--owner", "future-organization"),
                {
                    "FAKE_ORGANIZATION": "future-organization",
                    "FAKE_ORGANIZATION_ADMIN": "1",
                    "FAKE_ORGANIZATION_CAN_CREATE": "1",
                    "FAKE_ORGANIZATION_PLAN": "future-organization-plan",
                },
                "unknown GitHub organization plan",
            ),
        )
        for arguments, environment, diagnostic in cases:
            with self.subTest(arguments=arguments):
                result = self.run_create(
                    *arguments,
                    extra_environment=environment,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertFalse(self.destination.exists())
                self.assertFalse(self.log.exists())

    def test_internal_visibility_accepts_an_eligible_enterprise_organization(
        self,
    ) -> None:
        result = self.run_create(
            "--owner",
            "enterprise-organization",
            "--visibility",
            "internal",
            extra_environment={
                "FAKE_ORGANIZATION": "enterprise-organization",
                "FAKE_ORGANIZATION_ADMIN": "1",
                "FAKE_ORGANIZATION_CAN_CREATE": "1",
                "FAKE_ORGANIZATION_CAN_CREATE_INTERNAL": "1",
                "FAKE_ORGANIZATION_PLAN": "business_plus",
            },
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        remote = subprocess.run(
            ["git", "-C", str(self.destination), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            remote.stdout.strip(),
            "https://github.com/enterprise-organization/example.git",
        )
        manifest = json.loads(
            (self.destination / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["github"]["ruleset"]["name"], "Protect main")

    def test_lost_creation_response_reports_unknown_remote_attribution(
        self,
    ) -> None:
        result = self.run_create(
            extra_environment={"FAKE_CREATE_RESPONSE_FAILURE": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("GitHub repository creation failed", result.stderr)
        self.assertIn("offline baseline validated", result.stderr)
        self.assertIn(
            "GitHub repository: repository currently exists after an unconfirmed "
            "creation attempt; attribution unknown",
            result.stderr,
        )
        self.assertIn(
            "prepared live reconciliation: not observed; repository attribution "
            "is unknown",
            result.stderr,
        )
        self.assertIn("origin: not configured", result.stderr)
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

    def test_concurrent_create_collision_reports_unknown_remote_attribution(
        self,
    ) -> None:
        result = self.run_create(
            extra_environment={"FAKE_CONCURRENT_CREATE_COLLISION": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("GitHub repository creation failed", result.stderr)
        self.assertIn(
            "repository currently exists after an unconfirmed creation attempt; "
            "attribution unknown",
            result.stderr,
        )
        self.assertNotIn("creation confirmed", result.stderr)
        self.assertIn("origin: not configured", result.stderr)

    def test_inconclusive_reobservation_reports_unknown_remote_state(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_CREATE_RESPONSE_FAILURE": "1",
                "FAKE_OBSERVATION_FAILURE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("GitHub repository creation failed", result.stderr)
        self.assertIn("GitHub repository: state unknown", result.stderr)
        self.assertIn("inspect owner/example before retry", result.stderr)
        self.assertNotIn("not created by this operation", result.stderr)
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

    def test_ambiguous_profile_selection_stops_before_local_or_remote_mutation(
        self,
    ) -> None:
        result = self.run_create("--fact", "ambiguous=true")

        self.assertEqual(result.returncode, 2)
        self.assertIn("multiple selectable ecosystem profiles match", result.stderr)
        self.assertFalse(self.destination.exists())
        self.assertFalse(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(), ["init preview"]
        )

    def test_symlinked_destination_ancestor_is_rejected_before_preflight(self) -> None:
        actual_parent = self.directory / "actual"
        actual_parent.mkdir()
        linked_parent = self.directory / "linked"
        linked_parent.symlink_to(actual_parent, target_is_directory=True)
        self.destination = linked_parent / "example"

        result = self.run_create()

        self.assertEqual(result.returncode, 2)
        self.assertIn("traverses a symbolic link", result.stderr)
        self.assertFalse((actual_parent / "example").exists())
        self.assertFalse(self.log.exists())


if __name__ == "__main__":
    unittest.main()
