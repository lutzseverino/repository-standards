from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.repository_contract import (  # noqa: E402
    ContractError,
    resolve_repository_contract,
)
from scripts.tests.json_schema_support import validation_errors


class RepositoryContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.standards_root = Path(__file__).resolve().parents[2]

    def test_bundled_examples_match_the_current_release(self) -> None:
        release = (self.standards_root / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        json_example = json.loads(
            (self.standards_root / "examples/repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        yaml_release_lines = [
            line
            for line in (
                self.standards_root / "examples/repository-standards.yml"
            ).read_text(encoding="utf-8").splitlines()
            if line.startswith("standards-release:")
        ]

        self.assertEqual(json_example["standards-release"], release)
        self.assertEqual(yaml_release_lines, [f"standards-release: {release}"])

    def base_manifest(self) -> dict:
        return {
            "standards-version": 5,
            "standards-release": (self.standards_root / "VERSION").read_text(
                encoding="utf-8"
            ).strip(),
            "canonical-validation": {
                "executable": "scripts/validate",
                "arguments": [],
                "working-directory": ".",
            },
            "profiles": ["common", "documentation", "node-protocol"],
            "boundaries": [
                {"path": ".", "type": "repository", "title": "Example"}
            ],
            "dependency-updates": [
                {
                    "ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": "weekly",
                },
                {"ecosystem": "npm", "directory": "/", "schedule": "weekly"},
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
            "variables": {"repository_name": "Example"},
            "local-fragments": {".gitignore": ["local/gitignore"]},
            "repository-owned": ["README.md", "src/**"],
        }

    def create_repository(
        self, manifest: dict
    ) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        (repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        local_fragment = repository / "local/gitignore"
        local_fragment.parent.mkdir(parents=True)
        local_fragment.write_text("coverage/\n", encoding="utf-8")
        return temporary, repository

    def test_resolves_the_complete_normalized_contract(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        contract = resolve_repository_contract(
            repository, standards_root=self.standards_root
        )

        self.assertEqual(contract.protocol, 5)
        self.assertEqual(contract.release, "5.0.0")
        self.assertEqual(
            contract.canonical_validation.executable, "scripts/validate"
        )
        self.assertEqual(contract.canonical_validation.arguments, ())
        self.assertEqual(contract.canonical_validation.working_directory, ".")
        self.assertEqual(
            contract.selected_profiles,
            ("common", "documentation", "node-protocol"),
        )
        self.assertEqual(
            tuple(profile.name for profile in contract.profiles),
            (
                "agent-skills",
                "repository-lifecycle-skills",
                "common",
                "documentation",
                "node-npm",
                "node-protocol",
            ),
        )
        applicability = {
            profile.name: profile.applicability for profile in contract.profiles
        }
        self.assertTrue(
            all(
                applicability[name] is None
                for name in (
                    "agent-skills",
                    "repository-lifecycle-skills",
                    "common",
                    "documentation",
                )
            )
        )
        self.assertEqual(
            dict(applicability["node-npm"] or ()),
            {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "package",
            },
        )
        self.assertEqual(
            dict(applicability["node-protocol"] or ()),
            {
                "ecosystem": "node",
                "package-manager": "npm",
                "project-kind": "protocol",
            },
        )
        self.assertIn(".gitignore", contract.managed_paths)
        self.assertIn(
            ".github/pull_request_template.md", contract.managed_absences
        )
        self.assertEqual(contract.repository_owned, ("README.md", "src/**"))
        self.assertEqual(contract.variables, (("repository_name", "Example"),))
        self.assertEqual(contract.local_fragments, ((".gitignore", ("local/gitignore",)),))
        self.assertIn("ready-for-agent", contract.required_labels)
        self.assertEqual(contract.dependency_updates[1].ecosystem, "npm")
        self.assertEqual(contract.boundaries[0].title, "Example")
        self.assertEqual(contract.github.repository, "owner/example")
        self.assertEqual(contract.github.default_branch, "main")
        self.assertEqual(
            contract.github.settings.squash_merge_commit_title, "PR_TITLE"
        )
        self.assertEqual(
            contract.github.settings.squash_merge_commit_message, "PR_BODY"
        )
        self.assertTrue(contract.github.features.issues)
        self.assertFalse(contract.github.features.projects)
        self.assertFalse(contract.github.features.wiki)

    def test_normalizes_explicit_repository_feature_rules(self) -> None:
        manifest = self.base_manifest()
        manifest["github"]["features"] = {
            "issues": True,
            "projects": True,
            "wiki": False,
        }
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)

        contract = resolve_repository_contract(
            repository, standards_root=self.standards_root
        )

        self.assertTrue(contract.github.features.issues)
        self.assertTrue(contract.github.features.projects)
        self.assertFalse(contract.github.features.wiki)

    def test_rejects_contract_errors_through_the_high_level_interface(self) -> None:
        cases: list[tuple[str, dict, str]] = []

        unsupported = self.base_manifest()
        unsupported["standards-version"] = 999
        cases.append(("unsupported protocol", unsupported, "standards-version must be 5"))

        duplicate = self.base_manifest()
        duplicate["profiles"].append("common")
        cases.append(("duplicate profiles", duplicate, "must not contain duplicates"))

        missing = self.base_manifest()
        del missing["github"]
        cases.append(("missing field", missing, "github contract is required"))

        missing_validation_executable = self.base_manifest()
        del missing_validation_executable["canonical-validation"]["executable"]
        cases.append(
            (
                "missing validation executable",
                missing_validation_executable,
                "canonical-validation must define executable and arguments",
            )
        )

        unsafe_validation_directory = self.base_manifest()
        unsafe_validation_directory["canonical-validation"][
            "working-directory"
        ] = "../outside"
        cases.append(
            (
                "unsafe validation working directory",
                unsafe_validation_directory,
                "canonical-validation.working-directory must stay within the repository",
            )
        )

        unknown = self.base_manifest()
        unknown["unexpected"] = True
        cases.append(("unknown field", unknown, "unknown manifest fields"))

        unsafe = self.base_manifest()
        unsafe["repository-owned"].append("../outside")
        cases.append(("unsafe ownership", unsafe, "must stay within the repository"))

        missing_mandatory = self.base_manifest()
        missing_mandatory["profiles"].remove("common")
        cases.append(("mandatory profile", missing_mandatory, "requires the common profile"))

        for label, manifest, diagnostic in cases:
            with self.subTest(label=label):
                temporary, repository = self.create_repository(manifest)
                try:
                    with self.assertRaisesRegex(ContractError, diagnostic):
                        resolve_repository_contract(
                            repository, standards_root=self.standards_root
                        )
                finally:
                    temporary.cleanup()

    def test_profile_applicability_is_validated_and_normalized_in_resolved_order(
        self,
    ) -> None:
        standards_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(standards_temporary.cleanup)
        custom_root = Path(standards_temporary.name)
        (custom_root / "VERSION").write_text("5.0.0\n", encoding="utf-8")
        for name, applicability in (
            ("common", {"ecosystem": "baseline"}),
            ("documentation", None),
        ):
            profile_dir = custom_root / "profiles" / name
            profile_dir.mkdir(parents=True)
            profile = {
                "name": name,
                "description": f"{name} profile",
                "extends": [],
                "files": [],
            }
            if applicability is not None:
                profile["applicability"] = applicability
            (profile_dir / "profile.json").write_text(
                json.dumps(profile), encoding="utf-8"
            )

        manifest = self.base_manifest()
        manifest["profiles"] = ["common", "documentation"]
        manifest["local-fragments"] = {}
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)

        contract = resolve_repository_contract(
            repository, standards_root=custom_root
        )
        self.assertEqual(
            tuple((profile.name, profile.applicability) for profile in contract.profiles),
            (
                ("common", (("ecosystem", "baseline"),)),
                ("documentation", None),
            ),
        )

        common_profile = custom_root / "profiles/common/profile.json"
        invalid_profile = json.loads(common_profile.read_text(encoding="utf-8"))
        invalid_profile["applicability"] = ["baseline"]
        common_profile.write_text(json.dumps(invalid_profile), encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "applicability must be an object"):
            resolve_repository_contract(repository, standards_root=custom_root)

    def test_json_schema_and_runtime_validation_have_representative_parity(self) -> None:
        schema = json.loads(
            (self.standards_root / "schema/repository-standards.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cases: list[tuple[str, dict, bool]] = []
        cases.append(("valid", self.base_manifest(), True))

        validation_with_literal_arguments = self.base_manifest()
        validation_with_literal_arguments["canonical-validation"] = {
            "executable": "tools/validate checks",
            "arguments": ["argument with spaces", "$(touch sentinel)", "*.py"],
        }
        cases.append(
            (
                "literal validation arguments and default working directory",
                validation_with_literal_arguments,
                True,
            )
        )

        validation_unknown_field = self.base_manifest()
        validation_unknown_field["canonical-validation"]["shell"] = True
        cases.append(("unknown validation field", validation_unknown_field, False))

        missing_validation_executable = self.base_manifest()
        del missing_validation_executable["canonical-validation"]["executable"]
        cases.append(
            ("missing validation executable", missing_validation_executable, False)
        )

        blank_validation_executable = self.base_manifest()
        blank_validation_executable["canonical-validation"]["executable"] = "   "
        cases.append(("blank validation executable", blank_validation_executable, False))

        empty_validation_arguments = self.base_manifest()
        empty_validation_arguments["canonical-validation"]["arguments"] = []
        cases.append(("empty validation argument sequence", empty_validation_arguments, True))

        empty_validation_argument = self.base_manifest()
        empty_validation_argument["canonical-validation"]["arguments"] = [""]
        cases.append(("empty validation argument", empty_validation_argument, False))

        malformed_validation_arguments = self.base_manifest()
        malformed_validation_arguments["canonical-validation"]["arguments"] = [1]
        cases.append(
            ("malformed validation arguments", malformed_validation_arguments, False)
        )

        nul_validation_argument = self.base_manifest()
        nul_validation_argument["canonical-validation"]["arguments"] = ["bad\0arg"]
        cases.append(("nul validation argument", nul_validation_argument, False))

        unsafe_validation_directory = self.base_manifest()
        unsafe_validation_directory["canonical-validation"][
            "working-directory"
        ] = "../outside"
        cases.append(("unsafe validation directory", unsafe_validation_directory, False))

        backslash_validation_directory = self.base_manifest()
        backslash_validation_directory["canonical-validation"][
            "working-directory"
        ] = "..\\outside"
        cases.append(
            ("backslash validation directory", backslash_validation_directory, False)
        )

        nul_validation_directory = self.base_manifest()
        nul_validation_directory["canonical-validation"][
            "working-directory"
        ] = "bad\0directory"
        cases.append(("nul validation directory", nul_validation_directory, False))

        unsupported = self.base_manifest()
        unsupported["standards-version"] = 999
        cases.append(("unsupported protocol", unsupported, False))

        duplicate_profiles = self.base_manifest()
        duplicate_profiles["profiles"].append("common")
        cases.append(("duplicate profiles", duplicate_profiles, False))

        duplicate_owned = self.base_manifest()
        duplicate_owned["repository-owned"].append("README.md")
        cases.append(("duplicate ownership", duplicate_owned, False))

        duplicate_fragments = self.base_manifest()
        duplicate_fragments["local-fragments"][".gitignore"].append("local/gitignore")
        cases.append(("duplicate local fragments", duplicate_fragments, False))

        duplicate_repository = self.base_manifest()
        duplicate_repository["boundaries"].append(
            {"path": ".", "type": "repository", "title": "Another title"}
        )
        cases.append(("duplicate repository boundary", duplicate_repository, False))

        duplicate_boundary = self.base_manifest()
        duplicate_boundary["boundaries"].append(
            {"path": ".", "type": "repository", "title": "Example"}
        )
        cases.append(("duplicate boundary declaration", duplicate_boundary, False))

        duplicate_update = self.base_manifest()
        duplicate_update["dependency-updates"].append(
            {"ecosystem": "npm", "directory": "/", "schedule": "weekly"}
        )
        cases.append(("duplicate dependency declaration", duplicate_update, False))

        distinct_boundary = self.base_manifest()
        distinct_boundary["boundaries"].extend(
            [
                {"path": "services", "type": "collection", "title": "Services"},
                {
                    "path": "services",
                    "type": "collection",
                    "title": "Other services",
                },
            ]
        )
        cases.append(("distinct boundary declarations", distinct_boundary, True))

        distinct_root_boundaries = self.base_manifest()
        distinct_root_boundaries["boundaries"].insert(
            0,
            {"path": ".", "type": "collection", "title": "Root collection"},
        )
        cases.append(
            ("distinct root boundary declarations", distinct_root_boundaries, True)
        )

        distinct_update = self.base_manifest()
        distinct_update["dependency-updates"].append(
            {"ecosystem": "npm", "directory": "/", "schedule": "daily"}
        )
        cases.append(("distinct dependency declarations", distinct_update, True))

        explicit_features = self.base_manifest()
        explicit_features["github"]["features"] = {
            "issues": True,
            "projects": False,
            "wiki": True,
        }
        cases.append(("explicit repository features", explicit_features, True))

        invalid_features = self.base_manifest()
        invalid_features["github"]["features"] = {
            "issues": True,
            "projects": "disabled",
            "wiki": False,
        }
        cases.append(("invalid repository features", invalid_features, False))

        disabled_issues = self.base_manifest()
        disabled_issues["github"]["features"] = {
            "issues": False,
            "projects": False,
            "wiki": False,
        }
        cases.append(("disabled issues", disabled_issues, False))

        explicit_squash_format = self.base_manifest()
        explicit_squash_format["github"]["settings"].update(
            {
                "squash-merge-commit-title": "COMMIT_OR_PR_TITLE",
                "squash-merge-commit-message": "COMMIT_MESSAGES",
            }
        )
        cases.append(("explicit squash format", explicit_squash_format, True))

        incomplete_squash_format = self.base_manifest()
        incomplete_squash_format["github"]["settings"][
            "squash-merge-commit-title"
        ] = "PR_TITLE"
        cases.append(("one explicit squash format", incomplete_squash_format, True))

        missing = self.base_manifest()
        del missing["dependency-updates"]
        cases.append(("missing field", missing, False))

        unknown = self.base_manifest()
        unknown["github"]["unknown"] = True
        cases.append(("unknown nested field", unknown, False))

        unsafe = self.base_manifest()
        unsafe["repository-owned"].append("../outside")
        cases.append(("unsafe path", unsafe, False))

        missing_common = self.base_manifest()
        missing_common["profiles"].remove("common")
        cases.append(("mandatory profile", missing_common, False))

        for label, manifest, accepted in cases:
            with self.subTest(label=label):
                schema_accepted = not validation_errors(manifest, schema)
                temporary, repository = self.create_repository(manifest)
                try:
                    try:
                        resolve_repository_contract(
                            repository, standards_root=self.standards_root
                        )
                    except ContractError:
                        runtime_accepted = False
                    else:
                        runtime_accepted = True
                finally:
                    temporary.cleanup()
                self.assertEqual(schema_accepted, accepted)
                self.assertEqual(runtime_accepted, accepted)


if __name__ == "__main__":
    unittest.main()
