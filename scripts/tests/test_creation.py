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
        self.validation = self.directory / "validate"
        self.validation.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys

                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write("canonical validation\\n")
                if os.environ.get("FAKE_CANONICAL_VALIDATION_FAILURE"):
                    print("injected canonical validation failure", file=sys.stderr)
                    raise SystemExit(1)
                """
            ),
            encoding="utf-8",
        )
        self.validation.chmod(0o755)

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
        library = scripts / "lib"
        library.mkdir()
        (library / "__init__.py").write_text("", encoding="utf-8")
        (library / "repository_contract.py").write_text(
            textwrap.dedent(
                """\
                import json
                import os


                class InitialContract:
                    def __init__(self, mapping):
                        self.mapping = mapping

                    def as_mapping(self):
                        return self.mapping


                def build_initial_repository_contract(facts, *, standards_root):
                    with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                        handle.write("contract build\\n")
                    if facts.get("facts", {}).get("ambiguous") == "true":
                        raise ValueError("multiple selectable ecosystem profiles match")
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
                    return InitialContract({
                        "standards-version": 5,
                        "standards-release": facts["standards-release"],
                        "profiles": ["common", "documentation"],
                        "boundaries": [{"path": ".", "type": "repository", "title": facts["title"]}],
                        "dependency-updates": [{"ecosystem": "github-actions", "directory": "/", "schedule": "weekly"}],
                        "repository-owned": ["README.md", "LICENSE", "CONTEXT.md", "docs/README.md", "docs/agents/domain.md"],
                        "github": {
                            "repository": facts["repository"],
                            "default-branch": "main",
                            "settings": {
                                "delete-branch-on-merge": True,
                                "allow-squash-merge": True,
                                "allow-merge-commit": False,
                                "allow-rebase-merge": False,
                            },
                            "features": {"issues": True, "projects": False, "wiki": False},
                            "ruleset": ruleset,
                        },
                        "variables": facts.get("variables", {}),
                        "local-fragments": {},
                    })
                """
            ),
            encoding="utf-8",
        )
        tools = {
            "standards": """\
                #!/usr/bin/env python3
                import json
                import os
                from pathlib import Path
                import sys

                goal = sys.argv[1]
                if goal == "create" and "--contract-input" in sys.argv:
                    from lib.repository_contract import build_initial_repository_contract

                    input_path = Path(sys.argv[sys.argv.index("--contract-input") + 1])
                    initialization = json.loads(input_path.read_text(encoding="utf-8"))
                    contract = build_initial_repository_contract(
                        initialization,
                        standards_root=Path(__file__).resolve().parents[1],
                    )
                    raced_destination = os.environ.get("FAKE_RACED_DESTINATION")
                    if raced_destination:
                        Path(raced_destination).symlink_to(
                            os.environ["FAKE_RACED_OUTSIDE"],
                            target_is_directory=True,
                        )
                    print(json.dumps(contract.as_mapping(), indent=2))
                    raise SystemExit(0)
                repository = Path(sys.argv[-1])
                scope = "content" if "--scope" in sys.argv and "content" in sys.argv else "repository"
                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"standards {goal} {scope}\\n")
                state_path = Path(os.environ["FAKE_GITHUB_STATE"])
                state = json.loads(state_path.read_text(encoding="utf-8"))
                required = [
                    ".repository-standards.json", "managed.txt", "README.md", "LICENSE",
                    "CONTEXT.md", "docs/README.md", "docs/agents/domain.md",
                ]
                content_clean = all((repository / path).is_file() for path in required)
                if goal == "repair" and scope == "content":
                    if os.environ.get("FAKE_REPOSITORY_CONTENT_FAILURE"):
                        if os.environ.get("FAKE_CONCURRENT_REMOTE"):
                            state["created"] = True
                            state_path.write_text(json.dumps(state), encoding="utf-8")
                        license_path = repository / "LICENSE"
                        license_path.unlink()
                        license_path.mkdir()
                        print("injected repository content failure", file=sys.stderr)
                        raise SystemExit(2)
                    if not (repository / "LICENSE").is_file():
                        print("repository content is invalid", file=sys.stderr)
                        raise SystemExit(2)
                    (repository / "managed.txt").write_text("managed\\n", encoding="utf-8")
                    print("Assessment after repair:\\nConclusion: unverified")
                    raise SystemExit(2)
                if goal == "repair":
                    if os.environ.get("FAKE_GITHUB_WRITE_FAILURE"):
                        if os.environ.get("FAKE_DELETE_DURING_GITHUB_FAILURE"):
                            state["created"] = False
                            state_path.write_text(json.dumps(state), encoding="utf-8")
                        print("injected GitHub repair failure", file=sys.stderr)
                        raise SystemExit(2)
                    state["github_applied"] = True
                    state_path.write_text(json.dumps(state), encoding="utf-8")
                    print("Assessment after repair:\\nConclusion: not-standards-complete")
                    raise SystemExit(1)
                if goal != "check":
                    print(f"unsupported goal: {goal}", file=sys.stderr)
                    raise SystemExit(2)
                differences = []
                corrections = []
                if not content_clean:
                    differences.append({"subject": "repository-content", "description": "content differs"})
                    corrections.append({"subject": "repository-content", "action": "WRITE managed content"})
                if scope == "repository" and state.get("created") and not state.get("github_applied"):
                    differences.append({"subject": "github", "description": "required labels differ"})
                    corrections.append({"subject": "github", "action": "CREATE required labels"})
                lifecycle = "prepared" if scope == "repository" and state.get("created") else None
                payload = {
                    "conclusion": "not-standards-complete" if lifecycle else "unverified",
                    "scope": scope,
                    "lifecycle": lifecycle,
                    "differences": differences,
                    "evidence-gaps": [] if lifecycle else [{"subject": "scope", "description": "restricted evidence"}],
                    "automatic-corrections": corrections,
                    "required-maintainer-work": (
                        [{"subject": "lifecycle", "action": "perform first publication"}]
                        if lifecycle and not differences else []
                    ),
                }
                if "--json" in sys.argv:
                    print(json.dumps(payload))
                else:
                    print("Conclusion: " + payload["conclusion"])
                raise SystemExit(1 if lifecycle else 2)
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
                "--validation-command",
                str(self.validation),
                *arguments,
            ],
            cwd=self.directory,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def run_standards_create(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_CHECKOUT": str(self.release),
                "REPOSITORY_STANDARDS_GH": str(self.gh),
                "FAKE_GITHUB_STATE": str(self.github_state),
                "FAKE_CREATION_LOG": str(self.log),
            }
        )
        return subprocess.run(
            [
                str(ROOT / "scripts/standards"),
                "create",
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
                "--validation-command",
                str(self.validation),
                "--fact",
                "ecosystem=unsupported",
                "--fact",
                "project-kind=application",
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
                "contract build",
                "standards repair content",
                "standards check content",
                "canonical validation",
                "github create",
                "standards repair repository",
                "standards check repository",
            ],
        )

    def test_canonical_validation_failure_stops_before_remote_creation(self) -> None:
        result = self.run_create(
            "--fact",
            "ecosystem=unsupported",
            "--fact",
            "project-kind=application",
            extra_environment={"FAKE_CANONICAL_VALIDATION_FAILURE": "1"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Canonical validation failed", result.stderr)
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
        )
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(),
            [
                "contract build",
                "standards repair content",
                "standards check content",
                "canonical validation",
            ],
        )

    def test_destination_replaced_during_preflight_is_rejected_before_write(
        self,
    ) -> None:
        outside = self.directory / "raced-outside"
        outside.mkdir()
        sentinel = outside / "keep.txt"
        sentinel.write_text("keep\n", encoding="utf-8")

        result = self.run_create(
            extra_environment={
                "FAKE_RACED_DESTINATION": str(self.destination),
                "FAKE_RACED_OUTSIDE": str(outside),
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("local destination traverses a symbolic link", result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((outside / ".repository-standards.json").exists())
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
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

    def test_standards_create_defaults_to_the_participating_repository_goal(self) -> None:
        result = self.run_standards_create()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Prepared creation baseline", result.stdout)
        self.assertFalse(
            subprocess.run(
                ["git", "-C", str(self.destination), "rev-parse", "--verify", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            ).returncode
            == 0
        )

    def test_github_failure_retains_both_repositories_and_reports_exact_state(self) -> None:
        result = self.run_create(
            extra_environment={"FAKE_GITHUB_WRITE_FAILURE": "1"},
            use_reusable_checkout=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared repository repair failed", result.stderr)
        self.assertIn("local destination: present", result.stderr)
        self.assertIn(
            "GitHub repository: creation confirmed; repository currently exists",
            result.stderr,
        )
        self.assertIn("origin: configured", result.stderr)
        self.assertIn(
            "prepared GitHub reconciliation: re-observed with applicable drift",
            result.stderr,
        )
        self.assertIn(
            "applicable drift: required labels differ",
            result.stderr,
        )
        self.assertIn("no automatic deletion or rollback", result.stderr)
        self.assertTrue((self.destination / "managed.txt").is_file())
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

    def test_deleted_repository_is_reobserved_after_github_failure(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_GITHUB_WRITE_FAILURE": "1",
                "FAKE_DELETE_DURING_GITHUB_FAILURE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared repository repair failed", result.stderr)
        self.assertIn(
            "GitHub repository: creation was confirmed; repository is now absent",
            result.stderr,
        )
        self.assertIn(
            "prepared GitHub reconciliation: not retained; GitHub repository is "
            "confirmed absent",
            result.stderr,
        )
        self.assertFalse(
            json.loads(self.github_state.read_text(encoding="utf-8"))["created"]
        )

    def test_revoked_access_is_not_reported_as_a_retained_repository(self) -> None:
        result = self.run_create(
            extra_environment={
                "FAKE_GITHUB_WRITE_FAILURE": "1",
                "FAKE_REVOKE_AFTER_CREATE": "1",
            }
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared repository repair failed", result.stderr)
        self.assertIn("GitHub repository: state unknown", result.stderr)
        self.assertNotIn("repository currently exists", result.stderr)
        self.assertIn(
            "prepared GitHub reconciliation: state unknown; GitHub repository "
            "could not be observed",
            result.stderr,
        )


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
        self.assertIn("canonical validation passed", result.stderr)
        self.assertIn(
            "GitHub repository: repository currently exists after an unconfirmed "
            "creation attempt; attribution unknown",
            result.stderr,
        )
        self.assertIn(
            "prepared GitHub reconciliation: not observed; repository attribution "
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
            self.log.read_text(encoding="utf-8").splitlines(), ["contract build"]
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
