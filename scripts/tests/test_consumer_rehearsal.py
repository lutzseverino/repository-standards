from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ConsumerRehearsalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.log = self.directory / "calls.log"
        self.release = self.directory / "release"
        standards = self.release / "scripts/standards"
        standards.parent.mkdir(parents=True)
        standards.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys
                from pathlib import Path

                if os.environ.get("GH_TOKEN") != "fixture-token":
                    print("missing isolated GitHub authentication", file=sys.stderr)
                    raise SystemExit(2)
                with Path(os.environ["REHEARSAL_CALL_LOG"]).open(
                    "a", encoding="utf-8"
                ) as log:
                    log.write("standards " + " ".join(sys.argv[1:]) + "\\n")
                print("Conclusion: standards-complete")
                """
            ),
            encoding="utf-8",
        )
        standards.chmod(0o755)
        self.demo = self.directory / "demo-source"
        self.demo.mkdir()
        (self.demo / ".repository-standards.json").write_text(
            '{"standards-release": "6.0.0"}\n', encoding="utf-8"
        )

    def write_executable(self, name: str, content: str) -> Path:
        executable = self.bin / name
        executable.write_text(textwrap.dedent(content), encoding="utf-8")
        executable.chmod(0o755)
        return executable

    def test_public_installation_selects_release_and_assesses_live_target(
        self,
    ) -> None:
        self.write_executable(
            "npx",
            """\
            #!/usr/bin/env python3
            import os
            import sys
            from pathlib import Path

            forbidden = {
                "REPOSITORY_STANDARDS_SOURCE",
                "GIT_CONFIG_COUNT",
                "GIT_CONFIG_KEY_0",
                "GIT_CONFIG_VALUE_0",
                "GIT_CONFIG_PARAMETERS",
            }
            inherited = forbidden.intersection(os.environ)
            if inherited:
                print(
                    "inherited source override: " + ", ".join(sorted(inherited)),
                    file=sys.stderr,
                )
                raise SystemExit(2)
            with Path(os.environ["REHEARSAL_CALL_LOG"]).open(
                "a", encoding="utf-8"
            ) as log:
                log.write("npx " + " ".join(sys.argv[1:]) + "\\n")
            resolver = (
                Path(os.environ["HOME"])
                / ".agents/skills/adopt-standards/scripts/select-release"
            )
            resolver.parent.mkdir(parents=True)
            resolver.write_text(
                "#!/usr/bin/env python3\\n"
                "import os, sys\\n"
                "print(f'Selected standards release: {sys.argv[1]}')\\n"
                "print(f'Release checkout: {os.environ[\\\"REHEARSAL_RELEASE\\\"]}')\\n"
                "print(f'Selected skill: {os.environ[\\\"REHEARSAL_RELEASE\\\"]}'"
                "+ '/.agents/skills/adopt-standards/SKILL.md')\\n",
                encoding="utf-8",
            )
            resolver.chmod(0o755)
            """,
        )
        self.write_executable(
            "gh",
            """\
            #!/usr/bin/env python3
            import sys

            if sys.argv[1:] != ["auth", "token"]:
                raise SystemExit(2)
            print("fixture-token")
            """,
        )
        self.write_executable(
            "git",
            """\
            #!/usr/bin/env python3
            import os
            import shutil
            import sys
            from pathlib import Path

            with Path(os.environ["REHEARSAL_CALL_LOG"]).open(
                "a", encoding="utf-8"
            ) as log:
                log.write("git " + " ".join(sys.argv[1:]) + "\\n")
            if sys.argv[1] != "clone":
                raise SystemExit(2)
            shutil.copytree(os.environ["REHEARSAL_DEMO"], sys.argv[-1])
            """,
        )
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": str(self.bin) + os.pathsep + environment["PATH"],
                "REHEARSAL_CALL_LOG": str(self.log),
                "REHEARSAL_RELEASE": str(self.release),
                "REHEARSAL_DEMO": str(self.demo),
                "REPOSITORY_STANDARDS_SOURCE": str(self.release),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "url.file:///fixture/.insteadOf",
                "GIT_CONFIG_VALUE_0": "https://github.com/",
                "GIT_CONFIG_PARAMETERS": (
                    "'url.file:///fixture/.insteadOf'='https://github.com/'"
                ),
            }
        )

        result = subprocess.run(
            [
                str(ROOT / "scripts/rehearse-public-contract"),
                "6.0.0",
                "owner/repository-standards-demo",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.log.read_text(encoding="utf-8")
        self.assertIn(
            "npx --yes skills@1.5.23 add "
            "https://github.com/lutzseverino/repository-standards/tree/main/bootstrap "
            "--skill create-repository --skill adopt-standards --global",
            calls,
        )
        self.assertIn(
            "git clone --quiet "
            "https://github.com/owner/repository-standards-demo.git",
            calls,
        )
        self.assertIn("standards check", calls)
        self.assertIn("Selected immutable release: 6.0.0", result.stdout)
        self.assertIn("Live public-contract rehearsal passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
