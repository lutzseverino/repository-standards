from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_SOURCE = (
    ROOT
    / "profiles/repository-lifecycle-skills/files/.agents/skills"
    / "create-repository"
)


@unittest.skipUnless(
    os.environ.get("RUN_FRESH_AGENT_TESTS") == "1" and shutil.which("codex"),
    "set RUN_FRESH_AGENT_TESTS=1 with Codex authentication to run fresh-agent tests",
)
class CreationFreshAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name).resolve() / "harness"
        self.repository.mkdir()
        skill = self.repository / ".agents/skills/create-repository"
        shutil.copytree(SKILL_SOURCE, skill)
        runner = skill / "scripts/create"
        runner.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import pathlib
                import sys

                arguments = sys.argv[1:]
                if arguments == ["--help"]:
                    print("usage: create --name NAME --purpose PURPOSE --visibility "
                          "VISIBILITY --license LICENSE --owner OWNER --destination "
                          "DESTINATION --validation-executable EXECUTABLE "
                          "[--validation-argument ARGUMENT] [--fact FACT] "
                          "[--profile PROFILE] [--version VERSION]")
                    raise SystemExit(0)
                pathlib.Path(".creation-invoked").write_text(
                    "\\n".join(arguments) + "\\n", encoding="utf-8"
                )
                destination = pathlib.Path(
                    arguments[arguments.index("--destination") + 1]
                )
                if destination.exists():
                    print("error: local destination collision", file=sys.stderr)
                    raise SystemExit(2)
                if "existing" in arguments:
                    print("error: GitHub identity collision; repository exists", file=sys.stderr)
                    raise SystemExit(2)
                facts = [
                    arguments[index + 1]
                    for index, value in enumerate(arguments)
                    if value == "--fact"
                ]
                if "package-manager=npm" in facts and "framework=vite-react" in facts:
                    print(
                        "error: multiple selectable ecosystem profiles match; "
                        "choose explicitly: node-npm, vite-react",
                        file=sys.stderr,
                    )
                    raise SystemExit(2)
                selected = ["common", "documentation"]
                if all(
                    fact in facts
                    for fact in (
                        "ecosystem=node",
                        "package-manager=npm",
                        "project-kind=protocol",
                    )
                ):
                    selected.append("node-protocol")
                pathlib.Path(".creation-result").write_text(
                    "\\n".join(selected) + "\\n", encoding="utf-8"
                )
                print(
                    "Prepared creation baseline; selected profiles: "
                    + ", ".join(selected)
                    + "; first publication is required."
                )
                """
            ),
            encoding="utf-8",
        )
        runner.chmod(0o755)
        (self.repository / "AGENTS.md").write_text(
            "# Agent guidance\n\nRespond in English. The canonical validation "
            "command for new repository baselines is `true`.\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.repository), "init", "-q", "-b", "main"],
            check=True,
        )

    def run_fresh_agent(self, prompt: str) -> tuple[subprocess.CompletedProcess[str], str]:
        final_message = self.repository / ".agent-final.txt"
        result = subprocess.run(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--sandbox",
                "workspace-write",
                "--color",
                "never",
                "--output-last-message",
                str(final_message),
                "--cd",
                str(self.repository),
                prompt,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        final = (
            final_message.read_text(encoding="utf-8")
            if final_message.is_file()
            else ""
        )
        return result, final

    def invocation(self) -> str:
        return (self.repository / ".creation-invoked").read_text(encoding="utf-8")

    def selected_profiles(self) -> list[str]:
        return (self.repository / ".creation-result").read_text(
            encoding="utf-8"
        ).splitlines()

    def test_rich_prior_context_is_reused_for_standalone_creation(self) -> None:
        destination = self.repository.parent / "widget"
        result, final = self.run_fresh_agent(
            "Create private "
            "owner/widget at "
            f"{destination}; purpose is 'Track widgets safely.'; license is MIT; "
            "ecosystem is unsupported Elixir and project kind is application."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        invocation = self.invocation()
        self.assertIn("--name\nwidget", invocation)
        self.assertIn("--purpose\nTrack widgets safely.", invocation)
        self.assertIn("--visibility\nprivate", invocation)
        self.assertIn("--license\nMIT", invocation)
        self.assertIn("--fact\necosystem=elixir", invocation.lower())
        self.assertNotIn("workflow", invocation.lower())
        self.assertEqual(self.selected_profiles(), ["common", "documentation"])
        self.assertIn("first publication", final.lower())

    def test_missing_explicit_decisions_are_requested_before_invocation(self) -> None:
        result, final = self.run_fresh_agent(
            "Create a new repository named widget."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repository / ".creation-invoked").exists())
        lowered = final.lower()
        for missing in ("purpose", "visibility", "license", "ecosystem"):
            self.assertIn(missing, lowered)

    def test_unknown_applicability_is_requested_before_invocation(self) -> None:
        destination = self.repository.parent / "widget"
        result, final = self.run_fresh_agent(
            "Create private owner/widget at "
            f"{destination}. Purpose: 'Track widgets.' License: MIT."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repository / ".creation-invoked").exists())
        self.assertTrue(
            "ecosystem" in final.lower() or "applicability" in final.lower()
        )

    def test_ambiguous_profiles_are_returned_for_explicit_selection(self) -> None:
        destination = self.repository.parent / "web"
        result, final = self.run_fresh_agent(
            "Create private owner/web at "
            f"{destination}. Purpose: 'Serve the web.' License: MIT. It is a "
            "Vite React application using npm; pass ecosystem=node, "
            "package-manager=npm, and framework=vite-react as facts."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("package-manager=npm", self.invocation())
        self.assertIn("framework=vite-react", self.invocation())
        self.assertIn("node-npm", final)
        self.assertIn("vite-react", final)
        self.assertIn("explicit", final.lower())

    def test_unique_profile_facts_are_forwarded_without_extra_questions(self) -> None:
        destination = self.repository.parent / "protocol"
        result, final = self.run_fresh_agent(
            "Create private owner/protocol at "
            f"{destination}. Purpose: 'Define a wire protocol.' License: MIT. "
            "The settled facts are ecosystem=node, package-manager=npm, and "
            "project-kind=protocol."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        invocation = self.invocation()
        self.assertIn("ecosystem=node", invocation)
        self.assertIn("package-manager=npm", invocation)
        self.assertIn("project-kind=protocol", invocation)
        self.assertEqual(
            self.selected_profiles(),
            ["common", "documentation", "node-protocol"],
        )
        self.assertIn("first publication", final.lower())

    def test_collision_is_surfaced_without_switching_workflows(self) -> None:
        destination = self.repository.parent / "existing"
        result, final = self.run_fresh_agent(
            "Create private owner/existing at "
            f"{destination}. Purpose: 'Existing identity.' License: MIT. "
            "The unsupported ecosystem is Elixir and the project kind is application."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        lowered = final.lower()
        self.assertTrue(
            "collision" in lowered or "already exists" in lowered
        )
        self.assertNotIn("implement", final.lower())
        self.assertFalse((self.repository / ".workflow-invoked").exists())

    def test_local_collision_is_surfaced_without_mutating_the_destination(
        self,
    ) -> None:
        destination = self.repository.parent / "occupied"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_text("keep\n", encoding="utf-8")
        result, final = self.run_fresh_agent(
            "Create private owner/fresh at "
            f"{destination}. Purpose: 'Preserve the destination.' License: MIT. "
            "The unsupported ecosystem is Elixir and the project kind is application."
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("collision", final.lower())
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
