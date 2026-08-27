from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/lib/canonical_validation.py"


class CanonicalValidationExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        manifest = json.loads(
            (ROOT / "examples/repository-standards.json").read_text(
                encoding="utf-8"
            )
        )
        manifest["profiles"] = ["common", "documentation"]
        manifest["github"]["repository"] = "owner/example"
        manifest["local-fragments"] = {}
        manifest["canonical-validation"] = {
            "executable": "tools/check runner",
            "arguments": ["argument with spaces", "$(touch sentinel)", "*.py"],
            "working-directory": "validation workspace",
        }
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        workspace = self.repository / "validation workspace"
        executable = workspace / "tools/check runner"
        executable.parent.mkdir(parents=True)
        executable.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                from pathlib import Path
                import sys

                Path("observed.json").write_text(
                    json.dumps({"arguments": sys.argv[1:], "cwd": Path.cwd().name}),
                    encoding="utf-8",
                )
                """
            ),
            encoding="utf-8",
        )
        executable.chmod(0o755)

    def run_validation(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(RUNNER),
                "--standards-root",
                str(ROOT),
                str(self.repository),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def manifest(self) -> dict:
        return json.loads(
            (self.repository / ".repository-standards.json").read_text(
                encoding="utf-8"
            )
        )

    def write_manifest(self, manifest: dict) -> None:
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def test_preserves_literal_arguments_and_declared_working_directory(self) -> None:
        result = self.run_validation()

        self.assertEqual(result.returncode, 0, result.stderr)
        observed = json.loads(
            (self.repository / "validation workspace/observed.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            observed["arguments"],
            ["argument with spaces", "$(touch sentinel)", "*.py"],
        )
        self.assertEqual(observed["cwd"], "validation workspace")
        self.assertFalse((self.repository / "validation workspace/sentinel").exists())

    def test_reports_an_unavailable_executable(self) -> None:
        manifest = self.manifest()
        manifest["canonical-validation"]["executable"] = "missing validator"
        self.write_manifest(manifest)

        result = self.run_validation()

        self.assertEqual(result.returncode, 127)
        self.assertIn("canonical validation executable is unavailable", result.stderr)
        self.assertIn("missing validator", result.stderr)

    def test_reports_the_exact_nonzero_exit(self) -> None:
        manifest = self.manifest()
        manifest["canonical-validation"]["arguments"] = ["fail"]
        self.write_manifest(manifest)
        executable = self.repository / "validation workspace/tools/check runner"
        executable.write_text(
            "#!/usr/bin/env python3\nraise SystemExit(23)\n", encoding="utf-8"
        )

        result = self.run_validation()

        self.assertEqual(result.returncode, 23)
        self.assertIn("canonical validation exited with status 23", result.stderr)

    def test_rejects_a_working_directory_symlink_that_escapes_the_repository(self) -> None:
        outside = self.repository.parent / f"{self.repository.name}-outside"
        outside.mkdir()
        workspace = self.repository / "validation workspace"
        for path in sorted(workspace.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        workspace.rmdir()
        workspace.symlink_to(outside, target_is_directory=True)

        result = self.run_validation()

        self.assertEqual(result.returncode, 2)
        self.assertIn("working directory escapes the repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
