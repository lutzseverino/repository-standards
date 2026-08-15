from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / "scripts/publish-release"


class PublishReleaseCommandTests(unittest.TestCase):
    def test_manual_recovery_routes_through_the_complete_release_command(self) -> None:
        maintenance = (ROOT / "standards/maintenance-and-rollout.md").read_text(
            encoding="utf-8"
        )
        recovery = maintenance.split("### Recover a tag whose release failed", 1)[1]
        recovery = recovery.split("## Adopt a standards release", 1)[0]

        self.assertIn("git checkout vMAJOR.MINOR.PATCH", recovery)
        self.assertIn("scripts/publish-release vMAJOR.MINOR.PATCH", recovery)
        self.assertNotIn("gh release create", recovery)

    def create_repository(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        (repository / "VERSION").write_text("2.0.0\n", encoding="utf-8")
        (repository / "CHANGELOG.md").write_text(
            """# Changelog

## [Unreleased]

## [2.0.0] - 2026-08-14

### Changed

- Changed the public contract.
""",
            encoding="utf-8",
        )
        return temporary, repository

    def fake_environment(
        self, repository: Path
    ) -> tuple[dict[str, str], Path]:
        binaries = repository / "bin"
        binaries.mkdir()
        git = binaries / "git"
        git.write_text(
            """#!/bin/sh
if [ "$1 $2" = "cat-file -t" ]; then
  printf '%s\n' "${FAKE_TAG_TYPE:-tag}"
  exit 0
fi
if [ "$1 $2" = "merge-base --is-ancestor" ]; then
  exit "${FAKE_MAIN_EXIT:-0}"
fi
exit 2
""",
            encoding="utf-8",
        )
        git.chmod(0o755)
        gh = binaries / "gh"
        gh.write_text(
            """#!/bin/sh
if [ "$1" = api ]; then
  printf '%s\n' "${FAKE_CI_RESULT:-true}"
  exit 0
fi
if [ "$1 $2" = "release create" ]; then
  previous=
  notes_file=
  for argument in "$@"; do
    if [ "$previous" = --notes-file ]; then
      notes_file=$argument
    fi
    previous=$argument
  done
  printf '%s\n' "$*" > "$PUBLISH_LOG"
  printf '%s\n' BODY >> "$PUBLISH_LOG"
  cat "$notes_file" >> "$PUBLISH_LOG"
  exit 0
fi
exit 2
""",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        log = repository / "publish.log"
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{binaries}{os.pathsep}{environment['PATH']}",
                "GITHUB_REPOSITORY": "owner/example",
                "PUBLISH_LOG": str(log),
            }
        )
        return environment, log

    def run_command(
        self, repository: Path, environment: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(COMMAND), "v2.0.0"],
            cwd=repository,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_publishes_validated_notes_for_an_annotated_main_tag_with_green_ci(
        self,
    ) -> None:
        temporary, repository = self.create_repository()
        self.addCleanup(temporary.cleanup)
        environment, log = self.fake_environment(repository)

        result = self.run_command(repository, environment)

        self.assertEqual(result.returncode, 0, result.stderr)
        publication = log.read_text(encoding="utf-8")
        self.assertIn("release create v2.0.0 --verify-tag", publication)
        self.assertIn("--title v2.0.0 --notes-file", publication)
        self.assertNotIn("--draft", publication)
        self.assertNotIn("--prerelease", publication)
        self.assertIn("BODY\n### Changed\n\n- Changed the public contract.\n", publication)

    def test_rejects_unannotated_off_main_or_unverified_tags_before_publication(
        self,
    ) -> None:
        cases = (
            {"FAKE_TAG_TYPE": "commit"},
            {"FAKE_MAIN_EXIT": "1"},
            {"FAKE_CI_RESULT": "false"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                temporary, repository = self.create_repository()
                try:
                    environment, log = self.fake_environment(repository)
                    environment.update(overrides)

                    result = self.run_command(repository, environment)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(log.exists())
                finally:
                    temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
