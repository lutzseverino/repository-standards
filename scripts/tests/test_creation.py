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
                manifest = {
                    "standards-version": 5,
                    "standards-release": facts["standards-release"],
                    "profiles": ["common", "documentation"],
                    "repository-owned": ["README.md", "LICENSE", "CONTEXT.md", "docs/README.md", "docs/agents/domain.md"],
                    "github": {"repository": facts["repository"], "default-branch": "main", "ruleset": None},
                }
                if mode == "preview":
                    print(json.dumps(manifest))
                    raise SystemExit(1)
                destination.mkdir(parents=True)
                (destination / ".repository-standards.json").write_text(
                    json.dumps(manifest) + "\\n", encoding="utf-8"
                )
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
                import os
                import sys

                mode = "write" if "--write" in sys.argv else "preview"
                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"sync-live {mode} {' '.join(sys.argv[1:])}\\n")
                if mode == "write" and os.environ.get("FAKE_LIVE_WRITE_FAILURE"):
                    print("injected live write failure", file=sys.stderr)
                    raise SystemExit(2)
                raise SystemExit(0 if mode == "write" else 1)
            """,
            "audit-live": """\
                #!/usr/bin/env python3
                import os
                import sys

                with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"audit-live {' '.join(sys.argv[1:])}\\n")
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
                if arguments[:2] == ["api", "repos/owner/example"]:
                    if state["created"] and os.environ.get("FAKE_OBSERVATION_FAILURE"):
                        print("network unavailable", file=sys.stderr)
                        raise SystemExit(2)
                    if not state["created"]:
                        print("HTTP 404: Not Found", file=sys.stderr)
                        raise SystemExit(1)
                    print(json.dumps({"full_name": "owner/example"}))
                    raise SystemExit(0)
                if arguments[:2] == ["api", "repos/owner/example/branches"]:
                    print("[]")
                    raise SystemExit(0)
                if arguments[:3] == ["repo", "create", "owner/example"]:
                    state["created"] = True
                    with open(state_path, "w", encoding="utf-8") as handle:
                        json.dump(state, handle)
                    with open(os.environ["FAKE_CREATION_LOG"], "a", encoding="utf-8") as handle:
                        handle.write("github create\\n")
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
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_CHECKOUT": str(self.release),
                "REPOSITORY_STANDARDS_GH": str(self.gh),
                "FAKE_GITHUB_STATE": str(self.github_state),
                "FAKE_CREATION_LOG": str(self.log),
            }
        )
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
            extra_environment={"FAKE_LIVE_WRITE_FAILURE": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Prepared live synchronization write failed", result.stderr)
        self.assertIn("local destination: present", result.stderr)
        self.assertIn("GitHub repository: created and retained", result.stderr)
        self.assertIn("origin: configured", result.stderr)
        self.assertIn("no automatic deletion or rollback", result.stderr)
        self.assertTrue((self.destination / "managed.txt").is_file())
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

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

    def test_lost_creation_response_reobserves_and_reports_the_retained_remote(
        self,
    ) -> None:
        result = self.run_create(
            extra_environment={"FAKE_CREATE_RESPONSE_FAILURE": "1"}
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("GitHub repository creation failed", result.stderr)
        self.assertIn("offline baseline validated", result.stderr)
        self.assertIn("GitHub repository: created and retained", result.stderr)
        self.assertIn("origin: not configured", result.stderr)
        self.assertTrue(json.loads(self.github_state.read_text(encoding="utf-8"))["created"])

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
