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
    inspect,
    inspect_boundaries,
    load_manifest,
    standards_root,
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
            "standards-version": 2,
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
        self.assertTrue(all(result.status == "missing" for result in initial))

        self.assertEqual(write(repository, initial), len(initial))
        final = inspect(repository, plan)
        self.assertTrue(all(result.status == "ok" for result in final))

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
        manifest["profiles"] = ["documentation"]
        manifest["repository-owned"] = ["docs/README.md", "docs/tutorials/**"]
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        _, loaded = load_manifest(repository)
        plan = build_plan(standards_root(), repository, loaded)
        self.assertEqual(len(plan), 7)
        self.assertTrue(
            all(item.target.startswith("docs/_templates/") for item in plan)
        )

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
            item.target for item in plan if "/_templates/" in item.target
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
