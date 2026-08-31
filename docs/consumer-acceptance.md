# Consumer acceptance

Consumer acceptance journeys prove the public repository environment from
outside the standards source repository. They complement narrower behavioral
tests; they do not replace them.

## Deterministic journeys

`scripts/tests/test_bootstrap_creation.py` maintains three complete journeys:

- creation, structured canonical validation, first publication, and final
  repository assessment;
- initial adoption of a committed repository without a standards manifest,
  followed by validation and final assessment; and
- upgrade from the preceding stable release, including contract migration,
  validation, and final assessment.

Each journey gives the real `skills` installer the exact public bootstrap URL
shown in the README. A Git URL rewrite maps that clone boundary to an isolated
release fixture, so ordinary CI does not depend on mutable `main`. The
installed bootstrap skill selects an immutable release through its public
resolver. Release discovery and GitHub observation and writes are replaced at
their documented environment ports, while the installed skills and lifecycle
executables remain real. The tests invoke no lifecycle orchestration helper.

Every journey receives a new temporary `HOME`, XDG configuration, cache, and
state directory. Only `create-repository` and `adopt-standards` exist in its
user-scoped skill directory, so unrelated maintainer skills cannot affect the
result.

## Supported platforms

Required CI runs complete canonical validation, including the deterministic
consumer journeys, on Linux. A separate macOS job repeats those journeys
through the same public interfaces. WSL support means executing the Linux
toolchain inside WSL: Python, Node.js, Git, and GitHub CLI resolve and execute
the same literal process arguments and repository-relative paths covered on
Linux. There is no generally available hosted WSL runner, so Linux CI supplies
the automated WSL contract evidence and a release rehearsal may repeat the
command from WSL when that environment is available.

Native Windows is outside the supported matrix. CI has no native Windows job,
and Linux or WSL results must not be described as native Windows evidence.

## Fresh-agent interpretation

Fresh-agent tests are opt-in because they require authenticated harnesses:

```sh
RUN_FRESH_AGENT_TESTS=1 python3 -m unittest -v \
  scripts.tests.test_creation_fresh_agents \
  scripts.tests.test_adoption_fresh_agents \
  scripts.tests.test_claude_adapter_fresh_agents
```

The Codex journeys use `--ephemeral --ignore-user-config` and discover the
canonical Agent Skills path. The Claude journey uses project-only settings and
discovers `.claude/skills/create-repository`, follows its pointer to the
canonical `.agents` skill, and invokes that canonical skill's adapter. These
tests exercise skill interpretation rather than merely comparing adapter
files; deterministic contract tests separately reject adapter drift.

## Controlled live rehearsal

After an exact stable release is published and the demonstration repository
selects it, run the read-only live seam:

```sh
scripts/rehearse-public-contract VERSION \
  lutzseverino/repository-standards-demo
```

The rehearsal creates a clean temporary user environment, runs the documented
public installer, asks the installed bootstrap skill to select the supplied
immutable release, clones the demonstration repository, verifies that its
manifest selects the same release, and invokes that release's public
repository assessment against live GitHub state. It removes the temporary
checkout afterward and performs no repository or GitHub writes. Authentication
is carried into the clean environment as a process token obtained from
`GH_TOKEN`, `GITHUB_TOKEN`, or the active GitHub CLI account; it must provide the
observation permissions described by the repository lifecycle policy.

The separate `lutzseverino/repository-standards-demo` repository retains the
committed repository environment and declared live GitHub state for the
selected immutable release. The scheduled Standards Check assesses it with the
tooling selected by its own manifest. That ongoing observation makes drift
visible, but deterministic consumer journeys remain required and are the
ordinary CI gate for creation, initial adoption, and upgrade behavior.
