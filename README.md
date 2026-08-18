<div align="center">
  <h1>Repository Standards</h1>
  <p>Conventions, profiles, and synchronization tooling for repositories maintained by Lutz Severino.</p>

  [![CI](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml/badge.svg)](https://github.com/lutzseverino/repository-standards/actions/workflows/ci.yml)
  [![Releases](https://img.shields.io/github/v/release/lutzseverino/repository-standards?color=2f3437)](https://github.com/lutzseverino/repository-standards/releases)
  [![License: MIT](https://img.shields.io/badge/license-MIT-2f3437)](LICENSE)
</div>

This public source of truth defines the common change workflow, repository
presentation, documentation structure, managed community files, and
ecosystem-specific build and CI baselines.

This repository is a standards and synchronization repository, not a universal
application skeleton. Product code and earned repository-specific tooling stay
owned by each repository.

## What belongs here

- exact managed files that should be identical everywhere;
- managed absences for retired files whose presence restores conflicting
  behavior;
- templates whose variables are explicit in a repository manifest;
- composable fragments such as common and ecosystem `.gitignore` blocks;
- written conventions that need human judgment;
- ecosystem profiles and starter examples;
- dependency-free audit and synchronization tools.

## Repository contract

Each participating repository carries `.repository-standards.json`:

```json
{
  "standards-version": 5,
  "standards-release": "4.0.0",
  "profiles": ["common", "documentation", "vite-react", "pnpm-workspace"],
  "boundaries": [
    {"path": ".", "type": "repository", "title": "Product"},
    {"path": "apps", "type": "collection", "title": "Applications"},
    {"path": "apps/web", "type": "project", "title": "Product Web"}
  ],
  "dependency-updates": [
    {"ecosystem": "github-actions", "directory": "/", "schedule": "weekly"},
    {"ecosystem": "npm", "directory": "/", "schedule": "weekly"}
  ],
  "github": {
    "repository": "example/product",
    "default-branch": "main",
    "settings": {
      "delete-branch-on-merge": true,
      "allow-squash-merge": true,
      "allow-merge-commit": false,
      "allow-rebase-merge": false,
      "squash-merge-commit-title": "PR_TITLE",
      "squash-merge-commit-message": "PR_BODY"
    },
    "features": {
      "issues": true,
      "projects": false,
      "wiki": false
    },
    "ruleset": {
      "name": "Protect main",
      "required-status-checks": ["CI / Required"],
      "require-current-branch": true,
      "required-approvals": 0,
      "allowed-merge-methods": ["squash"],
      "prevent-deletion": true,
      "prevent-force-push": true,
      "allow-bypass-actors": false
    }
  },
  "variables": {},
  "local-fragments": {
    ".gitignore": [".repository-standards/gitignore.local"]
  },
  "repository-owned": [
    "README.md",
    "LICENSE",
    "CONTEXT.md",
    "docs/README.md",
    "docs/agents/domain.md",
    "docs/adr/**",
    "docs/how-to/**",
    "apps/**",
    "src/**"
  ]
}
```

The manifest is the ownership boundary. Files emitted by selected profiles are
managed. Paths listed under `repository-owned` cannot be emitted by a profile.
Everything else remains untouched. Declared boundaries make repository-owned
README and documentation structure auditable without making their prose a
managed copy. Declaring the exact `CHANGELOG.md` path as repository-owned also
opts into changelog structural audit; repositories without versioned consumers
may omit both the declaration and file.

Version 5 requires the `common` and `documentation` profiles and a GitHub
contract whose ruleset does not define bypass actors. Set
`allow-bypass-actors` to `false`; actor identities are not yet part of the
manifest contract. This keeps the family-wide workflow, repository-local agent
skills, agent configuration, required labels, repository settings, and
documentation boundary auditable.

JSON is canonical because the tools can read it with the Python standard
library. YAML manifests are also accepted when PyYAML is installed. The JSON
Schema in `schema/repository-standards.schema.json` documents the contract;
local validation does not depend on network access.

`standards-version` is the integer compatibility version of the manifest and
sync protocol. `standards-release` is the exact semantic version of the
standards content being adopted. Audit with the matching checkout or tag of
this repository.

## Use

Requires Python 3.11 or later.

```sh
scripts/audit /path/to/repository
scripts/audit-live /path/to/repository
scripts/sync /path/to/repository
scripts/sync --write /path/to/repository
scripts/sync-live /path/to/repository
scripts/sync-live --write /path/to/repository
```

`audit` reports drift and exits non-zero. `sync` previews the same plan and
unified diffs. `sync --write` changes managed targets only. It refuses a plan
that conflicts with a `repository-owned` path.

`audit-live` is deliberately separate: it requires an authenticated GitHub CLI
and renders the shared live desired-state delta for required labels, declared
repository settings and features, and the named ruleset. `sync-live` previews
operations projected from that same delta, and `sync-live --write` applies
them. Extra labels, rulesets, and undeclared live resources remain untouched.
Repository features default to Issues enabled and Projects and Wiki disabled;
declare `github.features` to record intentional use. Repositories that cannot
use rulesets may declare `"ruleset": null` while retaining auditable repository
settings, features, and labels.

GitHub omits ruleset bypass actors from read responses unless the caller has
write access to the ruleset. A complete live audit of a declared ruleset
therefore requires Administration write permission and fails rather than
reporting false conformance when that field is not observable.

Participating repositories receive the user-invoked
`adopt-repository-standards` skill. Give it an exact stable version for a
reproducible adoption, or omit the version to select the latest stable GitHub
Release. It previews offline and live changes, applies them with that release's
own tools, runs the repository's canonical validation and both audits, and
leaves the prepared changes uncommitted.

Run the canonical validation gate with:

```sh
scripts/check
```

## Profiles

| Profile | Use |
| --- | --- |
| `agent-skills` | Standard repository-local agent skills; inherited by `common` |
| `repository-lifecycle-skills` | Family-owned adoption skills; inherited by `common` |
| `common` | Every participating repository |
| `documentation` | Repositories using the shared Diataxis documentation set |
| `node-npm` | Standalone npm install units |
| `vite-react` | React applications built with Vite |
| `pnpm-workspace` | pnpm workspaces and install units |
| `spring-boot` | Spring Boot services and platforms |
| `paper-plugin` | Paper server plugins |
| `node-protocol` | Node.js protocol and schema packages |
| `tauri` | Tauri desktop applications |
| `codex-skill` | Codex skill repositories |

Profiles are additive. For example, a pnpm monorepo containing Vite apps and a
Spring service can select `common`, `pnpm-workspace`, `vite-react`, and
`spring-boot`, plus `documentation` for its repository and project docs roots.

## Documentation

See the [documentation index](docs/README.md) for the standards guides,
boundary conventions, and canonical authoring templates.

## Maintenance and rollout

Participating repositories have no runtime or build dependency on this
repository. Managed outputs, including standard agent skills, are vendored
into each repository, so its build, CI, contribution workflow, and history
remain self-contained.

A standards change is reviewed here, recorded in `CHANGELOG.md`, assigned a
semantic release, and tagged. Every pushed stable tag publishes a GitHub
Release with notes from its matching changelog section. Consumers can inspect
the public release history and check out an exact stable tag without private
credentials. Adoption remains deliberate: update the target manifest's
`standards-release` through the user-invoked lifecycle skill, review its offline
and live previews, and let it prepare the changes with the exact release's own
tools. The introducing release uses the documented manual bootstrap because
older repositories do not yet contain the skill.

See [Maintenance and rollout](standards/maintenance-and-rollout.md) for the
versioning and adoption procedure.

## Scope of automation

The tools deliberately do not rewrite product READMEs, build manifests, source
trees, release workflows, or documentation indexes. They render Dependabot
configuration from structured manifest data, manage repository-family agent
configuration, remove only exact paths explicitly declared absent, and mutate
only the live GitHub resources declared by the manifest and profiles. README and
documentation boundaries are structurally audited while their content is
maintained with repository-aware judgment.

## License

Distributed under the [MIT License](LICENSE). Public distribution keeps the
repository's existing commit history and author metadata intact.
