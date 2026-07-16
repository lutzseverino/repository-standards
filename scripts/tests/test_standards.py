from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.standards import (  # noqa: E402
    Source,
    StandardsError,
    _render_template,
    build_plan,
    inspect,
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

    def base_manifest(self) -> dict:
        return {
            "standards-version": 1,
            "standards-release": "1.0.0",
            "profiles": ["common", "node-npm", "vite-react"],
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
        manifest["profiles"] = ["common", "node-protocol"]
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
