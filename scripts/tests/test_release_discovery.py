from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


INTRODUCING_RELEASE = "4.0.0"


class ReleaseDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name) / "repository"
        self.repository.mkdir()
        self.release = (ROOT / "VERSION").read_text(
            encoding="utf-8"
        ).strip()
        self.manifest = {
            "standards-version": 5,
            "standards-release": self.release,
            "profiles": ["common", "documentation"],
            "boundaries": [
                {"path": ".", "type": "repository", "title": "Test Repository"}
            ],
            "dependency-updates": [
                {
                    "ecosystem": "github-actions",
                    "directory": "/",
                    "schedule": "weekly",
                }
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
            "repository-owned": ["README.md", "docs/README.md"],
        }
        self.write_manifest()

        discovery = self.repository / ".agents/scripts/discover-standards-release.sh"
        discovery.parent.mkdir(parents=True)
        shutil.copy2(
            ROOT / "profiles/common/files/.agents/scripts/discover-standards-release.sh",
            discovery,
        )
        self.manifest["standards-release"] = "3.1.0"
        self.write_manifest()

        self.fake_bin = Path(self.temporary.name) / "bin"
        self.fake_bin.mkdir()
        fake_curl = self.fake_bin / "curl"
        fake_curl.write_text(
            """#!/bin/sh
printf '%s\\n' "$*" >> "$DISCOVERY_CURL_LOG"
if [ "${DISCOVERY_CURL_EXIT:-0}" -ne 0 ]; then
    printf 'simulated curl failure\\n' >&2
    exit "$DISCOVERY_CURL_EXIT"
fi
printf '%s' "$DISCOVERY_FINAL_URL"
""",
            encoding="utf-8",
        )
        fake_curl.chmod(0o755)
        self.curl_log = Path(self.temporary.name) / "curl.log"

    def write_manifest(self) -> None:
        (self.repository / ".repository-standards.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def request_count(self) -> int:
        if not self.curl_log.exists():
            return 0
        return len(self.curl_log.read_text(encoding="utf-8").splitlines())

    def run_discovery(
        self, final_url: str, *arguments: str, curl_exit: int = 0
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PATH"] = f"{self.fake_bin}{os.pathsep}{environment['PATH']}"
        environment["DISCOVERY_CURL_LOG"] = str(self.curl_log)
        environment["DISCOVERY_CURL_EXIT"] = str(curl_exit)
        environment["DISCOVERY_FINAL_URL"] = final_url
        return subprocess.run(
            [
                "sh",
                str(
                    self.repository
                    / ".agents/scripts/discover-standards-release.sh"
                ),
                *arguments,
            ],
            cwd=self.repository,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_newer_stable_release_is_discovered_with_one_bounded_request(self) -> None:
        result = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/"
            f"v{INTRODUCING_RELEASE}"
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, f"{INTRODUCING_RELEASE}\n")
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            self.curl_log.read_text(encoding="utf-8"),
            "--location --fail --silent --max-time 3 --output /dev/null "
            "--write-out %{url_effective} "
            "https://github.com/lutzseverino/repository-standards/releases/latest\n",
        )

    def test_cached_newer_release_renders_the_portable_notice_without_a_request(
        self,
    ) -> None:
        discovery = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/"
            f"v{INTRODUCING_RELEASE}"
        )

        notice = self.run_discovery(
            "unused because notice rendering must stay offline",
            "--notice",
            discovery.stdout.strip(),
        )

        self.assertEqual(notice.returncode, 0)
        self.assertEqual(
            notice.stdout,
            "Repository standards update available: "
            f"3.1.0 → {INTRODUCING_RELEASE}.\n"
            "\n"
            "Start a new session in this repository and enter:\n"
            f"adopt-standards {INTRODUCING_RELEASE}\n",
        )
        self.assertEqual(notice.stderr, "")
        self.assertEqual(self.request_count(), 1)

    def test_equal_and_locally_newer_releases_remain_silent(self) -> None:
        self.manifest["standards-release"] = "4.5.6"
        self.write_manifest()
        equal = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v4.5.6"
        )

        self.manifest["standards-release"] = "4.10.0"
        self.write_manifest()
        locally_newer = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v4.9.99"
        )

        self.assertEqual(equal.returncode, 0)
        self.assertEqual(equal.stdout, "")
        self.assertEqual(equal.stderr, "")
        self.assertEqual(locally_newer.returncode, 0)
        self.assertEqual(locally_newer.stdout, "")
        self.assertEqual(locally_newer.stderr, "")
        self.assertEqual(self.request_count(), 2)

    def test_missing_or_malformed_manifest_remains_silent_without_a_request(
        self,
    ) -> None:
        manifest_path = self.repository / ".repository-standards.json"
        manifest_path.unlink()
        missing = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v9.0.0"
        )
        manifest_path.write_text(
            '{"standards-release":"not-a-release"}', encoding="utf-8"
        )
        malformed = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v9.0.0"
        )

        self.assertEqual(missing.returncode, 0)
        self.assertEqual(missing.stdout, "")
        self.assertEqual(missing.stderr, "")
        self.assertEqual(malformed.returncode, 0)
        self.assertEqual(malformed.stdout, "")
        self.assertEqual(malformed.stderr, "")
        self.assertEqual(self.request_count(), 0)

    def test_manifest_release_is_read_only_from_the_top_level_field(self) -> None:
        manifest_path = self.repository / ".repository-standards.json"
        manifest_path.write_text(
            '''{
  "metadata": {"standards-release": "9.9.9"},
  "standards-release":
    "3.1.0"
}
''',
            encoding="utf-8",
        )

        json_result = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v3.2.0"
        )

        manifest_path.unlink()
        (self.repository / ".repository-standards.yml").write_text(
            '''  "standards-release": "3.1.0"
  metadata:
    standards-release: 9.9.9
''',
            encoding="utf-8",
        )
        yaml_result = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v3.2.0"
        )

        for result in (json_result, yaml_result):
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "3.2.0\n")
            self.assertEqual(result.stderr, "")

    def test_failed_request_and_invalid_final_urls_remain_silent(self) -> None:
        failed = self.run_discovery("", curl_exit=22)
        wrong_repository = self.run_discovery(
            "https://github.com/example/project/releases/tag/v9.0.0"
        )
        prerelease = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v9.0.0-rc.1"
        )
        malformed = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v9.0"
        )

        for result in (failed, wrong_repository, prerelease, malformed):
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")
        self.assertEqual(self.request_count(), 4)

    def test_same_session_adoption_suppresses_the_cached_notice(self) -> None:
        discovery = self.run_discovery(
            "https://github.com/lutzseverino/repository-standards/releases/tag/v3.2.0"
        )
        self.assertEqual(discovery.stdout, "3.2.0\n")

        self.manifest["standards-release"] = "3.2.0"
        self.write_manifest()
        notice = self.run_discovery(
            "unused because notice rendering must stay offline",
            "--notice",
            "3.2.0",
        )

        self.assertEqual(notice.returncode, 0)
        self.assertEqual(notice.stdout, "")
        self.assertEqual(notice.stderr, "")
        self.assertEqual(self.request_count(), 1)


if __name__ == "__main__":
    unittest.main()
