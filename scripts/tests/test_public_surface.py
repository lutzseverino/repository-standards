from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PublicSurfaceTests(unittest.TestCase):
    def test_standards_is_the_only_repository_goal_executable(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts/standards"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "{check,repair,create,publish,adopt}", result.stdout
        )
        self.assertNotIn("deliver", result.stdout)
        create_help = subprocess.run(
            [str(ROOT / "scripts/standards"), "create", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(create_help.returncode, 0, create_help.stderr)
        self.assertNotIn("contract-input", create_help.stdout)
        create_without_facts = subprocess.run(
            [str(ROOT / "scripts/standards"), "create"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(create_without_facts.returncode, 2)
        self.assertIn(
            "required: --name, --purpose, --visibility, --license, --owner, "
            "--validation-command",
            create_without_facts.stderr,
        )
        for retired in (
            "audit",
            "audit-live",
            "sync",
            "sync-live",
            "init",
            "first-publication",
            "check",
        ):
            self.assertFalse((ROOT / "scripts" / retired).exists(), retired)

    def test_retired_implementation_and_test_surfaces_are_absent(self) -> None:
        retired_paths = (
            "scripts/lib/standards.py",
            "scripts/lib/offline_" + "sync.py",
            "scripts/lib/live_" + "reconciliation.py",
            "scripts/lib/repository_initialization.py",
            "scripts/lib/first_" + "publication.py",
            "scripts/tests/test_standards.py",
            "scripts/tests/test_offline_" + "sync.py",
            "scripts/tests/test_live_" + "sync.py",
            "scripts/tests/test_live_" + "reconciliation.py",
            "scripts/tests/test_initialization.py",
            "scripts/tests/test_standards_audit_workflow.py",
            "scripts/tests/test_first_" + "publication.py",
            "scripts/tests/test_first_" + "publication_skill.py",
            ".github/workflows/standards-" + "audit.yml",
        )

        for retired in retired_paths:
            self.assertFalse((ROOT / retired).exists(), retired)

        retired_types = (
            "Planned" + "File",
            "PlanBuild" + "Blocker",
            "Synchronization" + "Plan",
            "Synchronization" + "Blocker",
            "Synchronization" + "Operation",
            "LiveDesiredState" + "Delta",
            "LiveRepository" + "Contract",
            "Live" + "Lifecycle",
            "Live" + "Operation",
            "Live" + "Difference",
            "LiveApplication" + "Report",
            "InitializationPlan",
            "Publication" + "Plan",
        )
        python = "\n".join(
            path.read_text(encoding="utf-8")
            for directory in (ROOT / "scripts/lib", ROOT / "scripts/tests")
            for path in directory.glob("*.py")
            if path != Path(__file__)
        )
        for retired in retired_types:
            self.assertNotIn(retired, python, retired)

    def test_retired_adapters_and_phase_commands_are_not_distributed_or_taught(
        self,
    ) -> None:
        retired_skill_names = (
            "adopt-repository-" + "standards",
            "first-" + "publication",
        )
        skill_roots = (
            ROOT / ".agents/skills",
            ROOT
            / "profiles/repository-lifecycle-skills/files/.agents/skills",
        )
        for skill_root in skill_roots:
            for retired in retired_skill_names:
                self.assertFalse((skill_root / retired).exists(), retired)

        living_files = (
            ROOT / "README.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "CONTEXT.md",
            ROOT / "docs/README.md",
            *sorted((ROOT / "standards").glob("*.md")),
            *sorted((ROOT / "profiles").glob("*/README.md")),
            *(
                path
                for skill_root in skill_roots
                for path in skill_root.rglob("*")
                if path.is_file()
            ),
            ROOT / "profiles/repository-lifecycle-skills/profile.json",
            *(path for path in (ROOT / "scripts/tests").glob("*.py") if path != Path(__file__)),
            ROOT / ".agents/scripts/discover-standards-release.sh",
            ROOT / "profiles/common/files/.agents/scripts/discover-standards-release.sh",
        )
        retired_fragments = (
            "scripts/" + "audit",
            "scripts/" + "sync",
            "scripts/" + "init",
            "scripts/" + "first-publication",
            "scripts/" + "check",
            *retired_skill_names,
            "--plan-" + "file",
            "Plan " + "mode",
            "Publish " + "mode",
            "Prepare " + "begins",
            "Finalize",
            "live " + "audit",
            "standards " + "audit",
            "synchron" + "ization",
            "managed or " + "audited behavior",
        )
        contents = {
            path.relative_to(ROOT): path.read_text(encoding="utf-8")
            for path in living_files
        }
        for retired in retired_fragments:
            offenders = [
                str(path)
                for path, text in contents.items()
                if retired.casefold() in text.casefold()
            ]
            self.assertEqual(offenders, [], f"{retired}: {offenders}")

    def test_public_orientation_states_the_repository_environment_contract(
        self,
    ) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        lifecycle = (ROOT / "standards/repository-lifecycle.md").read_text(
            encoding="utf-8"
        )
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        for fragment in (
            "unrelated maintainers",
            "repository environment",
            "Product implementation",
            "repository-owned tooling",
            "Linux",
            "macOS",
            "WSL",
            "Native Windows",
            "$deliver-change",
        ):
            self.assertIn(fragment, readme)
        self.assertNotIn("scripts/standards deliver", readme)

        self.assertIn("repository environment", lifecycle)
        self.assertIn("Product implementation", lifecycle)
        self.assertIn("Agent Skill", lifecycle)
        self.assertIn("$deliver-change", lifecycle)
        self.assertIn("supplementary workflows", contributing)
        self.assertIn("alternative workflow sets", contributing)

    def test_superseding_decisions_record_the_truthful_public_boundary(
        self,
    ) -> None:
        environment_decision = (
            ROOT
            / "docs/adr/0010-define-the-public-repository-environment.md"
        ).read_text(encoding="utf-8")
        lifecycle_decision = (
            ROOT
            / "docs/adr/0011-advertise-only-operational-lifecycle-interfaces.md"
        ).read_text(encoding="utf-8")

        self.assertIn("repository environment", environment_decision)
        self.assertIn("product implementation", environment_decision)
        self.assertIn("Supersedes", environment_decision)
        self.assertIn("Agent Skill", lifecycle_decision)
        self.assertIn("stub", lifecycle_decision)
        self.assertIn("Supersedes", lifecycle_decision)


if __name__ == "__main__":
    unittest.main()
