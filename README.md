<div align="center">
  <h1>Repository Standards</h1>
  <p>Shared repository conventions, profiles, and lifecycle tooling for repositories maintained by Lutz Severino.</p>

  [![CI](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml)
  [![Releases](https://img.shields.io/github/v/release/lutzseverino/repository-standards?color=2f3437)](https://github.com/lutzseverino/repository-standards/releases)
  [![License: MIT](https://img.shields.io/badge/license-MIT-2f3437)](LICENSE)
</div>

Repository Standards is the public source of truth for the common change
workflow, repository presentation, documentation structure, managed community
files, and ecosystem-specific build and CI baselines. Participating
repositories remain self-contained: managed artifacts are copied into each
repository rather than loaded as a runtime dependency.

This is not a universal application skeleton. Product code and earned
repository-specific tooling remain owned by each participating repository.

## Quick start

Python 3.11 or later and an authenticated GitHub CLI are required for goals
that inspect or change declared GitHub state.

```sh
scripts/standards --help
scripts/standards check /path/to/repository
scripts/standards repair /path/to/repository
scripts/standards create --help
scripts/standards publish /path/to/repository
scripts/standards adopt VERSION --repository /path/to/repository
scripts/standards deliver /path/to/repository
```

`check` is read-only. It reports `standards-complete`,
`not-standards-complete`, or `unverified` with exit status 0, 1, or 2.
`repair` shows the complete repository assessment before applying safe
automatic corrections, then assesses the repository again. Restricted
`--scope content` and `--scope github` operations remain unverified at the
whole-repository level.

The remaining goals own distinct repository transitions:

- `create` produces a prepared creation baseline;
- `publish` performs first publication after exact proposal confirmation;
- `adopt` creates a validated standards-adoption commit;
- `deliver` carries a validated change through GitHub after exact proposal
  confirmation.

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
observable ecosystem behavior:

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

Distributed under the [MIT License](LICENSE).
