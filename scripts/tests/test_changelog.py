from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / "scripts/changelog"


class ChangelogCommandTests(unittest.TestCase):
    def run_command(
        self, repository: Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(COMMAND), *arguments, str(repository)],
            check=False,
            capture_output=True,
            text=True,
        )

    def write_repository(
        self, changelog: str, version: str = "2.0.0"
    ) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        (repository / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
        (repository / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        return temporary

    def test_valid_changelog_passes_validation(self) -> None:
        temporary = self.write_repository(
            """# Changelog

All notable changes are documented here.

## [Unreleased]

### Added

- Work in progress.

## [2.0.0] - 2026-08-14

### Changed

- Changed the public contract.

### Migration

- Adopt the new contract.

## [1.1.0] - 2026-07-01

### Fixed

- Corrected the previous behavior.

[Unreleased]: https://example.test/compare/v2.0.0...HEAD
[2.0.0]: https://example.test/compare/v1.1.0...v2.0.0
"""
        )
        self.addCleanup(temporary.cleanup)

        result = self.run_command(Path(temporary.name), "validate")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "CHANGELOG.md is valid\n")

    def test_root_title_must_be_one_changelog_heading(self) -> None:
        cases = {
            "wrong title": "# Changes\n\n## [Unreleased]\n",
            "duplicate title": (
                "# Changelog\n\n## [Unreleased]\n\n# Changelog\n"
            ),
        }
        for label, changelog in cases.items():
            with self.subTest(label=label):
                temporary = self.write_repository(changelog)
                try:
                    result = self.run_command(Path(temporary.name), "validate")
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn("exactly one root '# Changelog' title", result.stderr)

    def test_changelog_requires_exactly_one_unreleased_section(self) -> None:
        cases = {
            "missing": "# Changelog\n\n## [2.0.0] - 2026-08-14\n",
            "duplicate": (
                "# Changelog\n\n## [Unreleased]\n\n## [Unreleased]\n"
            ),
        }
        for label, changelog in cases.items():
            with self.subTest(label=label):
                temporary = self.write_repository(changelog)
                try:
                    result = self.run_command(Path(temporary.name), "validate")
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn("exactly one '## [Unreleased]' section", result.stderr)

    def test_release_headings_require_semantic_versions_and_iso_dates(self) -> None:
        cases = {
            "malformed version": "## [1.2] - 2026-08-14",
            "leading-zero version": "## [01.2.3] - 2026-08-14",
            "impossible date": "## [1.2.3] - 2026-02-30",
            "non-iso date": "## [1.2.3] - 2026-8-14",
            "unknown section": "## Notes",
        }
        for label, heading in cases.items():
            with self.subTest(label=label):
                temporary = self.write_repository(
                    f"# Changelog\n\n## [Unreleased]\n\n{heading}\n"
                )
                try:
                    result = self.run_command(Path(temporary.name), "validate")
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn("invalid level-two section heading", result.stderr)

    def test_sections_and_releases_are_newest_first_without_duplicates(self) -> None:
        cases = {
            "unreleased is not first": (
                "## [2.0.0] - 2026-08-14\n\n## [Unreleased]"
            ),
            "duplicate release": (
                "## [Unreleased]\n\n## [2.0.0] - 2026-08-14\n\n"
                "## [2.0.0] - 2026-08-13"
            ),
            "version order": (
                "## [Unreleased]\n\n## [1.0.0] - 2026-08-14\n\n"
                "## [2.0.0] - 2026-08-13"
            ),
            "prerelease order": (
                "## [Unreleased]\n\n## [2.0.0-rc.1] - 2026-08-14\n\n"
                "## [2.0.0] - 2026-08-13"
            ),
            "date order": (
                "## [Unreleased]\n\n## [2.0.0] - 2026-07-01\n\n"
                "## [1.0.0] - 2026-08-14"
            ),
        }
        for label, sections in cases.items():
            with self.subTest(label=label):
                temporary = self.write_repository(f"# Changelog\n\n{sections}\n")
                try:
                    result = self.run_command(Path(temporary.name), "validate")
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn("newest first", result.stderr)

    def test_categories_are_known_unique_and_nonempty_within_each_section(self) -> None:
        cases = {
            "category before a section": (
                "### Added\n\n- Outside a changelog section.\n\n"
                "## [Unreleased]\n"
            ),
            "uncategorized": (
                "## [Unreleased]\n\n## [2.0.0] - 2026-08-14\n\n"
                "- Changed the contract without a category.\n"
            ),
            "unknown": (
                "## [Unreleased]\n\n### Breaking\n\n- Broke the contract.\n"
            ),
            "duplicate": (
                "## [Unreleased]\n\n### Added\n\n- First.\n\n"
                "### Added\n\n- Second.\n"
            ),
            "empty": (
                "## [Unreleased]\n\n### Added\n\n"
                "[Unreleased]: https://example.test/compare/v2.0.0...HEAD\n"
            ),
        }
        for label, sections in cases.items():
            with self.subTest(label=label):
                temporary = self.write_repository(f"# Changelog\n\n{sections}")
                try:
                    result = self.run_command(Path(temporary.name), "validate")
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn("changelog category", result.stderr)

    def test_release_notes_are_exactly_the_matching_changelog_section(self) -> None:
        temporary = self.write_repository(
            """# Changelog

## [Unreleased]

## [2.0.0] - 2026-08-14

### Changed

- Changed the public contract.

### Migration

- Adopt the new contract.

## [1.1.0] - 2026-07-01

### Fixed

- Corrected the previous behavior.
"""
        )
        self.addCleanup(temporary.cleanup)

        result = self.run_command(
            Path(temporary.name), "release-notes", "--tag", "v2.0.0"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "### Changed\n\n- Changed the public contract.\n\n"
            "### Migration\n\n- Adopt the new contract.\n",
        )

    def test_release_notes_reject_incoherent_release_inputs(self) -> None:
        changelog = """# Changelog

## [Unreleased]

## [2.0.0] - 2026-08-14

### Changed

- Changed the public contract.
"""
        cases = (
            ("v2.0.0-rc.1", "2.0.0", "stable semantic version"),
            ("v2.0.0", "2.0.1", "disagrees with source VERSION"),
            ("v2.0.1", "2.0.1", "no matching release"),
        )
        for tag, version, message in cases:
            with self.subTest(tag=tag, version=version):
                temporary = self.write_repository(changelog, version)
                try:
                    result = self.run_command(
                        Path(temporary.name), "release-notes", "--tag", tag
                    )
                finally:
                    temporary.cleanup()

                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)
                self.assertEqual(result.stdout, "")

    def test_comparison_links_are_not_part_of_release_notes(self) -> None:
        temporary = self.write_repository(
            """# Changelog

## [Unreleased]

## [2.0.0] - 2026-08-14

### Changed

- Changed the public contract.

[Unreleased]: https://example.test/compare/v2.0.0...HEAD
[2.0.0]: https://example.test/compare/v1.0.0...v2.0.0
"""
        )
        self.addCleanup(temporary.cleanup)

        result = self.run_command(
            Path(temporary.name), "release-notes", "--tag", "v2.0.0"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "### Changed\n\n- Changed the public contract.\n",
        )

    def test_fenced_heading_examples_are_literal_release_note_content(self) -> None:
        temporary = self.write_repository(
            '''# Changelog

## [Unreleased]

## [2.0.0] - 2026-08-14

### Changed

- Document the generated Markdown:

```markdown
## Example

### Added

## [Unreleased]
```

- Keep parsing the release after the example.
'''
        )
        self.addCleanup(temporary.cleanup)

        result = self.run_command(
            Path(temporary.name), "release-notes", "--tag", "v2.0.0"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Example", result.stdout)
        self.assertIn("### Added", result.stdout)
        self.assertIn("## [Unreleased]", result.stdout)
        self.assertIn("Keep parsing the release after the example", result.stdout)


if __name__ == "__main__":
    unittest.main()
