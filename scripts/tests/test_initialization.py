from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INITIALIZE = ROOT / "scripts/init"


class RepositoryInitializationCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.destination = self.directory / "example"
        self.input_path = self.directory / "initialization.json"

    def write_input(self, **overrides: object) -> None:
        initialization = {
            "standards-release": (ROOT / "VERSION").read_text(
                encoding="utf-8"
            ).strip(),
            "repository": "owner/example",
            "title": "Example Repository",
            "facts": {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "none",
            },
        }
        initialization.update(overrides)
        self.input_path.write_text(
            json.dumps(initialization, indent=2) + "\n", encoding="utf-8"
        )

    def run_initialize(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(INITIALIZE),
                "--input",
                str(self.input_path),
                *arguments,
                str(self.destination),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_preview_then_write_produces_a_valid_complete_contract(self) -> None:
        self.write_input()

        preview = self.run_initialize()

        self.assertEqual(preview.returncode, 1, preview.stderr)
        self.assertFalse(self.destination.exists())
        previewed = json.loads(preview.stdout)
        self.assertEqual(
            previewed["profiles"],
            ["common", "documentation", "node-npm"],
        )
        self.assertEqual(previewed["github"]["repository"], "owner/example")
        self.assertEqual(previewed["github"]["default-branch"], "main")
        self.assertEqual(
            previewed["github"]["ruleset"],
            {
                "name": "Protect main",
                "required-status-checks": ["CI / Required"],
                "require-current-branch": True,
                "required-approvals": 0,
                "allowed-merge-methods": ["squash"],
                "prevent-deletion": True,
                "prevent-force-push": True,
                "allow-bypass-actors": False,
            },
        )

        written = self.run_initialize("--write")

        self.assertEqual(written.returncode, 0, written.stderr)
        manifest_path = self.destination / ".repository-standards.json"
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8")), previewed)

        verified = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "from pathlib import Path; "
                    "from scripts.lib.repository_contract import "
                    "resolve_repository_contract; "
                    f"resolve_repository_contract(Path({str(self.destination)!r}), "
                    f"standards_root=Path({str(ROOT)!r}))"
                ),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_explicitly_unsupported_rulesets_remain_disabled(self) -> None:
        self.write_input(github={"ruleset": None})

        preview = self.run_initialize()

        self.assertEqual(preview.returncode, 1, preview.stderr)
        self.assertIsNone(json.loads(preview.stdout)["github"]["ruleset"])

    def test_multiple_qualifying_profiles_stop_before_destination_mutation(self) -> None:
        self.write_input(
            facts={
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "vite-react",
            }
        )

        result = self.run_initialize("--write")

        self.assertEqual(result.returncode, 2)
        self.assertIn(
            "multiple selectable ecosystem profiles match", result.stderr
        )
        self.assertIn("node-npm", result.stderr)
        self.assertIn("vite-react", result.stderr)
        self.assertFalse(self.destination.exists())

    def test_each_ecosystem_profile_has_an_observable_applicability_match(self) -> None:
        cases = {
            "node-protocol": {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "protocol",
                "framework": "none",
            },
            "pnpm-workspace": {
                "ecosystem": "node",
                "package-manager": "pnpm",
                "project-kind": "workspace",
                "framework": "none",
            },
            "spring-boot": {
                "ecosystem": "java",
                "framework": "spring-boot",
                "project-kind": "service",
            },
            "paper-plugin": {
                "ecosystem": "java",
                "framework": "paper",
                "project-kind": "plugin",
            },
            "tauri": {
                "ecosystem": "rust",
                "framework": "tauri",
                "project-kind": "desktop-application",
            },
            "codex-skill": {
                "ecosystem": "codex",
                "project-kind": "skill",
            },
        }
        for profile, facts in cases.items():
            with self.subTest(profile=profile):
                self.write_input(facts=facts)

                result = self.run_initialize()

                self.assertEqual(result.returncode, 1, result.stderr)
                manifest = json.loads(result.stdout)
                self.assertEqual(
                    manifest["profiles"],
                    ["common", "documentation", profile],
                )

    def test_incomplete_applicability_facts_stop_before_mutation(self) -> None:
        for facts, missing in (
            ({}, "ecosystem"),
            ({"ecosystem": "node"}, "package-manager"),
        ):
            with self.subTest(facts=facts):
                self.write_input(facts=facts)

                result = self.run_initialize("--write")

                self.assertEqual(result.returncode, 2)
                self.assertIn("applicability facts are incomplete", result.stderr)
                self.assertIn(missing, result.stderr)
                self.assertFalse(self.destination.exists())

    def test_no_match_uses_only_the_mandatory_baseline(self) -> None:
        self.write_input(
            facts={
                "ecosystem": "elixir",
                "project-kind": "application",
            }
        )

        result = self.run_initialize()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"], ["common", "documentation"]
        )

    def test_explicit_selection_resolves_multiple_qualifying_profiles(self) -> None:
        self.write_input(
            facts={
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "vite-react",
            },
            profiles=["node-npm", "vite-react"],
        )

        result = self.run_initialize()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"],
            ["common", "documentation", "node-npm", "vite-react"],
        )

    def test_explicit_selection_cannot_bypass_applicability(self) -> None:
        facts = {
            "ecosystem": "node",
            "package-manager": "npm",
            "project-kind": "package",
            "framework": "vite-react",
        }
        for profiles, diagnostic in (
            ([], "non-empty unique list"),
            (["spring-boot"], "do not match the supplied facts"),
        ):
            with self.subTest(profiles=profiles):
                self.write_input(facts=facts, profiles=profiles)

                result = self.run_initialize("--write")

                self.assertEqual(result.returncode, 2)
                self.assertIn(diagnostic, result.stderr)
                self.assertFalse(self.destination.exists())

    def test_local_fragment_declarations_are_validated_without_existing_content(
        self,
    ) -> None:
        local_fragment = ".repository-standards/gitignore.local"
        self.write_input(
            **{"local-fragments": {".gitignore": [local_fragment]}}
        )

        preview = self.run_initialize()

        self.assertEqual(preview.returncode, 1, preview.stderr)
        self.assertEqual(
            json.loads(preview.stdout)["local-fragments"],
            {".gitignore": [local_fragment]},
        )
        self.assertFalse(self.destination.exists())

        written = self.run_initialize("--write")

        self.assertEqual(written.returncode, 0, written.stderr)
        manifest = json.loads(
            (self.destination / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["local-fragments"], {".gitignore": [local_fragment]}
        )
        self.assertFalse((self.destination / local_fragment).exists())

    def test_collisions_and_incompatible_releases_leave_no_partial_manifest(self) -> None:
        self.write_input(**{"standards-release": "99.0.0"})

        incompatible = self.run_initialize("--write")

        self.assertEqual(incompatible.returncode, 2)
        self.assertIn("selected release checkout declares", incompatible.stderr)
        self.assertFalse(self.destination.exists())

        self.write_input()
        self.destination.mkdir()
        existing = self.destination / "existing.txt"
        existing.write_text("keep\n", encoding="utf-8")

        collision = self.run_initialize("--write")

        self.assertEqual(collision.returncode, 2)
        self.assertIn("destination is not empty", collision.stderr)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse(
            (self.destination / ".repository-standards.json").exists()
        )

    def test_symlinked_destination_ancestor_is_rejected_before_write(self) -> None:
        self.write_input()
        actual_parent = self.directory / "actual"
        actual_parent.mkdir()
        linked_parent = self.directory / "linked"
        linked_parent.symlink_to(actual_parent, target_is_directory=True)
        self.destination = linked_parent / "example"

        result = self.run_initialize("--write")

        self.assertEqual(result.returncode, 2)
        self.assertIn("traverses a symbolic link", result.stderr)
        self.assertFalse((actual_parent / "example").exists())


if __name__ == "__main__":
    unittest.main()
