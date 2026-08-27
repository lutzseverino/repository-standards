from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from lib.repository_content import (  # noqa: E402
    Source,
    StandardsError,
    _render_template,
    _collect_sources,
    inspect,
    inspect_boundaries,
    inspect_repository_owned_documents,
    standards_root,
)
from lib.repository_content_reconciliation import (  # noqa: E402
    apply_content_reconciliation,
    calculate_content_reconciliation,
    render_content_reconciliation,
)
from lib.repository_contract import (  # noqa: E402
    ContractError,
    RepositoryContract,
    resolve_repository_contract,
)


class RepositoryContentTests(unittest.TestCase):
    def resolve_contract(self, repository: Path) -> RepositoryContract:
        return resolve_repository_contract(
            repository, standards_root=standards_root()
        )

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

    def apply_content(self, repository: Path) -> int:
        reconciliation = calculate_content_reconciliation(
            self.resolve_contract(repository)
        )
        report = apply_content_reconciliation(reconciliation)
        self.assertTrue(report.succeeded, report.failed)
        return len(report.completed)

    def write_results(self, repository: Path, results) -> int:
        changed = 0
        for result in results:
            if result.status == "ok":
                continue
            target = repository / result.target
            if result.mode == "absent":
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(result.expected)
            changed += 1
        return changed

    def base_manifest(self) -> dict:
        return {
            "standards-version": 5,
            "standards-release": (standards_root() / "VERSION").read_text(
                encoding="utf-8"
            ).strip(),
            "canonical-validation": {
                "executable": "scripts/validate",
                "arguments": [],
                "working-directory": ".",
            },
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

    def test_content_correction_then_inspection_is_clean(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        initial = inspect(repository, content_files)
        self.assertTrue(initial)
        self.assertTrue(
            all(result.status in {"missing", "ok"} for result in initial)
        )
        changed = [result for result in initial if result.status != "ok"]
        self.assertTrue(changed)

        self.assertEqual(self.write_results(repository, initial), len(changed))
        final = inspect(repository, content_files)
        self.assertTrue(all(result.status == "ok" for result in final))

    def test_common_profile_sets_the_default_response_language(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        output = StringIO()
        self.assertGreaterEqual(self.apply_content(repository), 0)

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

    def test_common_profile_installs_session_release_discovery_guidance(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        output = StringIO()
        self.assertGreaterEqual(self.apply_content(repository), 0)

        guidance = """## Standards release discovery

At the start of each agent session, run this check at most once:

```sh
sh .agents/scripts/discover-standards-release.sh
```

Cache that the check was attempted and cache its output for the session. Empty
output means that discovery is unavailable or no newer stable release exists;
it is not evidence that the repository is current. Do not run the check again
during the session.

Only the first substantive final response is eligible for an update notice. If
the cached output is a stable semantic version, immediately before that response
run the following command, replacing `AVAILABLE` with the cached version:

```sh
sh .agents/scripts/discover-standards-release.sh --notice AVAILABLE
```

The notice check rereads only the local manifest and makes no network request.
Append its non-empty output verbatim to the final response. Whether its output is
empty or non-empty, consider the notice handled and do not repeat it in later
responses.
"""
        agents = (repository / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(guidance, agents)
        self.assertTrue(
            (repository / ".agents/scripts/discover-standards-release.sh").is_file()
        )

    def test_common_profile_installs_the_canonical_workflow_skill_closure(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        expected_skills = (
            "code-review",
            "codebase-design",
            "domain-modeling",
            "grill-with-docs",
            "grilling",
            "implement",
            "prototype",
            "research",
            "setup-matt-pocock-skills",
            "tdd",
            "to-spec",
            "to-tickets",
            "triage",
            "wayfinder",
        )
        expected_roots = (
            "grill-with-docs",
            "implement",
            "to-spec",
            "to-tickets",
            "triage",
            "wayfinder",
        )
        expected_dependencies = {
            "code-review": ["setup-matt-pocock-skills"],
            "codebase-design": [],
            "domain-modeling": [],
            "grill-with-docs": ["domain-modeling", "grilling"],
            "grilling": [],
            "implement": ["code-review", "tdd"],
            "prototype": [],
            "research": [],
            "setup-matt-pocock-skills": [],
            "tdd": ["codebase-design"],
            "to-spec": ["setup-matt-pocock-skills"],
            "to-tickets": ["setup-matt-pocock-skills"],
            "triage": [
                "domain-modeling",
                "grilling",
                "setup-matt-pocock-skills",
            ],
            "wayfinder": [
                "domain-modeling",
                "grilling",
                "prototype",
                "research",
                "setup-matt-pocock-skills",
            ],
        }

        output = StringIO()
        self.assertGreaterEqual(self.apply_content(repository), 0)

        bundled_skills = tuple(
            sorted(
                path.parent.name
                for path in (
                    standards_root()
                    / "profiles/agent-skills/files/.agents/skills"
                ).glob("*/SKILL.md")
            )
        )
        self.assertEqual(bundled_skills, expected_skills)
        for skill in expected_skills:
            self.assertTrue(
                (repository / f".agents/skills/{skill}/SKILL.md").is_file()
            )

        inventory = json.loads(
            (repository / ".agents/standard-skills.json").read_text(encoding="utf-8")
        )
        self.assertEqual(inventory["version"], 2)
        self.assertEqual(len(inventory["bundles"]), 1)
        bundle = inventory["bundles"][0]
        self.assertEqual(bundle["name"], "mattpocock-skills")
        self.assertEqual(bundle["source"], "https://github.com/mattpocock/skills")
        self.assertEqual(
            bundle["revision"],
            "84fdeffd12f2ee307994d1eb6feb48173b6e0502",
        )
        self.assertEqual(bundle["upstream-manifest"], ".claude-plugin/plugin.json")
        self.assertEqual(bundle["license"], "MIT")
        self.assertEqual(
            bundle["license-file"],
            ".agents/licenses/mattpocock-skills.txt",
        )
        self.assertEqual(tuple(bundle["workflow-roots"]), expected_roots)
        self.assertEqual(bundle["dependencies"], expected_dependencies)
        self.assertEqual(tuple(sorted(bundle["skills"])), expected_skills)

        closure: set[str] = set()
        frontier = list(bundle["workflow-roots"])
        while frontier:
            skill = frontier.pop()
            if skill in closure:
                continue
            closure.add(skill)
            frontier.extend(bundle["dependencies"][skill])
        self.assertEqual(closure, set(bundle["skills"]))

        upstream_skills = {
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
        }
        bundled_root = (
            standards_root() / "profiles/agent-skills/files/.agents/skills"
        )
        for skill in expected_skills:
            instructions = (bundled_root / skill / "SKILL.md").read_text(
                encoding="utf-8"
            )
            referenced_skills = {
                candidate
                for candidate in upstream_skills
                if re.search(
                    rf"/{re.escape(candidate)}(?![a-z0-9-])",
                    instructions,
                )
                and candidate != skill
            }
            self.assertEqual(
                referenced_skills,
                set(expected_dependencies[skill]),
                skill,
            )
        license_text = (
            repository / ".agents/licenses/mattpocock-skills.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 Matt Pocock", license_text)

    def test_common_profile_installs_the_family_owned_lifecycle_skill_bundle(
        self,
    ) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.assertGreaterEqual(self.apply_content(repository), 0)

        for name, runner_name in (
            ("adopt-standards", "adopt"),
            ("create-repository", "create"),
            ("deliver-change", None),
            ("publish-repository", "publish"),
        ):
            skill = repository / f".agents/skills/{name}/SKILL.md"
            self.assertTrue(skill.is_file())
            if runner_name:
                runner = repository / f".agents/skills/{name}/scripts/{runner_name}"
                self.assertTrue(runner.is_file())
            skill_text = skill.read_text(encoding="utf-8")
            self.assertIn(f"name: {name}", skill_text)
            self.assertIn("disable-model-invocation: true", skill_text)
        inventory = json.loads(
            (
                repository / ".agents/repository-lifecycle-skills.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(inventory["version"], 1)
        self.assertEqual(inventory["bundle"]["name"], "repository-lifecycle-skills")
        self.assertEqual(
            inventory["bundle"]["source"],
            "https://github.com/lutzseverino/repository-standards",
        )
        self.assertEqual(inventory["bundle"]["license"], "MIT")
        self.assertEqual(
            inventory["bundle"]["skills"],
            [
                "adopt-standards",
                "create-repository",
                "deliver-change",
                "publish-repository",
            ],
        )
        license_text = (
            repository / ".agents/licenses/repository-lifecycle-skills.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Copyright (c) 2026 Lutz Severino", license_text)

    def test_common_profile_exposes_canonical_agent_artifacts_to_claude(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.assertGreaterEqual(self.apply_content(repository), 0)

        self.assertEqual(
            (repository / "CLAUDE.md").read_text(encoding="utf-8"),
            "@AGENTS.md\n",
        )
        workflow_inventory = json.loads(
            (repository / ".agents/standard-skills.json").read_text(
                encoding="utf-8"
            )
        )
        lifecycle_inventory = json.loads(
            (repository / ".agents/repository-lifecycle-skills.json").read_text(
                encoding="utf-8"
            )
        )
        canonical_skills = sorted(
            workflow_inventory["bundles"][0]["skills"]
            + lifecycle_inventory["bundle"]["skills"]
        )
        adapter_skills = sorted(
            path.parent.name
            for path in (repository / ".claude/skills").glob("*/SKILL.md")
        )
        self.assertEqual(adapter_skills, canonical_skills)

        for name in canonical_skills:
            canonical = (
                repository / f".agents/skills/{name}/SKILL.md"
            ).read_text(encoding="utf-8")
            adapter = (
                repository / f".claude/skills/{name}/SKILL.md"
            ).read_text(encoding="utf-8")
            canonical_frontmatter = canonical.split("---", 2)[1].strip()
            adapter_frontmatter, adapter_body = adapter.split("---", 2)[1:]
            self.assertEqual(adapter_frontmatter.strip(), canonical_frontmatter)
            self.assertEqual(
                adapter_body.strip(),
                "Read and follow [the canonical Agent Skill]"
                f"(../../../.agents/skills/{name}/SKILL.md). Resolve its relative "
                "references from the canonical skill directory.",
            )

    def test_content_inspection_reports_standard_skill_drift(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")

        self.assertGreaterEqual(self.apply_content(repository), 0)
        skill = repository / ".agents/skills/implement/SKILL.md"
        skill.write_text("changed locally\n", encoding="utf-8")

        results = inspect(
            repository, self.resolve_contract(repository).managed_files
        )
        result = next(
            item
            for item in results
            if item.target == ".agents/skills/implement/SKILL.md"
        )
        self.assertEqual(result.status, "drift")

    def test_repository_local_skills_can_coexist_with_the_standard_bundle(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        self.assertGreaterEqual(self.apply_content(repository), 0)
        local_skill = repository / ".agents/skills/local-only/SKILL.md"
        local_skill.parent.mkdir()
        local_skill.write_text("# Local skill\n", encoding="utf-8")

        reconciliation = calculate_content_reconciliation(
            self.resolve_contract(repository)
        )
        self.assertEqual(reconciliation.changes, ())
        self.assertTrue(local_skill.is_file())

    def test_retired_standard_skills_are_managed_absent_without_removing_local_skills(
        self,
    ) -> None:
        retired_files = {
            ".agents/skills/ask-matt/PHASE-BOUNDARIES.md",
            ".agents/skills/ask-matt/SKILL.md",
            ".agents/skills/ask-matt/agents/openai.yaml",
            ".agents/skills/diagnosing-bugs/SKILL.md",
            ".agents/skills/diagnosing-bugs/agents/openai.yaml",
            ".agents/skills/diagnosing-bugs/scripts/hitl-loop.template.sh",
            ".agents/skills/grill-me/SKILL.md",
            ".agents/skills/grill-me/agents/openai.yaml",
            ".agents/skills/handoff/SKILL.md",
            ".agents/skills/handoff/agents/openai.yaml",
            ".agents/skills/improve-codebase-architecture/HTML-REPORT.md",
            ".agents/skills/improve-codebase-architecture/SKILL.md",
            ".agents/skills/improve-codebase-architecture/agents/openai.yaml",
            ".agents/skills/resolving-merge-conflicts/SKILL.md",
            ".agents/skills/resolving-merge-conflicts/agents/openai.yaml",
            ".agents/skills/teach/GLOSSARY-FORMAT.md",
            ".agents/skills/teach/LEARNING-RECORD-FORMAT.md",
            ".agents/skills/teach/MISSION-FORMAT.md",
            ".agents/skills/teach/RESOURCES-FORMAT.md",
            ".agents/skills/teach/SKILL.md",
            ".agents/skills/teach/agents/openai.yaml",
            ".agents/skills/to-questionnaire/SKILL.md",
            ".agents/skills/to-questionnaire/agents/openai.yaml",
            ".agents/skills/wait-what/SKILL.md",
            ".agents/skills/wait-what/agents/openai.yaml",
            ".agents/skills/wizard/SKILL.md",
            ".agents/skills/wizard/agents/openai.yaml",
            ".agents/skills/wizard/template.sh",
            ".agents/skills/writing-for-agents/SKILL-MECHANICS.md",
            ".agents/skills/writing-for-agents/SKILL.md",
            ".agents/skills/writing-for-agents/agents/openai.yaml",
        }
        profile = json.loads(
            (standards_root() / "profiles/agent-skills/profile.json").read_text(
                encoding="utf-8"
            )
        )
        managed_absences = {
            item["target"]
            for item in profile["files"]
            if item["mode"] == "absent"
        }
        self.assertEqual(managed_absences, retired_files)

        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        for retired in retired_files:
            self.write_file(repository, retired, "retired standard skill content\n")
        local_skill = repository / ".agents/skills/local-only/SKILL.md"
        self.write_file(repository, ".agents/skills/local-only/SKILL.md", "# Local\n")

        self.assertGreaterEqual(self.apply_content(repository), len(retired_files))

        self.assertTrue(all(not (repository / retired).exists() for retired in retired_files))
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

        content_files = self.resolve_contract(repository).managed_files
        gitignore = next(item for item in content_files if item.target == ".gitignore")
        rendered = gitignore.content.decode("utf-8")
        self.assertIn("node_modules/", rendered)
        self.assertIn("dist/", rendered)
        self.assertIn("product-output/", rendered)

    def test_repository_owned_target_is_rejected(self) -> None:
        manifest = self.base_manifest()
        manifest["repository-owned"].append(".gitignore")
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(ContractError, "conflicts with repository-owned"):
            self.resolve_contract(repository)

    def test_managed_absence_is_inspected_and_removed(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        retired = repository / ".github/pull_request_template.md"
        retired.parent.mkdir(parents=True)
        retired.write_text("retired policy\n", encoding="utf-8")

        content_files = self.resolve_contract(repository).managed_files
        initial = inspect(repository, content_files)
        result = next(
            item
            for item in initial
            if item.target == ".github/pull_request_template.md"
        )
        self.assertEqual(result.status, "present")
        self.assertEqual(result.mode, "absent")

        self.assertEqual(self.write_results(repository, [result]), 1)
        self.assertFalse(retired.exists())
        final = inspect(repository, content_files)
        result = next(
            item
            for item in final
            if item.target == ".github/pull_request_template.md"
        )
        self.assertEqual(result.status, "ok")

    def test_content_preview_names_every_managed_deletion(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        self.write_results(repository, inspect(repository, content_files))
        retired = repository / ".github/pull_request_template.md"

        cases = (
            (b"", False),
            (b"retired policy\n", True),
            (b"\xff", False),
        )
        for content, has_diff in cases:
            with self.subTest(content=content):
                retired.write_bytes(content)
                reconciliation = calculate_content_reconciliation(
                    self.resolve_contract(repository)
                )
                preview = render_content_reconciliation(reconciliation)

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

    def test_content_preview_reports_blocked_managed_absence(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        self.write_results(repository, inspect(repository, content_files))
        retired_file = repository / ".github/pull_request_template.md"
        blocked_path = repository / ".github/workflows/pr-policy.yml"
        retired_file.touch()
        blocked_path.mkdir(parents=True)

        reconciliation = calculate_content_reconciliation(
            self.resolve_contract(repository)
        )
        preview = render_content_reconciliation(reconciliation)

        self.assertIn(
            "DELETE   .github/pull_request_template.md\n",
            preview,
        )
        self.assertIn(
            "BLOCKED  .github/workflows/pr-policy.yml "
            "(managed absence requires a regular file)\n",
            preview,
        )
        self.assertTrue(blocked_path.is_dir())

    def test_mismatched_standards_release_is_rejected(self) -> None:
        manifest = self.base_manifest()
        manifest["standards-release"] = "9.9.9"
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(ContractError, "check out tag v9.9.9"):
            self.resolve_contract(repository)

    def test_profile_inheritance_is_resolved_once(self) -> None:
        manifest = self.base_manifest()
        manifest["profiles"] = ["common", "documentation", "node-protocol"]
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        gitignore = next(item for item in content_files if item.target == ".gitignore")
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
            _collect_sources(profiles)

    def test_common_profile_declares_the_canonical_required_labels(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)

        self.assertEqual(
            self.resolve_contract(repository).required_labels,
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
        content_files = self.resolve_contract(repository).managed_files
        outside = repository.parent / f"{repository.name}-outside"
        outside.write_text("do not change", encoding="utf-8")
        self.addCleanup(outside.unlink)
        (repository / ".editorconfig").symlink_to(outside)
        with self.assertRaisesRegex(StandardsError, "symlink"):
            inspect(repository, content_files)

    def test_content_reconciliation_rejects_a_symlinked_managed_target_ancestor(
        self,
    ) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        linked_skills = repository / "linked-skills"
        linked_skills.mkdir()
        (repository / ".agents").mkdir()
        (repository / ".agents/skills").symlink_to(
            linked_skills, target_is_directory=True
        )

        reconciliation = calculate_content_reconciliation(
            self.resolve_contract(repository)
        )

        self.assertIn(
            "managed target ancestor must not be a symlink",
            render_content_reconciliation(reconciliation),
        )

    def test_documentation_profile_manages_exactly_seven_templates(self) -> None:
        manifest = self.base_manifest()
        manifest["profiles"] = ["common", "documentation"]
        manifest["repository-owned"] = ["docs/README.md", "docs/tutorials/**"]
        temporary, repository = self.create_repository(manifest)
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        documentation_targets = [
            item.target
            for item in content_files
            if item.target.startswith("docs/_templates/") and item.mode != "absent"
        ]
        self.assertEqual(len(documentation_targets), 7)
        retired = next(
            item
            for item in content_files
            if item.target == "docs/_templates/decision.template.md"
        )
        self.assertEqual(retired.mode, "absent")

    def test_dependabot_is_rendered_from_structured_manifest_updates(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        content_files = self.resolve_contract(repository).managed_files
        dependabot = next(
            item for item in content_files if item.target == ".github/dependabot.yml"
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
                ContractError, "dependency-updates must be a non-empty list"
            ):
                self.resolve_contract(repository)
        finally:
            temporary.cleanup()

        unsafe = self.base_manifest()
        unsafe["dependency-updates"][0]["directory"] = "/../outside"
        temporary, repository = self.create_repository(unsafe)
        try:
            with self.assertRaisesRegex(ContractError, "must not contain dot segments"):
                self.resolve_contract(repository)
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
            ContractError,
            "github must define repository, default-branch, settings, and ruleset",
        ):
            self.resolve_contract(repository)

    def test_manifest_requires_common_profile_and_github_contract(self) -> None:
        missing_common = self.base_manifest()
        missing_common["profiles"].remove("common")
        temporary, repository = self.create_repository(missing_common)
        try:
            with self.assertRaisesRegex(
                ContractError, "requires the common profile"
            ):
                self.resolve_contract(repository)
        finally:
            temporary.cleanup()

        missing_github = self.base_manifest()
        del missing_github["github"]
        temporary, repository = self.create_repository(missing_github)
        try:
            with self.assertRaisesRegex(
                ContractError, "github contract is required"
            ):
                self.resolve_contract(repository)
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

        duplicate_boundaries = self.base_manifest()
        duplicate_boundaries["boundaries"].append(
            {"path": ".", "type": "repository", "title": "Test Repository"}
        )
        invalid_manifests.append(
            (
                "duplicate boundary",
                duplicate_boundaries,
                "duplicate declarations",
            )
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
                    with self.assertRaisesRegex(ContractError, message):
                        self.resolve_contract(repository)
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

        contract = self.resolve_contract(repository)
        results = inspect_boundaries(repository, contract.boundaries)
        self.assertEqual([result.status for result in results], ["ok", "ok", "ok"])
        documentation_targets = [
            item.target
            for item in contract.managed_files
            if "/_templates/" in item.target and item.mode != "absent"
        ]
        self.assertEqual(len(documentation_targets), 7)
        self.assertTrue(
            all(target.startswith("docs/_templates/") for target in documentation_targets)
        )

    def test_boundary_inspection_reports_shape_docs_and_nested_template_failures(self) -> None:
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

        results = inspect_boundaries(
            repository, self.resolve_contract(repository).boundaries
        )
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

        result = inspect_boundaries(
            repository, self.resolve_contract(repository).boundaries
        )[0]
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

        result = inspect_boundaries(
            repository, self.resolve_contract(repository).boundaries
        )[0]

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

        result = inspect_boundaries(
            repository, self.resolve_contract(repository).boundaries
        )[0]
        self.assertEqual(result.status, "ok")

    def test_boundary_inspection_reflects_repository_document_state(self) -> None:
        temporary, repository = self.create_repository(self.base_manifest())
        self.addCleanup(temporary.cleanup)
        self.write_file(
            repository,
            "README.md",
            '<div align="center">\n  <h1>Test Repository</h1>\n</div>\n\n'
            "See [documentation](docs/README.md).\n",
        )
        self.write_file(repository, "docs/README.md", "# Documentation\n")
        content_files = self.resolve_contract(repository).managed_files
        self.write_results(repository, inspect(repository, content_files))

        boundaries = self.resolve_contract(repository).boundaries
        self.assertEqual(inspect_boundaries(repository, boundaries)[0].status, "ok")

        self.write_file(repository, "docs/README.md", "# Wrong\n")
        self.assertEqual(
            inspect_boundaries(repository, boundaries)[0].status, "invalid"
        )

    def test_repository_owned_changelog_opts_into_structural_inspection(self) -> None:
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
        content_files = self.resolve_contract(repository).managed_files
        self.write_results(repository, inspect(repository, content_files))

        documents = inspect_repository_owned_documents(
            repository, self.resolve_contract(repository).repository_owned
        )

        self.assertEqual(documents[0].path, "CHANGELOG.md")
        self.assertEqual(documents[0].status, "invalid")
        self.assertIn(
            "root '# Changelog' title",
            documents[0].messages[0],
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
