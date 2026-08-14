from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.standards import (  # noqa: E402
    Source,
    StandardsError,
    _render_template,
    audit_main,
    build_plan,
    collect_required_labels,
    collect_sources,
    inspect,
    inspect_boundaries,
    load_manifest,
    load_profiles,
    standards_root,
    sync_main,
    write,
)


class StandardsTests(unittest.TestCase):
    def create_repository(self, manifest: dict) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        (repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return temporary, repository

    def write_file(self, repository: Path, relative_path: str, content: str) -> None:
        target = repository / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def base_manifest(self) -> dict:
        return {
            "standards-version": 4,
            "standards-release": (standards_root() / "VERSION").read_text(
                encoding="utf-8"
            ).strip(),
            "profiles": ["common", "documentation", "node-npm", "vite-react"],
            "boundaries": [
                {
                    "path": ".",
                    "type": "repository",
                    "title": "Test Repository",
                }
            ],
            "dependency-updates": [
                {
                    "ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": "weekly",
                },
                {
                    "ecosystem": "npm",
                    "directory": "/",
                    "schedule": "weekly",
                },
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
            "repository-owned": [
                "README.md",
                "src/**",
                ".github/workflows/ci.yml",
                ".github/workflows/release.yml",
            ],
        }

    def test_sync_then_audit_is_clean(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        _, manifest = load_manifest(repository)
        plan = build_plan(standards_root(), repository, manifest)
        initial = inspect(repository, plan)
        self.assertTrue(initial)
        self.assertTrue(
            all(result.status in {"missing", "ok"} for result in initial)
        )
        changed = [result for result in initial if result.status != "ok"]
        self.assertTrue(changed)

        self.assertEqual(write(repository, initial), len(changed))
        final = inspect(repository, plan)
        self.assertTrue(all(result.status == "ok" for result in final))

    def test_common_profile_sets_the_default_response_language(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync_main(["--write", str(repository)]), 0)

        agents = " ".join(
            (repository / "AGENTS.md").read_text(encoding="utf-8").split()
        )
        self.assertIn(
            "Respond in English regardless of the language used to address you.",
            agents,
        )
        self.assertIn(
            "Use another language when explicitly requested or when the content "
            "itself requires it",
            agents,
        )

    def test_common_profile_installs_the_official_matt_pocock_skill_bundle(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        expected_skills = (
            "ask-matt",
            "code-review",
            "codebase-design",
            "diagnosing-bugs",
            "domain-modeling",
            "grill-me",
            "grill-with-docs",
            "grilling",
            "handoff",
            "implement",
            "improve-codebase-architecture",
            "prototype",
            "research",
            "resolving-merge-conflicts",
            "setup-matt-pocock-skills",
            "tdd",
            "teach",
            "to-questionnaire",
            "to-spec",
            "to-tickets",
            "triage",
            "wait-what",
            "wayfinder",
            "wizard",
            "writing-for-agents",
        )

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync_main(["--write", str(repository)]), 0)

        installed_skills = tuple(
            sorted(
                path.parent.name
                for path in (repository / ".agents/skills").glob("*/SKILL.md")
            )
        )
        self.assertEqual(installed_skills, expected_skills)

        inventory = json.loads(
            (repository / ".agents/standard-skills.json").read_text(encoding="utf-8")
        )
        self.assertEqual(inventory["version"], 1)
        self.assertEqual(len(inventory["bundles"]), 1)
        bundle = inventory["bundles"][0]
        self.assertEqual(bundle["name"], "mattpocock-skills")
        self.assertEqual(bundle["source"], "https://github.com/mattpocock/skills")
        self.assertEqual(
            bundle["revision"],
            "84fdeffd12f2ee307994d1eb6feb48173b6e0502",
        )
        self.assertEqual(tuple(sorted(bundle["skills"])), expected_skills)
        license_text = (
            repository / ".agents/licenses/mattpocock-skills.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 Matt Pocock", license_text)

    def test_audit_reports_standard_skill_drift(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync_main(["--write", str(repository)]), 0)
        skill = repository / ".agents/skills/implement/SKILL.md"
        skill.write_text("changed locally\n", encoding="utf-8")

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(audit_main([str(repository), "--json"]), 1)
        payload = json.loads(output.getvalue())
        result = next(
            item
            for item in payload["files"]
            if item["path"] == ".agents/skills/implement/SKILL.md"
        )
        self.assertEqual(result["status"], "drift")

    def test_repository_local_skills_can_coexist_with_the_standard_bundle(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync_main(["--write", str(repository)]), 0)
        local_skill = repository / ".agents/skills/local-only/SKILL.md"
        local_skill.parent.mkdir()
        local_skill.write_text("# Local skill\n", encoding="utf-8")

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(sync_main([str(repository)]), 0)
        self.assertTrue(local_skill.is_file())

    def test_local_gitignore_fragment_is_preserved(self) -> None:
        manifest = self.base_manifest()
        manifest["local-fragments"] = {
            ".gitignore": [".repository-standards/gitignore.local"]
        }
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        local = repository / ".repository-standards/gitignore.local"
        local.parent.mkdir()
        local.write_text("# Product output\nproduct-output/\n", encoding="utf-8")

        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        gitignore = next(item for item in plan if item.target == ".gitignore")
        rendered = gitignore.content.decode("utf-8")
        self.assertIn("node_modules/", rendered)
        self.assertIn("dist/", rendered)
        self.assertIn("product-output/", rendered)

    def test_repository_owned_target_is_rejected(self) -> None:
        manifest = self.base_manifest()
        manifest["repository-owned"].append(".gitignore")
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        with self.assertRaisesRegex(StandardsError, "conflicts with repository-owned"):
            build_plan(standards_root(), repository, loaded)

    def test_managed_absence_is_audited_and_removed(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        retired = repository / ".github/pull_request_template.md"
        retired.parent.mkdir(parents=True)
        retired.write_text("retired policy\n", encoding="utf-8")

        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        initial = inspect(repository, plan)
        result = next(
            item
            for item in initial
            if item.target == ".github/pull_request_template.md"
        )
        self.assertEqual(result.status, "present")
        self.assertEqual(result.mode, "absent")

        self.assertEqual(write(repository, [result]), 1)
        self.assertFalse(retired.exists())
        final = inspect(repository, plan)
        result = next(
            item
            for item in final
            if item.target == ".github/pull_request_template.md"
        )
        self.assertEqual(result.status, "ok")

    def test_sync_preview_names_every_managed_deletion(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        write(repository, inspect(repository, plan))
        retired = repository / ".github/pull_request_template.md"

        cases = (
            (b"", False),
            (b"retired policy\n", True),
            (b"\xff", False),
        )
        for content, has_diff in cases:
            with self.subTest(content=content):
                retired.write_bytes(content)
                output = StringIO()
                with redirect_stdout(output):
                    exit_code = sync_main([str(repository)])
                preview = output.getvalue()

                self.assertEqual(exit_code, 1)
                self.assertIn(
                    "DELETE   .github/pull_request_template.md\n",
                    preview,
                )
                if has_diff:
                    self.assertIn(
                        "--- a/.github/pull_request_template.md\n",
                        preview,
                    )
                    self.assertIn("-retired policy\n", preview)
                else:
                    self.assertNotIn(
                        "--- a/.github/pull_request_template.md\n",
                        preview,
                    )

    def test_sync_preview_reports_blocked_managed_absence(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        write(repository, inspect(repository, plan))
        retired_file = repository / ".github/pull_request_template.md"
        blocked_path = repository / ".github/workflows/pr-policy.yml"
        retired_file.touch()
        blocked_path.mkdir(parents=True)

        output = StringIO()
        with redirect_stdout(output):
            exit_code = sync_main([str(repository)])
        preview = output.getvalue()

        self.assertEqual(exit_code, 2)
        self.assertIn(
            "DELETE   .github/pull_request_template.md\n",
            preview,
        )
        self.assertIn(
            "BLOCKED  .github/workflows/pr-policy.yml "
            "(managed absence requires a regular file)\n",
            preview,
        )
        self.assertIn(
            "Preview: 1 managed file(s) would change; "
            "1 blocked path(s) require attention.\n",
            preview,
        )
        self.assertTrue(blocked_path.is_dir())

        retired_file.unlink()
        output = StringIO()
        with redirect_stdout(output):
            exit_code = sync_main([str(repository)])
        blocked_preview = output.getvalue()

        self.assertEqual(exit_code, 2)
        self.assertIn(
            "Preview blocked: 1 managed path(s) require attention.\n",
            blocked_preview,
        )
        self.assertNotIn("would change", blocked_preview)

    def test_mismatched_standards_release_is_rejected(self) -> None:
        manifest = self.base_manifest()
        manifest["standards-release"] = "9.9.9"
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        with self.assertRaisesRegex(StandardsError, "check out tag v9.9.9"):
            build_plan(standards_root(), repository, loaded)

    def test_profile_inheritance_is_resolved_once(self) -> None:
        manifest = self.base_manifest()
        manifest["profiles"] = ["common", "documentation", "node-protocol"]
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        gitignore = next(item for item in plan if item.target == ".gitignore")
        rendered = gitignore.content.decode("utf-8")
        self.assertEqual(rendered.count("node_modules/"), 1)
        self.assertIn("# Protocol package outputs", rendered)

    def test_tree_profile_rejects_a_symlinked_source_directory(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        profile = Path(temporary.name)
        source = profile / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
        (profile / "linked-source").symlink_to(source, target_is_directory=True)
        profiles = [
            (
                "agent-skills",
                {
                    "files": [
                        {
                            "mode": "tree",
                            "source": "linked-source",
                            "target": ".agents/skills",
                        }
                    ]
                },
                profile,
            )
        ]

        with self.assertRaisesRegex(StandardsError, "tree source must not be a symlink"):
            collect_sources(profiles)

    def test_common_profile_declares_the_canonical_required_labels(self) -> None:
        profiles = load_profiles(standards_root(), ["common"])

        self.assertEqual(
            collect_required_labels(profiles),
            (
                "bug",
                "enhancement",
                "needs-info",
                "needs-triage",
                "ready-for-agent",
                "ready-for-human",
                "wontfix",
            ),
        )

    def test_managed_target_symlink_is_rejected(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        outside = repository.parent / f"{repository.name}-outside"
        outside.write_text("do not change", encoding="utf-8")
        self.addCleanup(outside.unlink)
        (repository / ".editorconfig").symlink_to(outside)
        with self.assertRaisesRegex(StandardsError, "symlink"):
            inspect(repository, plan)

    def test_documentation_profile_manages_exactly_seven_templates(self) -> None:
        manifest = self.base_manifest()
        manifest["profiles"] = ["common", "documentation"]
        manifest["repository-owned"] = ["docs/README.md", "docs/tutorials/**"]
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        documentation_targets = [
            item.target
            for item in plan
            if item.target.startswith("docs/_templates/") and item.mode != "absent"
        ]
        self.assertEqual(len(documentation_targets), 7)
        retired = next(
            item
            for item in plan
            if item.target == "docs/_templates/decision.template.md"
        )
        self.assertEqual(retired.mode, "absent")

    def test_dependabot_is_rendered_from_structured_manifest_updates(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        _, manifest = load_manifest(repository)
        plan = build_plan(standards_root(), repository, manifest)
        dependabot = next(
            item for item in plan if item.target == ".github/dependabot.yml"
        )
        rendered = dependabot.content.decode("utf-8")
        self.assertIn("package-ecosystem: github-actions", rendered)
        self.assertIn("package-ecosystem: npm", rendered)
        self.assertEqual(rendered.count("directory: /"), 2)

    def test_dependency_updates_reject_missing_and_unsafe_declarations(self) -> None:
        missing = self.base_manifest()
        del missing["dependency-updates"]
        temporary, repository = self.create_repository(missing)
        try:
            with self.assertRaisesRegex(
                StandardsError, "dependency-updates must be a non-empty list"
            ):
                load_manifest(repository)
        finally:
            temporary.cleanup()

        unsafe = self.base_manifest()
        unsafe["dependency-updates"][0]["directory"] = "/../outside"
        temporary, repository = self.create_repository(unsafe)
        try:
            with self.assertRaisesRegex(StandardsError, "must not contain dot segments"):
                load_manifest(repository)
        finally:
            temporary.cleanup()

    def test_github_contract_requires_an_explicit_ruleset_decision(self) -> None:
        manifest = self.base_manifest()
        manifest["github"] = {
            "repository": "owner/example",
            "default-branch": "main",
            "settings": {
                "delete-branch-on-merge": True,
                "allow-squash-merge": True,
                "allow-merge-commit": False,
                "allow-rebase-merge": False,
            },
        }
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(
            StandardsError,
            "github must define repository, default-branch, settings, and ruleset",
        ):
            load_manifest(repository)

    def test_manifest_requires_common_profile_and_github_contract(self) -> None:
        missing_common = self.base_manifest()
        missing_common["profiles"].remove("common")
        temporary, repository = self.create_repository(missing_common)
        try:
            with self.assertRaisesRegex(
                StandardsError, "requires the common profile"
            ):
                load_manifest(repository)
        finally:
            temporary.cleanup()

        missing_github = self.base_manifest()
        del missing_github["github"]
        temporary, repository = self.create_repository(missing_github)
        try:
            with self.assertRaisesRegex(
                StandardsError, "github contract is required"
            ):
                load_manifest(repository)
        finally:
            temporary.cleanup()

    def test_boundary_manifest_contract_is_enforced(self) -> None:
        invalid_manifests: list[tuple[str, dict, str]] = []

        missing_boundaries = self.base_manifest()
        del missing_boundaries["boundaries"]
        invalid_manifests.append(
            ("missing boundaries", missing_boundaries, "boundaries must be a non-empty list")
        )

        missing_documentation = self.base_manifest()
        missing_documentation["profiles"].remove("documentation")
        invalid_manifests.append(
            ("missing documentation", missing_documentation, "require the documentation profile")
        )

        wrong_repository = self.base_manifest()
        wrong_repository["boundaries"] = [
            {"path": "workspace", "type": "repository", "title": "Workspace"}
        ]
        invalid_manifests.append(
            ("wrong repository path", wrong_repository, "repository boundary at '.'")
        )

        duplicate_paths = self.base_manifest()
        duplicate_paths["boundaries"].append(
            {"path": ".", "type": "collection", "title": "Duplicate"}
        )
        invalid_manifests.append(
            ("duplicate path", duplicate_paths, "boundary paths must be unique")
        )

        non_normalized = self.base_manifest()
        non_normalized["boundaries"].append(
            {"path": "services/", "type": "collection", "title": "Services"}
        )
        invalid_manifests.append(
            ("non-normalized path", non_normalized, "normalized concrete directory")
        )

        for label, manifest, message in invalid_manifests:
            with self.subTest(label=label):
                temporary, repository = self.create_repository(manifest)
                try:
                    with self.assertRaisesRegex(StandardsError, message):
                        load_manifest(repository)
                finally:
                    temporary.cleanup()

    def test_repository_collection_and_project_boundaries_pass(self) -> None:
        manifest = self.base_manifest()
        manifest["boundaries"].extend(
            [
                {"path": "services", "type": "collection", "title": "Services"},
                {
                    "path": "services/example",
                    "type": "project",
                    "title": "Example Service",
                },
            ]
        )
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "## Documentation\n\nSee [the documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n\nRoot docs.\n")
        self.write_file(repository, "services/README.md", "# Services\n\nService index.\n")
        self.write_file(
            repository,
            "services/example/README.md",
            "# Example Service\n\nSee [documentation](docs/README.md).\n",
        )
        self.write_file(
            repository,
            "services/example/docs/README.md",
            "# Documentation\n\nService docs.\n",
        )

        _, loaded = load_manifest(repository)
        results = inspect_boundaries(repository, loaded["boundaries"])
        self.assertEqual([result.status for result in results], ["ok", "ok", "ok"])
        plan = build_plan(standards_root(), repository, loaded)
        documentation_targets = [
            item.target
            for item in plan
            if "/_templates/" in item.target and item.mode != "absent"
        ]
        self.assertEqual(len(documentation_targets), 7)
        self.assertTrue(
            all(target.startswith("docs/_templates/") for target in documentation_targets)
        )

    def test_boundary_audit_reports_shape_docs_and_nested_template_failures(self) -> None:
        manifest = self.base_manifest()
        manifest["boundaries"].extend(
            [
                {"path": "services", "type": "collection", "title": "Services"},
                {
                    "path": "services/example",
                    "type": "project",
                    "title": "Example Service",
                },
            ]
        )
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Wrong title</h1>\n</div>\n',
        )
        self.write_file(
            repository,
            "docs/README.md",
            "\n# Documentation\n\n# Extra\n\n![CI](https://example.test/badge.svg)\n",
        )
        self.write_file(
            repository,
            "services/README.md",
            '# Wrong\n\n<div align="center">centered</div>\n\n'
            "# Extra\n\n![CI](https://img.shields.io/badge/ci-pass)\n",
        )
        self.write_file(repository, "services/example/README.md", "# Example Service\n")
        self.write_file(
            repository,
            "services/example/docs/README.md",
            "# Documentation\n\nService docs.\n",
        )
        (repository / "services/example/docs/_templates").mkdir(parents=True)

        _, loaded = load_manifest(repository)
        results = inspect_boundaries(repository, loaded["boundaries"])
        messages = "\n".join(
            message for result in results for message in result.messages
        )
        self.assertTrue(all(result.status == "invalid" for result in results))
        self.assertIn("exactly one canonical centered header title", messages)
        self.assertIn("must link to docs/README.md", messages)
        self.assertIn("must begin with '# Documentation'", messages)
        self.assertIn("exactly one Markdown H1: # Documentation", messages)
        self.assertIn("services/README.md must begin with '# Services'", messages)
        self.assertIn("must not contain a centered wrapper", messages)
        self.assertIn("must not contain badges", messages)
        self.assertIn("templates are managed only at docs/_templates", messages)

    def test_empty_documentation_categories_are_rejected(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        self.write_file(repository, "docs/tutorials/README.md", "# Tutorials\n")

        _, loaded = load_manifest(repository)
        result = inspect_boundaries(repository, loaded["boundaries"])[0]
        self.assertEqual(result.status, "invalid")
        self.assertIn(
            "docs/tutorials has no authored content; remove it until needed",
            result.messages,
        )

    def test_empty_adr_category_is_rejected(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        self.write_file(repository, "docs/adr/README.md", "# ADRs\n")

        _, loaded = load_manifest(repository)
        result = inspect_boundaries(repository, loaded["boundaries"])[0]

        self.assertEqual(result.status, "invalid")
        self.assertIn(
            "docs/adr has no authored content; remove it until needed",
            result.messages,
        )

    def test_documentation_category_with_recursive_authored_content_passes(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        self.write_file(repository, "docs/reference/README.md", "# Reference\n")
        self.write_file(
            repository,
            "docs/reference/api/endpoints.md",
            "# Endpoints\n",
        )

        _, loaded = load_manifest(repository)
        result = inspect_boundaries(repository, loaded["boundaries"])[0]
        self.assertEqual(result.status, "ok")

    def test_audit_json_includes_boundaries_and_uses_them_for_exit_status(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        _, manifest = load_manifest(repository)
        plan = build_plan(standards_root(), repository, manifest)
        write(repository, inspect(repository, plan))

        output = StringIO()
        with redirect_stdout(output):
            exit_code = audit_main([str(repository), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["clean"])
        self.assertEqual(payload["boundaries"][0]["status"], "ok")

        self.write_file(repository, "docs/README.md", "# Wrong\n")
        output = StringIO()
        with redirect_stdout(output):
            exit_code = audit_main([str(repository), "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["boundaries"][0]["status"], "invalid")

    def test_repository_owned_changelog_opts_into_structural_audit(self) -> None:
        manifest = self.base_manifest()
        manifest["repository-owned"].append("CHANGELOG.md")
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        self.write_file(repository, "CHANGELOG.md", "# Changes\n")
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        write(repository, inspect(repository, plan))

        output = StringIO()
        with redirect_stdout(output):
            exit_code = audit_main([str(repository), "--json"])
        payload = json.loads(output.getvalue())

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["clean"])
        self.assertEqual(payload["documents"][0]["path"], "CHANGELOG.md")
        self.assertEqual(payload["documents"][0]["status"], "invalid")
        self.assertIn(
            "root '# Changelog' title",
            payload["documents"][0]["messages"][0],
        )

    def test_template_requires_and_renders_variables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.tmpl"
            path.write_text("Hello {{ repository_name }}!\n", encoding="utf-8")
            source = Source("template", path, "GREETING", 0, "test", 0)
            with self.assertRaisesRegex(StandardsError, "missing variables"):
                _render_template(source, {})
            self.assertEqual(
                _render_template(source, {"repository_name": "Cardo"}),
                b"Hello Cardo!\n",
            )


if __name__ == "__main__":
    unittest.main()
