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
ADOPT = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills"
    / "adopt-standards/scripts/adopt"
)


class AdoptionCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        self.repository.mkdir()
        self.run_git("init", "-q", "-b", "main")
        self.run_git("config", "user.name", "Test User")
        self.run_git("config", "user.email", "test@example.com")
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8"
        )
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "initial")

    def manifest(self) -> dict[str, Any]:
        return {
            "standards-version": 5,
            "standards-release": "1.0.0",
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
                "ruleset": None,
            },
            "variables": {},
            "local-fragments": {},
            "repository-owned": ["README.md"],
        }

    def run_git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_adopt(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
        validation_command: str = "true",
    ) -> subprocess.CompletedProcess[str]:
        command_environment = os.environ.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            [
                "python3",
                str(ADOPT),
                "--validation-command",
                validation_command,
                *arguments,
                "--repository",
                str(self.repository),
            ],
            cwd=self.repository,
            env=command_environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def run_standards_adopt(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
        validation_command: str = "true",
    ) -> subprocess.CompletedProcess[str]:
        command_environment = os.environ.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            [
                str(ROOT / "scripts/standards"),
                "adopt",
                *arguments,
                "--repository",
                str(self.repository),
                "--validation-command",
                validation_command,
            ],
            cwd=self.repository,
            env=command_environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def create_release_source(self, version: str = "2.0.0") -> Path:
        source = self.directory / f"standards-{version}"
        source.mkdir()
        subprocess.run(["git", "-C", str(source), "init", "-q", "-b", "main"], check=True)
        subprocess.run(
            ["git", "-C", str(source), "config", "user.name", "Test User"], check=True
        )
        subprocess.run(
            ["git", "-C", str(source), "config", "user.email", "test@example.com"],
            check=True,
        )
        (source / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        scripts = source / "scripts"
        scripts.mkdir()
        tools = {
            "standards": """\
                #!/usr/bin/env python3
                import json
                import os
                from pathlib import Path
                import sys

                goal = sys.argv[1]
                repository = Path(sys.argv[-1])
                version = (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip()
                with open(os.environ["FAKE_RELEASE_LOG"], "a", encoding="utf-8") as handle:
                    handle.write(f"standards {goal} {version}\\n")
                manifest = json.loads(
                    (repository / ".repository-standards.json").read_text(encoding="utf-8")
                )
                if manifest.get("standards-version") != 5:
                    print("error: unsupported standards-version", file=sys.stderr)
                    raise SystemExit(2)
                if "managed.txt" in manifest.get("repository-owned", []):
                    print(
                        "error: managed target 'managed.txt' conflicts with repository-owned pattern",
                        file=sys.stderr,
                    )
                    raise SystemExit(2)
                managed = repository / "managed.txt"
                obsolete = repository / "obsolete.txt"
                current_adapter = repository / ".agents/skills/adopt-standards/SKILL.md"
                expected = f"managed by {version}\\n"
                drift = (
                    not managed.is_file()
                    or managed.read_text() != expected
                    or obsolete.exists()
                    or not current_adapter.is_file()
                )
                if goal == "check":
                    if os.environ.get("FAKE_GITHUB_CHECK_FAILURE") and not drift:
                        print("Conclusion: unverified")
                        raise SystemExit(2)
                    if "--json" in sys.argv:
                        corrections = []
                        if not managed.is_file() or managed.read_text() != expected:
                            corrections.append({
                                "subject": "repository-content",
                                "action": "WRITE managed.txt",
                                "kind": "update",
                                "target": "managed.txt",
                            })
                        if obsolete.exists():
                            corrections.append({
                                "subject": "repository-content",
                                "action": "DELETE obsolete.txt",
                                "kind": "delete",
                                "target": "obsolete.txt",
                            })
                        print(json.dumps({
                            "conclusion": "not-standards-complete" if drift else "standards-complete",
                            "lifecycle": "published",
                            "automatic-corrections": corrections,
                        }))
                    else:
                        print("Conclusion: " + ("not-standards-complete" if drift else "standards-complete"))
                    raise SystemExit(1 if drift else 0)
                if goal != "repair":
                    print(f"unsupported goal: {goal}", file=sys.stderr)
                    raise SystemExit(2)
                print("Assessment before repair:")
                if os.environ.get("FAKE_GITHUB_WRITE_FAILURE"):
                    print("GitHub write failed", file=sys.stderr)
                    raise SystemExit(2)
                managed.write_text(expected, encoding="utf-8")
                if obsolete.exists():
                    obsolete.unlink()
                current_adapter.parent.mkdir(parents=True, exist_ok=True)
                current_adapter.write_text(
                    "---\\nname: adopt-standards\\n---\\n", encoding="utf-8"
                )
                print("Assessment after repair:\\nConclusion: standards-complete")
            """,
        }
        for name, content in tools.items():
            path = scripts / name
            path.write_text(textwrap.dedent(content), encoding="utf-8")
            path.chmod(0o755)
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-qm", f"release {version}"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "tag.gpgSign=false",
                "-C",
                str(source),
                "tag",
                "-a",
                f"v{version}",
                "-m",
                f"release {version}",
            ],
            check=True,
        )
        return source

    def prepare_target_for_adoption(self) -> None:
        (self.repository / "obsolete.txt").write_text("retired\n", encoding="utf-8")
        check = self.repository / "check.sh"
        check.write_text(
            "#!/bin/sh\ntest -f managed.txt && test ! -e obsolete.txt\n",
            encoding="utf-8",
        )
        check.chmod(0o755)
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "prepare adoption fixture")

    def test_dirty_repository_is_rejected_before_release_access(self) -> None:
        (self.repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        self.run_git("add", "tracked.txt")
        self.run_git("commit", "-qm", "add tracked file")
        (self.repository / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.repository / "untracked.txt").write_text("new\n", encoding="utf-8")
        before = self.run_git("status", "--porcelain=v1", "--untracked-files=all").stdout

        result = self.run_adopt(
            "2.0.0",
            environment={"REPOSITORY_STANDARDS_SOURCE": "/must/not/be/read"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("working tree must be clean", result.stderr)
        self.assertIn("tracked.txt", result.stderr)
        self.assertIn("untracked.txt", result.stderr)
        self.assertNotIn("release tag", result.stderr)
        self.assertEqual(
            self.run_git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            before,
        )

    def test_explicit_version_rejects_unsafe_requests(self) -> None:
        cases = (
            ("v2.0.0", 2, "malformed standards version"),
            ("2.0.0-rc.1", 2, "prerelease standards version"),
            ("2.0.0+build.1", 2, "build metadata is not a stable release"),
            ("0.9.0", 2, "downgrade"),
        )
        for version, returncode, message in cases:
            with self.subTest(version=version):
                result = self.run_adopt(
                    version,
                    environment={
                        "REPOSITORY_STANDARDS_SOURCE": "/must/not/be/read"
                    },
                )
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, returncode, output)
                self.assertIn(message, output)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_same_release_reconciles_and_runs_every_completion_check(self) -> None:
        source = self.create_release_source("1.0.0")
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "1.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Reconciled standards release 1.0.0", output)
        self.assertEqual(
            (self.repository / "managed.txt").read_text(encoding="utf-8"),
            "managed by 1.0.0\n",
        )
        self.assertFalse((self.repository / "obsolete.txt").exists())
        self.assertEqual(
            release_log.read_text(encoding="utf-8").splitlines(),
            [
                "standards check 1.0.0",
                "standards repair 1.0.0",
                "standards check 1.0.0",
            ],
        )

    def test_explicit_release_uses_its_goal_interface_and_creates_a_validated_commit(
        self,
    ) -> None:
        source = self.create_release_source()
        self.prepare_target_for_adoption()
        original_head = self.run_git("rev-parse", "HEAD").stdout.strip()
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Assessment before repair", output)
        self.assertIn("Prepared standards adoption 1.0.0 -> 2.0.0", output)
        manifest = json.loads(
            (self.repository / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["standards-release"], "2.0.0")
        self.assertEqual(
            (self.repository / "managed.txt").read_text(encoding="utf-8"),
            "managed by 2.0.0\n",
        )
        self.assertFalse((self.repository / "obsolete.txt").exists())
        self.assertNotEqual(self.run_git("rev-parse", "HEAD").stdout.strip(), original_head)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")
        self.assertEqual(
            self.run_git("show", "-s", "--format=%s", "HEAD").stdout.strip(),
            "chore(standards): adopt repository standards 2.0.0",
        )
        self.assertEqual(
            release_log.read_text(encoding="utf-8").splitlines(),
            [
                "standards check 2.0.0",
                "standards repair 2.0.0",
                "standards check 2.0.0",
            ],
        )

    def test_standards_adopt_uses_the_participating_repository_goal(self) -> None:
        source = self.create_release_source()
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"

        result = self.run_standards_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")
        self.assertIn("validated adoption commit", result.stdout)

    def test_v4_bootstrap_reaches_the_current_adoption_goal_without_wrappers(
        self,
    ) -> None:
        manifest_path = self.repository / ".repository-standards.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["standards-release"] = "4.0.0"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        source_prefix = Path(
            "profiles/repository-lifecycle-skills/files"
        )
        listed = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "ls-tree",
                "-r",
                "--name-only",
                "v4.0.0",
                str(source_prefix),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        v4_sources = {
            Path(line)
            for line in listed.stdout.splitlines()
            if "/.agents/skills/" in line
        }
        current_sources = {
            path.relative_to(ROOT)
            for path in (ROOT / source_prefix).rglob("*")
            if path.is_file() and "/.agents/skills/" in str(path)
        }
        removed_sources = v4_sources - current_sources
        self.assertTrue(removed_sources)

        for source in v4_sources:
            blob = subprocess.run(
                ["git", "-C", str(ROOT), "show", f"v4.0.0:{source}"],
                check=True,
                capture_output=True,
            ).stdout
            target = self.repository / source.relative_to(source_prefix)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "representative v4 lifecycle adapters")

        removed_targets = tuple(
            self.repository / source.relative_to(source_prefix)
            for source in sorted(removed_sources)
        )
        for target in removed_targets:
            target.unlink()
        self.run_git("add", "-u")
        self.run_git("commit", "-qm", "bootstrap current task grammar")

        source = self.create_release_source("5.0.0")
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"
        result = self.run_standards_adopt(
            "5.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(
            (self.repository / ".agents/skills/adopt-standards/SKILL.md").is_file()
        )
        self.assertTrue(all(not target.exists() for target in removed_targets))
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_omitted_version_adopts_the_latest_stable_release(self) -> None:
        source = self.create_release_source()
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "2.0.0",
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("Resolved latest stable standards release: 2.0.0", output)
        self.assertIn("Prepared standards adoption 1.0.0 -> 2.0.0", output)

    def test_missing_release_tag_is_rejected_without_target_changes(self) -> None:
        source = self.create_release_source()

        result = self.run_adopt(
            "3.0.0",
            environment={"REPOSITORY_STANDARDS_SOURCE": str(source)},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("stable release tag v3.0.0 was not found", result.stderr)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_reused_checkout_must_prove_the_exact_requested_tag(self) -> None:
        source = self.create_release_source()
        (source / "after-tag.txt").write_text("later\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-qm", "after tag"], check=True
        )

        result = self.run_adopt(
            "2.0.0",
            environment={"REPOSITORY_STANDARDS_CHECKOUT": str(source)},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("not proven at exact tag v2.0.0", result.stderr)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_reused_exact_checkout_must_also_be_clean(self) -> None:
        source = self.create_release_source()
        (source / "scripts/standards").write_text(
            "#!/bin/sh\necho modified tooling\n", encoding="utf-8"
        )

        result = self.run_adopt(
            "2.0.0",
            environment={"REPOSITORY_STANDARDS_CHECKOUT": str(source)},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("exact release checkout must be clean", result.stderr)
        self.assertIn("scripts/standards", result.stderr)
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_incompatible_manifest_protocol_fails_before_writes(
        self,
    ) -> None:
        source = self.create_release_source()
        manifest_path = self.repository / ".repository-standards.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["standards-version"] = 99
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "use incompatible protocol")
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("incompatible standards-version 99", result.stderr)
        self.assertFalse(release_log.exists())
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_incompatible_manifest_protocol_is_rejected_before_equal_version_no_op(
        self,
    ) -> None:
        manifest_path = self.repository / ".repository-standards.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["standards-version"] = 99
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "use incompatible protocol")

        result = self.run_adopt(
            "1.0.0",
            environment={"REPOSITORY_STANDARDS_SOURCE": "/must/not/be/read"},
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("incompatible standards-version 99", result.stderr)
        self.assertNotIn("already adopts", result.stdout)

    def test_repository_owned_conflict_fails_during_preview_before_writes(self) -> None:
        source = self.create_release_source()
        manifest_path = self.repository / ".repository-standards.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["repository-owned"].append("managed.txt")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        self.run_git("add", ".")
        self.run_git("commit", "-qm", "reserve managed target")
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("conflicts with repository-owned pattern", result.stderr)
        self.assertEqual(
            release_log.read_text(encoding="utf-8").splitlines(),
            ["standards check 2.0.0"],
        )
        self.assertEqual(self.run_git("status", "--porcelain=v1").stdout, "")

    def test_ignored_managed_absence_is_rejected_before_preview_or_writes(self) -> None:
        source = self.create_release_source()
        (self.repository / ".gitignore").write_text("obsolete.txt\n", encoding="utf-8")
        check = self.repository / "check.sh"
        check.write_text(
            "#!/bin/sh\ntest -f managed.txt && test ! -e obsolete.txt\n",
            encoding="utf-8",
        )
        check.chmod(0o755)
        self.run_git("add", ".gitignore", "check.sh")
        self.run_git("commit", "-qm", "ignore obsolete managed path")
        obsolete = self.repository / "obsolete.txt"
        obsolete.write_text("ignored but forbidden\n", encoding="utf-8")
        self.assertEqual(
            self.run_git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            "",
        )
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="./check.sh",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("ignored managed absences cannot be previewed", result.stderr)
        self.assertIn("obsolete.txt", result.stderr)
        self.assertTrue(obsolete.exists())
        self.assertFalse((self.repository / "managed.txt").exists())
        self.assertEqual(
            release_log.read_text(encoding="utf-8").splitlines(),
            ["standards check 2.0.0"],
        )

    def test_canonical_validation_failure_leaves_applied_changes_uncommitted(
        self,
    ) -> None:
        source = self.create_release_source()
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"
        original_head = self.run_git("rev-parse", "HEAD").stdout.strip()

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
            },
            validation_command="false",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Canonical validation failed", result.stderr)
        self.assertEqual(self.run_git("rev-parse", "HEAD").stdout.strip(), original_head)
        self.assertNotEqual(self.run_git("status", "--porcelain=v1").stdout, "")
        self.assertEqual(
            release_log.read_text(encoding="utf-8").splitlines(),
            ["standards check 2.0.0", "standards repair 2.0.0"],
        )

    def test_final_standards_check_failure_leaves_applied_changes_uncommitted(
        self,
    ) -> None:
        source = self.create_release_source()
        self.prepare_target_for_adoption()
        release_log = self.directory / "release-tools.log"

        result = self.run_adopt(
            "2.0.0",
            environment={
                "REPOSITORY_STANDARDS_SOURCE": str(source),
                "FAKE_RELEASE_LOG": str(release_log),
                "FAKE_GITHUB_CHECK_FAILURE": "1",
            },
            validation_command="./check.sh",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Conclusion: unverified", result.stdout)
        self.assertIn("Final standards check failed", result.stderr)
        self.assertNotEqual(self.run_git("status", "--porcelain=v1").stdout, "")


if __name__ == "__main__":
    unittest.main()
