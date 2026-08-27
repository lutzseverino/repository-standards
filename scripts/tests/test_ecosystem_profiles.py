from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STANDARDS = ROOT / "scripts/standards"


class EcosystemProfilePublicSeamTests(unittest.TestCase):
    def test_every_selectable_profile_owns_environment_behavior(self) -> None:
        selectable: list[str] = []
        forbidden_product_targets = {
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "pom.xml",
            ".github/workflows/ci.yml",
        }
        for profile_path in sorted((ROOT / "profiles").glob("*/profile.json")):
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            if "applicability" not in profile:
                continue
            selectable.append(profile["name"])
            self.assertTrue(profile["applicability"], profile_path)
            self.assertTrue(
                profile.get("files")
                or profile.get("github", {}).get("required-labels"),
                profile_path,
            )
            targets = {item["target"] for item in profile.get("files", [])}
            self.assertTrue(targets.isdisjoint(forbidden_product_targets), profile_path)
            guidance = (profile_path.parent / "README.md").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                "guidance is advisory and is not assessed for standards conformance",
                " ".join(guidance.split()).casefold(),
                profile_path,
            )

        self.assertEqual(
            selectable,
            [
                "codex-skill",
                "node-npm",
                "node-protocol",
                "paper-plugin",
                "pnpm-workspace",
                "spring-boot",
                "tauri",
                "vite-react",
            ],
        )

    def build_initial_contract(
        self,
        facts: dict[str, object],
        *,
        repository_owned: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            contract_input = Path(directory) / "initialization.json"
            initialization = {
                "standards-release": (ROOT / "VERSION")
                .read_text(encoding="utf-8")
                .strip(),
                "repository": "owner/example",
                "title": "Example",
                "canonical-validation": {
                    "executable": "scripts/validate",
                    "arguments": [],
                    "working-directory": ".",
                },
                "facts": facts,
            }
            if repository_owned is not None:
                initialization["repository-owned"] = repository_owned
            contract_input.write_text(
                json.dumps(initialization),
                encoding="utf-8",
            )
            return subprocess.run(
                [str(STANDARDS), "create", "--contract-input", str(contract_input)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_initial_contract_supports_no_applicable_profiles(self) -> None:
        result = self.build_initial_contract({"ecosystem": "elixir"})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"],
            ["common", "documentation"],
        )

    def test_initial_contract_supports_one_applicable_profile(self) -> None:
        result = self.build_initial_contract(
            {"ecosystem": "codex", "project-kind": "skill"}
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"],
            ["common", "documentation", "codex-skill"],
        )

    def write_custom_release(
        self, release: Path, profile: dict[str, object]
    ) -> None:
        shutil.copytree(ROOT / "scripts", release / "scripts")
        (release / "VERSION").write_text("5.0.0\n", encoding="utf-8")
        profiles = {
            "common": {
                "name": "common",
                "description": "Mandatory environment",
                "extends": [],
                "files": [],
            },
            "documentation": {
                "name": "documentation",
                "description": "Mandatory documentation environment",
                "extends": [],
                "files": [],
            },
            str(profile["name"]): profile,
        }
        for name, definition in profiles.items():
            profile_directory = release / "profiles" / name
            profile_directory.mkdir(parents=True)
            (profile_directory / "profile.json").write_text(
                json.dumps(definition), encoding="utf-8"
            )

    def build_custom_initial_contract(
        self, profile: dict[str, object], facts: dict[str, object]
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            self.write_custom_release(release, profile)
            contract_input = Path(directory) / "initialization.json"
            contract_input.write_text(
                json.dumps(
                    {
                        "standards-release": "5.0.0",
                        "repository": "owner/example",
                        "title": "Example",
                        "canonical-validation": {
                            "executable": "scripts/validate",
                            "arguments": [],
                            "working-directory": ".",
                        },
                        "facts": facts,
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    str(release / "scripts/standards"),
                    "create",
                    "--contract-input",
                    str(contract_input),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

    def check_custom_contract(
        self, profile: dict[str, object]
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            release = Path(directory) / "release"
            self.write_custom_release(release, profile)
            repository = Path(directory) / "repository"
            repository.mkdir()
            (repository / ".repository-standards.json").write_text(
                json.dumps(
                    {
                        "standards-version": 5,
                        "standards-release": "5.0.0",
                        "canonical-validation": {
                            "executable": "scripts/validate",
                            "arguments": [],
                            "working-directory": ".",
                        },
                        "profiles": [
                            "common",
                            "documentation",
                            str(profile["name"]),
                        ],
                        "boundaries": [
                            {
                                "path": ".",
                                "type": "repository",
                                "title": "Example",
                            }
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
                        "repository-owned": [],
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.run(
                [
                    str(release / "scripts/standards"),
                    "check",
                    "--scope",
                    "content",
                    str(repository),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_initial_contract_selects_several_applicable_profiles(self) -> None:
        result = self.build_initial_contract(
            {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "vite-react",
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"],
            ["common", "documentation", "node-npm", "vite-react"],
        )

    def test_initial_contract_composes_profiles_across_ecosystems(self) -> None:
        result = self.build_initial_contract(
            {
                "ecosystem": ["node", "rust"],
                "package-manager": "npm",
                "project-kind": ["package", "desktop-application"],
                "framework": ["vite-react", "tauri"],
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["profiles"],
            [
                "common",
                "documentation",
                "node-npm",
                "tauri",
                "vite-react",
            ],
        )

    def test_guidance_only_profile_is_rejected(self) -> None:
        result = self.build_custom_initial_contract(
            {
                "name": "advice",
                "description": "Advice without an environment effect",
                "extends": [],
                "applicability": {"ecosystem": "advice"},
                "files": [],
            },
            {"ecosystem": "advice"},
        )

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(
            "guidance-only profile 'advice' has no managed or assessed "
            "repository-environment behavior",
            result.stderr,
        )

    def test_existing_contract_rejects_a_guidance_only_profile(self) -> None:
        result = self.check_custom_contract(
            {
                "name": "advice",
                "description": "Advice without an environment effect",
                "extends": [],
                "applicability": {"ecosystem": "advice"},
                "files": [],
            }
        )

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn(
            "selected guidance-only profile 'advice' has no managed or assessed "
            "repository-environment behavior",
            result.stderr,
        )

    def test_product_content_remains_repository_owned(self) -> None:
        product_paths = [
            "package.json",
            "package-lock.json",
            "src/**",
            ".github/workflows/ci.yml",
        ]
        result = self.build_initial_contract(
            {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "vite-react",
            },
            repository_owned=product_paths,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["repository-owned"], product_paths
        )

    def test_profile_behavior_cannot_conflict_with_repository_ownership(self) -> None:
        result = self.build_initial_contract(
            {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
                "framework": "none",
            },
            repository_owned=[".gitignore"],
        )

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("conflicts with repository-owned", result.stderr)

    def test_mandatory_environment_behavior_cannot_be_waived(self) -> None:
        result = self.build_initial_contract(
            {"ecosystem": "elixir"},
            repository_owned=[".editorconfig"],
        )

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("conflicts with repository-owned", result.stderr)


if __name__ == "__main__":
    unittest.main()
