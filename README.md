<div align="center">
  <h1>Repository Standards</h1>
  <p>An opinionated, harness-portable repository environment for GitHub projects.</p>

  [![CI](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml)
  [![Releases](https://img.shields.io/github/v/release/lutzseverino/repository-standards?color=2f3437)](https://github.com/lutzseverino/repository-standards/releases)
  [![License: MIT](https://img.shields.io/badge/license-MIT-2f3437)](LICENSE)
</div>

Repository Standards gives unrelated maintainers a recognizable repository
environment they may deliberately adopt. It standardizes the canonical change
workflow, repository presentation, documentation structure, agent guidance,
public lifecycle interfaces, and declared GitHub behavior. Participating
repositories remain release-pinned and self-contained: managed artifacts are
copied into each repository rather than loaded as a runtime dependency.

Product implementation, application architecture, package policy, and
repository-owned tooling remain owned by each participating repository. The
mandatory repository environment and canonical workflow do not turn
Repository Standards into a product scaffold. Repositories may add
supplementary workflows without replacing the canonical workflow. Alternative
workflow sets and community templates are future directions, not selectable
interfaces today.

## Quick start

Python 3.11 or later and an authenticated GitHub CLI are required for commands
that inspect or change declared GitHub state. Linux, macOS, and WSL are
supported. Native Windows is unsupported future work.

```sh
scripts/standards --help
scripts/standards check /path/to/repository
scripts/standards repair /path/to/repository
scripts/standards create --help
scripts/standards publish /path/to/repository
scripts/standards adopt VERSION --repository /path/to/repository
```

`check` is read-only. It reports `standards-complete`,
`not-standards-complete`, or `unverified` with exit status 0, 1, or 2.
Default human output leads with the conclusion, compact evidence counts, and
actionable differences, gaps, corrections, and maintainer work. Add
`--verbose` to include complete satisfied and preservation evidence, or
`--json` to consume the stable complete automation contract. `repair` shows
the assessment before applying safe automatic corrections, then assesses the
repository again. Restricted `--scope content` and `--scope github` operations
remain unverified at the whole-repository level.

The remaining executable goals perform distinct repository transitions:

- `create` produces a prepared creation baseline;
- `publish` performs first publication after exact proposal confirmation;
- `adopt` creates a validated standards-adoption commit.

GitHub delivery is agent-owned because it requires judgment across current
pull-request, review, CI, and tracker state. Invoke the repository-local
`$deliver-change` Agent Skill to carry a validated commit through its exact
proposal and confirmation boundary. It is not advertised as a command stub.

Run this repository's complete change-validation gate with:

```sh
scripts/validate
```

## Repository contract

Each participating repository carries `.repository-standards.json`. Its exact
release, selected profiles, ownership boundaries, dependency-update policy,
and declared GitHub settings determine the applicable repository contract.
JSON is canonical and dependency-free; the schema is published at
[`schema/repository-standards.schema.json`](schema/repository-standards.schema.json).

The manifest distinguishes two versions:

- `standards-version` identifies the compatibility of the manifest protocol;
- `standards-release` pins the exact immutable standards content and tooling.

The selected release must perform assessment and repair. Repository-owned
paths and undeclared GitHub resources remain untouched.

## Profiles

Every repository selects `common` and `documentation`. Additional profiles add
observable repository-environment behavior and may provide guidance; they do
not govern product implementation:

| Profile | Applies to |
| --- | --- |
| `node-npm` | standalone npm install units |
| `vite-react` | React applications built with Vite |
| `pnpm-workspace` | pnpm workspaces and install units |
| `spring-boot` | Spring Boot services and platforms |
| `paper-plugin` | Paper server plugins |
| `node-protocol` | Node.js protocol and schema packages |
| `tauri` | Tauri desktop applications |
| `codex-skill` | Codex skill repositories |

The common profile also distributes the standard agent-skill bundle and the
repository lifecycle adapters.

## Documentation

- [Contributing](CONTRIBUTING.md) owns the ordinary change workflow.
- [Repository lifecycle](standards/repository-lifecycle.md) owns conformance
  and repository-transition policy.
- [Maintenance and rollout](standards/maintenance-and-rollout.md) owns release
  and migration policy.
- [Documentation index](docs/README.md) links the remaining standards,
  templates, domain language, and architectural decisions.

## License

Distributed under the [MIT License](LICENSE).
