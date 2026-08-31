from __future__ import annotations

import os
import json
import re
import shlex
import shutil
import subprocess
import textwrap
from pathlib import Path

if __package__:
    from .lifecycle_support import LifecycleTestCase
else:
    from lifecycle_support import LifecycleTestCase


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_SOURCE = ROOT / "bootstrap"
PUBLIC_BOOTSTRAP_SOURCE = (
    "https://github.com/lutzseverino/repository-standards/tree/main/bootstrap"
)
CREATE_RESOLVER = BOOTSTRAP_SOURCE / "create-repository/scripts/select-release"
ADOPT_RESOLVER = BOOTSTRAP_SOURCE / "adopt-standards/scripts/select-release"
INSTALLER_VERSION = "1.5.23"


class BootstrapCreationJourneyTests(LifecycleTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.directory = self.workspace

    def create_release(self, version: str = "6.0.0") -> Path:
        release = self.directory / "release"
        for name in ("create-repository", "adopt-standards"):
            skill = release / f".agents/skills/{name}/SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text(
                f"---\nname: {name}\ndescription: release-owned {name}\n---\n",
                encoding="utf-8",
            )
        (release / "VERSION").write_text(version + "\n", encoding="utf-8")
        return self.seal_release(release, version)

    def create_source_release(self, version: str = "6.0.0") -> Path:
        release = self.directory / "source-release"
        shutil.copytree(
            ROOT,
            release,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        (release / "VERSION").write_text(version + "\n", encoding="utf-8")
        return self.seal_release(release, version)

    def create_fake_gh(self) -> tuple[Path, Path]:
        state = self.directory / "github.json"
        state.write_text(
            json.dumps(
                {
                    "created": False,
                    "repository": {},
                    "labels": [],
                    "branches": [],
                    "rulesets": [],
                }
            ),
            encoding="utf-8",
        )
        executable = self.write_executable(
            "gh",
            """\
                #!/usr/bin/env python3
                import json
                import os
                import sys

                state_path = os.environ["FAKE_GITHUB_STATE"]
                with open(state_path, encoding="utf-8") as handle:
                    state = json.load(handle)
                arguments = sys.argv[1:]

                def save():
                    with open(state_path, "w", encoding="utf-8") as handle:
                        json.dump(state, handle)

                if arguments[:2] == ["auth", "status"]:
                    raise SystemExit(0)
                if arguments[:2] == ["api", "user"]:
                    print(json.dumps({"login": "owner", "plan": {"name": "free"}}))
                    raise SystemExit(0)
                if arguments[:2] == ["repo", "create"]:
                    state["created"] = True
                    state["repository"] = {
                        "full_name": "owner/example",
                        "default_branch": None,
                        "delete_branch_on_merge": False,
                        "allow_squash_merge": True,
                        "allow_merge_commit": True,
                        "allow_rebase_merge": True,
                        "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
                        "squash_merge_commit_message": "COMMIT_MESSAGES",
                        "has_issues": True,
                        "has_projects": True,
                        "has_wiki": False,
                        "permissions": {"admin": True, "push": True},
                    }
                    save()
                    print("https://github.com/owner/example")
                    raise SystemExit(0)
                if not arguments or arguments[0] != "api":
                    print(f"unexpected gh invocation: {arguments}", file=sys.stderr)
                    raise SystemExit(2)

                endpoint = arguments[1]
                method = "GET"
                if "--method" in arguments:
                    method = arguments[arguments.index("--method") + 1]
                payload = json.load(sys.stdin) if "--input" in arguments else {}
                if endpoint == "repos/owner/example":
                    if not state["created"]:
                        print("HTTP 404: Not Found", file=sys.stderr)
                        raise SystemExit(1)
                    if method == "PATCH":
                        state["repository"].update(payload)
                        if payload.get("default_branch") == "main":
                            state["branches"] = [{"name": "main"}]
                        save()
                    print(json.dumps(state["repository"]))
                    raise SystemExit(0)
                if endpoint.startswith("repos/owner/example/branches"):
                    print(json.dumps(state["branches"]))
                    raise SystemExit(0)
                if endpoint.startswith("repos/owner/example/labels"):
                    if method == "POST":
                        state["labels"].append(payload["name"])
                        save()
                        print(json.dumps(payload))
                    else:
                        print(json.dumps([{"name": name} for name in state["labels"]]))
                    raise SystemExit(0)
                if endpoint.startswith("repos/owner/example/rulesets"):
                    if method == "POST":
                        ruleset = {
                            "id": 1,
                            "source_type": "Repository",
                            "source": "owner/example",
                            **payload,
                        }
                        state["rulesets"].append(ruleset)
                        save()
                        print(json.dumps(ruleset))
                    elif endpoint == "repos/owner/example/rulesets/1":
                        print(json.dumps(state["rulesets"][0]))
                    else:
                        print(json.dumps(state["rulesets"]))
                    raise SystemExit(0)
                if endpoint.startswith("repos/owner/example/pulls"):
                    print("[]")
                    raise SystemExit(0)
                print(f"unexpected gh api invocation: {arguments}", file=sys.stderr)
                raise SystemExit(2)
                """,
        )
        return executable, state

    def install_bootstrap(self, public_source_fixture: Path) -> tuple[Path, dict[str, str]]:
        user_home = self.directory / "user-home"
        user_home.mkdir()
        environment = self.isolated_environment(
            {
                "HOME": str(user_home),
                "XDG_CONFIG_HOME": str(user_home / ".config"),
                "XDG_CACHE_HOME": str(user_home / ".cache"),
                "XDG_STATE_HOME": str(user_home / ".local/state"),
                "npm_config_cache": str(self.directory / "npm-cache"),
                "npm_config_update_notifier": "false",
                "GIT_CONFIG_COUNT": "2",
                "GIT_CONFIG_KEY_0": (
                    f"url.{public_source_fixture.as_uri()}/.insteadOf"
                ),
                "GIT_CONFIG_VALUE_0": (
                    "https://github.com/lutzseverino/repository-standards.git"
                ),
                "GIT_CONFIG_KEY_1": "protocol.file.allow",
                "GIT_CONFIG_VALUE_1": "always",
            }
        )
        installed = subprocess.run(
            [
                "npx",
                "--yes",
                f"skills@{INSTALLER_VERSION}",
                "add",
                PUBLIC_BOOTSTRAP_SOURCE,
                "--skill",
                "create-repository",
                "--skill",
                "adopt-standards",
                "--global",
                "--agent",
                "universal",
                "--yes",
                "--copy",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(
            installed.returncode, 0, installed.stdout + installed.stderr
        )
        return user_home / ".agents/skills", environment

    def create_fake_git(self, remote: Path) -> tuple[Path, str]:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        fake_bin = self.directory / "fake-bin"
        fake_bin.mkdir()
        executable = fake_bin / "git"
        executable.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import os
                import sys

                arguments = sys.argv[1:]
                if "ls-remote" in arguments:
                    arguments = [
                        os.environ["FAKE_GIT_REMOTE"]
                        if value in {
                            "https://github.com/owner/example.git",
                            "https://github.com/owner/example",
                        }
                        else value
                        for value in arguments
                    ]
                if "push" in arguments:
                    arguments = [
                        os.environ["FAKE_GIT_REMOTE"] if value == "origin" else value
                        for value in arguments
                    ]
                os.execv(os.environ["FAKE_GIT_REAL"], ["git", *arguments])
                """
            ),
            encoding="utf-8",
        )
        executable.chmod(0o755)
        return fake_bin, real_git

    def test_quick_start_installs_only_the_two_user_scoped_bootstrap_skills(
        self,
    ) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        match = re.search(
            r"^npx skills add "
            r"https://github\.com/lutzseverino/repository-standards/tree/main/bootstrap"
            r" .+$",
            readme,
            flags=re.MULTILINE,
        )

        self.assertIsNotNone(match, "README quick start has no bootstrap installer")
        self.assertEqual(
            shlex.split(match.group(0)),
            [
                "npx",
                "skills",
                "add",
                "https://github.com/lutzseverino/repository-standards/tree/main/bootstrap",
                "--skill",
                "create-repository",
                "--skill",
                "adopt-standards",
                "--global",
            ],
        )

        discovered = {}
        for skill_file in BOOTSTRAP_SOURCE.glob("*/SKILL.md"):
            frontmatter = skill_file.read_text(encoding="utf-8").split("---", 2)[1]
            name = re.search(r"^name: (.+)$", frontmatter, flags=re.MULTILINE)
            self.assertIsNotNone(name, skill_file)
            discovered[name.group(1)] = skill_file.parent.name

        self.assertEqual(
            discovered,
            {
                "adopt-standards": "adopt-standards",
                "create-repository": "create-repository",
            },
        )

    def test_omitted_version_discloses_latest_release_and_delegates_to_it(
        self,
    ) -> None:
        release = self.create_release()
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(release),
            }
        )

        result = subprocess.run(
            ["python3", str(CREATE_RESOLVER)],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "Selected standards release: 6.0.0")
        self.assertEqual(lines[1], f"Release checkout: {release}")
        self.assertEqual(
            lines[2],
            f"Selected skill: {release}/.agents/skills/create-repository/SKILL.md",
        )

    def test_both_bootstraps_accept_only_explicit_exact_stable_releases(self) -> None:
        self.assertEqual(
            CREATE_RESOLVER.read_bytes(),
            ADOPT_RESOLVER.read_bytes(),
            "self-contained bootstrap resolvers must remain identical",
        )
        release = self.create_release()
        environment = os.environ.copy()
        environment["REPOSITORY_STANDARDS_CHECKOUT"] = str(release)

        for resolver, skill_name in (
            (CREATE_RESOLVER, "create-repository"),
            (ADOPT_RESOLVER, "adopt-standards"),
        ):
            with self.subTest(skill=skill_name):
                selected = subprocess.run(
                    ["python3", str(resolver), "6.0.0"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(
                    selected.returncode, 0, selected.stdout + selected.stderr
                )
                self.assertEqual(
                    selected.stdout.splitlines()[0],
                    "Selected standards release: 6.0.0",
                )
                self.assertIn(
                    f"/.agents/skills/{skill_name}/SKILL.md", selected.stdout
                )

                prerelease = subprocess.run(
                    ["python3", str(resolver), "6.0.0-rc.1"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(prerelease.returncode, 2)
                self.assertIn("exact stable semantic version", prerelease.stderr)

    def test_public_bootstrap_policy_preserves_release_and_publication_boundaries(
        self,
    ) -> None:
        lifecycle = (ROOT / "standards/repository-lifecycle.md").read_text(
            encoding="utf-8"
        )
        decision = (
            ROOT / "docs/adr/0015-bootstrap-through-thin-user-scoped-skills.md"
        ).read_text(encoding="utf-8")

        for text in (lifecycle, decision):
            self.assertIn("user-scoped", text)
            self.assertIn("create-repository", text)
            self.assertIn("adopt-standards", text)
            self.assertIn("exact immutable", text)
            self.assertIn("latest stable GitHub Release", text)
            self.assertIn("release-pinned", text)
        self.assertIn("first publication", lifecycle)
        self.assertIn("product scaffolding", lifecycle)
        self.assertIn(
            "0015-bootstrap-through-thin-user-scoped-skills.md",
            (ROOT / "docs/adr/README.md").read_text(encoding="utf-8"),
        )

    def test_clean_room_bootstrap_creates_then_publishes_a_complete_repository(
        self,
    ) -> None:
        release = self.create_source_release()
        gh, github_state = self.create_fake_gh()
        user_skills, environment = self.install_bootstrap(release)
        self.assertEqual(
            sorted(path.name for path in user_skills.iterdir()),
            ["adopt-standards", "create-repository"],
        )

        environment.update(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(release),
                "REPOSITORY_STANDARDS_GH": str(gh),
                "FAKE_GITHUB_STATE": str(github_state),
            }
        )
        selected = subprocess.run(
            [
                "python3",
                str(user_skills / "create-repository/scripts/select-release"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(selected.returncode, 0, selected.stdout + selected.stderr)
        self.assertEqual(
            selected.stdout.splitlines()[0],
            "Selected standards release: 6.0.0",
        )
        selected_skill = Path(
            next(
                line.removeprefix("Selected skill: ")
                for line in selected.stdout.splitlines()
                if line.startswith("Selected skill: ")
            )
        )

        destination = self.directory / "example"
        validation_program = (
            "from pathlib import Path; "
            "assert Path('README.md').is_file(); "
            "assert not Path('package.json').exists()"
        )
        created = subprocess.run(
            [
                "python3",
                str(selected_skill.parent / "scripts/create"),
                "--name",
                "example",
                "--purpose",
                "Prove public repository creation.",
                "--visibility",
                "public",
                "--license",
                "MIT",
                "--owner",
                "owner",
                "--destination",
                str(destination),
                "--validation-executable",
                "python3",
                "--validation-argument=-c",
                f"--validation-argument={validation_program}",
                "--fact",
                "ecosystem=unsupported",
                "--fact",
                "project-kind=repository",
                "--version",
                "6.0.0",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        self.assertIn("Prepared creation baseline", created.stdout)
        self.assertIn("first publication", created.stdout)
        manifest = json.loads(
            (destination / ".repository-standards.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["standards-release"], "6.0.0")
        self.assertEqual(
            manifest["canonical-validation"],
            {
                "executable": "python3",
                "arguments": ["-c", validation_program],
                "working-directory": ".",
            },
        )
        self.assertFalse((destination / "package.json").exists())
        self.assertNotEqual(
            subprocess.run(
                ["git", "-C", str(destination), "rev-parse", "--verify", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            ).returncode,
            0,
        )
        prepared = subprocess.run(
            [
                str(release / "scripts/standards"),
                "check",
                "--json",
                str(destination),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(prepared.returncode, 1, prepared.stdout + prepared.stderr)
        prepared_assessment = json.loads(prepared.stdout)
        self.assertTrue(prepared_assessment["differences"])
        self.assertTrue(
            all(item["pending"] for item in prepared_assessment["differences"])
        )

        remote = self.directory / "remote.git"
        subprocess.run(["git", "init", "--quiet", "--bare", str(remote)], check=True)
        fake_bin, real_git = self.create_fake_git(remote)
        environment.update(
            {
                "PATH": str(fake_bin) + os.pathsep + environment["PATH"],
                "FAKE_GIT_REAL": real_git,
                "FAKE_GIT_REMOTE": str(remote),
            }
        )
        subprocess.run(
            ["git", "-C", str(destination), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(destination), "config", "user.email", "test@example.com"],
            check=True,
        )
        publish_adapter = (
            destination
            / ".agents/skills/publish-repository/scripts/publish"
        )
        proposal = subprocess.run(
            [
                "python3",
                str(publish_adapter),
                str(destination),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(proposal.returncode, 0, proposal.stdout + proposal.stderr)
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in proposal.stdout.splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        published = subprocess.run(
            [
                "python3",
                str(publish_adapter),
                str(destination),
                "--confirm",
                confirmation,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(published.returncode, 0, published.stdout + published.stderr)
        self.assertIn("Standards-complete repository: owner/example", published.stdout)
        assessed = subprocess.run(
            [
                str(release / "scripts/standards"),
                "check",
                "--json",
                str(destination),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(assessed.returncode, 0, assessed.stdout + assessed.stderr)
        self.assertEqual(json.loads(assessed.stdout)["conclusion"], "standards-complete")
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(destination), "show", "-s", "--format=%s", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "chore: publish initial repository",
        )

    def test_clean_room_bootstrap_adopts_a_committed_unmanifested_repository(
        self,
    ) -> None:
        release = self.create_source_release()
        gh, github_state = self.create_fake_gh()
        state = json.loads(github_state.read_text(encoding="utf-8"))
        state.update(
            {
                "created": True,
                "repository": {
                    "full_name": "owner/example",
                    "default_branch": "main",
                    "delete_branch_on_merge": False,
                    "allow_squash_merge": True,
                    "allow_merge_commit": True,
                    "allow_rebase_merge": True,
                    "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
                    "squash_merge_commit_message": "COMMIT_MESSAGES",
                    "has_issues": True,
                    "has_projects": True,
                    "has_wiki": False,
                    "permissions": {"admin": True, "push": True},
                },
                "branches": [{"name": "main"}],
            }
        )
        github_state.write_text(json.dumps(state), encoding="utf-8")
        user_skills, environment = self.install_bootstrap(release)
        environment.update(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(release),
                "REPOSITORY_STANDARDS_GH": str(gh),
                "FAKE_GITHUB_STATE": str(github_state),
            }
        )
        selected = subprocess.run(
            [
                "python3",
                str(user_skills / "adopt-standards/scripts/select-release"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(selected.returncode, 0, selected.stdout + selected.stderr)
        self.assertEqual(
            selected.stdout.splitlines()[0],
            "Selected standards release: 6.0.0",
        )
        selected_skill = Path(
            next(
                line.removeprefix("Selected skill: ")
                for line in selected.stdout.splitlines()
                if line.startswith("Selected skill: ")
            )
        )

        repository = self.directory / "existing"
        (repository / "docs").mkdir(parents=True)
        (repository / "README.md").write_text(
            '<div align="center">\n  <h1>existing</h1>\n</div>\n\n'
            "See the [documentation](docs/README.md).\n",
            encoding="utf-8",
        )
        (repository / "docs/README.md").write_text(
            "# Documentation\n\nExisting project documentation.\n",
            encoding="utf-8",
        )
        (repository / "product.txt").write_text(
            "repository-owned product content\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(repository), "init", "-q", "-b", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "remote",
                "add",
                "origin",
                "https://github.com/owner/example.git",
            ],
            check=True,
        )
        subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "commit", "-qm", "existing project"],
            check=True,
        )
        original_head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        validation_program = (
            "from pathlib import Path; "
            "assert Path('product.txt').read_text() == "
            "'repository-owned product content\\n'; "
            "assert Path('.agents/skills/adopt-standards/SKILL.md').is_file()"
        )
        adapter = selected_skill.parent / "scripts/adopt"
        arguments = [
            "python3",
            str(adapter),
            "--repository",
            str(repository),
            "--validation-executable",
            "python3",
            "--validation-argument=-c",
            f"--validation-argument={validation_program}",
            "--fact",
            "ecosystem=unsupported",
            "--title",
            "existing",
            "6.0.0",
        ]
        proposal = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(proposal.returncode, 0, proposal.stdout + proposal.stderr)
        self.assertIn("Initial standards adoption proposal", proposal.stdout)
        self.assertIn("Selected exact release: 6.0.0", proposal.stdout)
        self.assertFalse(
            (repository / ".repository-standards.json").exists()
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            original_head,
        )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in proposal.stdout.splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        adopted = subprocess.run(
            [*arguments, "--confirm", confirmation],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(adopted.returncode, 0, adopted.stdout + adopted.stderr)
        self.assertIn("validated adoption commit", adopted.stdout)
        self.assertIn("GitHub delivery remains a separate", adopted.stdout)
        self.assertEqual(
            (repository / "product.txt").read_text(encoding="utf-8"),
            "repository-owned product content\n",
        )
        manifest = json.loads(
            (repository / ".repository-standards.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["standards-release"], "6.0.0")
        self.assertTrue(
            (repository / ".agents/skills/adopt-standards/SKILL.md").is_file()
        )
        self.assertTrue(
            (repository / ".agents/standard-skills.json").is_file()
        )
        self.assertTrue(
            (repository / ".claude/skills/adopt-standards/SKILL.md").is_file()
        )
        self.assertNotEqual(
            subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            original_head,
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repository), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
            "",
        )
        assessed = subprocess.run(
            [
                str(release / "scripts/standards"),
                "check",
                "--json",
                str(repository),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(assessed.returncode, 0, assessed.stdout + assessed.stderr)
        self.assertEqual(
            json.loads(assessed.stdout)["conclusion"], "standards-complete"
        )

    def test_clean_room_bootstrap_upgrades_the_preceding_stable_release(
        self,
    ) -> None:
        selected_release = self.create_source_release()
        preceding_release = self.directory / "preceding-release"
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--branch",
                "v5.0.0",
                "--single-branch",
                str(ROOT),
                str(preceding_release),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        gh, github_state = self.create_fake_gh()
        state = json.loads(github_state.read_text(encoding="utf-8"))
        state.update(
            {
                "created": True,
                "repository": {
                    "full_name": "owner/example",
                    "default_branch": "main",
                    "delete_branch_on_merge": True,
                    "allow_squash_merge": True,
                    "allow_merge_commit": False,
                    "allow_rebase_merge": False,
                    "squash_merge_commit_title": "PR_TITLE",
                    "squash_merge_commit_message": "PR_BODY",
                    "has_issues": True,
                    "has_projects": False,
                    "has_wiki": False,
                    "permissions": {"admin": True, "push": True},
                },
                "labels": [
                    "bug",
                    "enhancement",
                    "needs-triage",
                    "needs-info",
                    "ready-for-agent",
                    "ready-for-human",
                    "wontfix",
                ],
                "branches": [{"name": "main"}],
            }
        )
        github_state.write_text(json.dumps(state), encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "REPOSITORY_STANDARDS_GH": str(gh),
                "FAKE_GITHUB_STATE": str(github_state),
            }
        )

        repository = self.directory / "upgrade-example"
        (repository / "docs").mkdir(parents=True)
        (repository / ".agents/skills/custom").mkdir(parents=True)
        (repository / "README.md").write_text(
            '<div align="center">\n  <h1>upgrade-example</h1>\n</div>\n\n'
            "See the [documentation](docs/README.md).\n",
            encoding="utf-8",
        )
        (repository / "docs/README.md").write_text(
            "# Documentation\n\nExisting project documentation.\n",
            encoding="utf-8",
        )
        (repository / "product.txt").write_text(
            "repository-owned product content\n", encoding="utf-8"
        )
        (repository / ".agents/skills/custom/SKILL.md").write_text(
            "---\nname: custom\ndescription: repository-owned capability\n---\n",
            encoding="utf-8",
        )
        manifest = {
            "standards-version": 5,
            "standards-release": "5.0.0",
            "profiles": ["common", "documentation"],
            "boundaries": [
                {
                    "path": ".",
                    "type": "repository",
                    "title": "upgrade-example",
                }
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
                    "squash-merge-commit-title": "PR_TITLE",
                    "squash-merge-commit-message": "PR_BODY",
                },
                "features": {
                    "issues": True,
                    "projects": False,
                    "wiki": False,
                },
                "ruleset": None,
            },
            "variables": {},
            "local-fragments": {},
            "repository-owned": [
                "README.md",
                "docs/README.md",
                "product.txt",
            ],
        }
        (repository / ".repository-standards.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(repository), "init", "-q", "-b", "main"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.name", "Test User"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "config",
                "user.email",
                "test@example.com",
            ],
            check=True,
        )
        prepared = subprocess.run(
            [
                str(preceding_release / "scripts/standards"),
                "repair",
                str(repository),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "commit",
                "-qm",
                "adopt preceding stable standards",
            ],
            check=True,
        )
        preceding_check = subprocess.run(
            [
                str(preceding_release / "scripts/standards"),
                "check",
                "--json",
                str(repository),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(
            preceding_check.returncode,
            0,
            preceding_check.stdout + preceding_check.stderr,
        )
        self.assertEqual(
            json.loads(preceding_check.stdout)["conclusion"],
            "standards-complete",
        )
        original_head = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        user_skills, bootstrap_environment = self.install_bootstrap(selected_release)
        bootstrap_environment.update(environment)
        bootstrap_environment.update(
            {
                "REPOSITORY_STANDARDS_LATEST_RELEASE": "6.0.0",
                "REPOSITORY_STANDARDS_CHECKOUT": str(selected_release),
            }
        )
        selected = subprocess.run(
            [
                "python3",
                str(user_skills / "adopt-standards/scripts/select-release"),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=bootstrap_environment,
        )
        self.assertEqual(selected.returncode, 0, selected.stdout + selected.stderr)
        selected_skill = Path(
            next(
                line.removeprefix("Selected skill: ")
                for line in selected.stdout.splitlines()
                if line.startswith("Selected skill: ")
            )
        )
        validation_program = (
            "from pathlib import Path; "
            "assert Path('product.txt').read_text() == "
            "'repository-owned product content\\n'; "
            "assert Path('.agents/skills/custom/SKILL.md').is_file(); "
            "assert not Path('.agents/skills/ask-matt/SKILL.md').exists(); "
            "assert Path('.claude/skills/adopt-standards/SKILL.md').is_file()"
        )
        arguments = [
            "python3",
            str(selected_skill.parent / "scripts/adopt"),
            "--repository",
            str(repository),
            "--validation-executable",
            "python3",
            "--validation-argument=-c",
            f"--validation-argument={validation_program}",
            "6.0.0",
        ]
        proposal = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            env=bootstrap_environment,
        )
        self.assertEqual(proposal.returncode, 0, proposal.stdout + proposal.stderr)
        self.assertIn("Standards upgrade proposal", proposal.stdout)
        self.assertIn('"standards-release": "5.0.0"', proposal.stdout)
        self.assertIn('"standards-release": "6.0.0"', proposal.stdout)
        self.assertIn('"evidence-gaps": []', proposal.stdout)
        self.assertIn('"required-maintainer-work": []', proposal.stdout)
        for migrated_surface in (
            "canonical-validation",
            ".agents/standard-skills.json",
            ".claude/skills/adopt-standards/SKILL.md",
            ".agents/skills/ask-matt/SKILL.md",
            ".agents/skills/adopt-standards/SKILL.md",
        ):
            self.assertIn(migrated_surface, proposal.stdout)
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            original_head,
        )
        confirmation = next(
            line.removeprefix("Exact confirmation required: ")
            for line in proposal.stdout.splitlines()
            if line.startswith("Exact confirmation required: ")
        )
        upgraded = subprocess.run(
            [*arguments, "--confirm", confirmation],
            check=False,
            capture_output=True,
            text=True,
            env=bootstrap_environment,
        )
        self.assertEqual(upgraded.returncode, 0, upgraded.stdout + upgraded.stderr)
        self.assertIn("validated adoption commit", upgraded.stdout)
        self.assertIn("GitHub delivery remains a separate", upgraded.stdout)
        upgraded_manifest = json.loads(
            (repository / ".repository-standards.json").read_text(encoding="utf-8")
        )
        self.assertEqual(upgraded_manifest["standards-version"], 5)
        self.assertEqual(upgraded_manifest["standards-release"], "6.0.0")
        self.assertEqual(
            upgraded_manifest["canonical-validation"],
            {
                "executable": "python3",
                "arguments": ["-c", validation_program],
                "working-directory": ".",
            },
        )
        self.assertTrue(
            (repository / ".agents/skills/custom/SKILL.md").is_file()
        )
        self.assertFalse(
            (repository / ".agents/skills/ask-matt/SKILL.md").exists()
        )
        self.assertTrue(
            (repository / ".claude/skills/adopt-standards/SKILL.md").is_file()
        )
        current_inventory = json.loads(
            (repository / ".agents/standard-skills.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(current_inventory["bundles"][0]["skills"]),
            {
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
            },
        )
        assessed = subprocess.run(
            [
                str(selected_release / "scripts/standards"),
                "check",
                "--json",
                str(repository),
            ],
            check=False,
            capture_output=True,
            text=True,
            env=bootstrap_environment,
        )
        self.assertEqual(assessed.returncode, 0, assessed.stdout + assessed.stderr)
        self.assertEqual(
            json.loads(assessed.stdout)["conclusion"], "standards-complete"
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repository), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
            "",
        )
        self.assertEqual(
            subprocess.run(
                ["git", "-C", str(repository), "rev-list", "--count", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "2",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
