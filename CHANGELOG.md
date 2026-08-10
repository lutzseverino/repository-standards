# Changelog

All notable changes to the repository standards are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and standards releases use semantic versioning.

## [Unreleased]

### Fixed

- Name every managed deletion in synchronization previews, including empty
  files, and report non-file managed absences as blocked.
- Authenticate scheduled live audits and run them from each repository's
  adopted standards release.

## [3.0.0] - 2026-08-08

### Added

- Added profile-owned canonical GitHub labels and read-only live label audits.
- Added managed absence so audit detects retired policy files and synchronization
  can preview and remove exact declared files.
- Added repository-family agent configuration for the GitHub issue tracker and
  canonical triage vocabulary.
- Added canonical language for complete standards adoption.
- Added `scripts/check` as this repository's complete local validation gate.

### Changed

- Replaced the issue-first workflow with the canonical manual Matt Pocock skills
  flow for incoming requests, self-authored planning, and implementation through
  a validated commit.
- Separated manual GitHub delivery and tracker reconciliation from
  implementation while retaining pull requests, CI, squash merge, Conventional
  Commits, and branch deletion.
- Changed branch names to `<type>/<short-kebab-slug>` so self-authored small work
  does not require an issue.
- Moved architectural decision records from `docs/decisions/` to `docs/adr/`
  while retaining the remaining Diataxis documentation structure.
- Bumped the manifest and synchronization compatibility version to `4`.
- Required version 4 manifests to select `common` and `documentation` and to
  declare the GitHub contract used by live label and repository audits.

### Removed

- Removed managed issue forms, the pull-request template, the pull-request
  policy workflow and checker, and the `PR Policy / Validate` required status.

### Fixed

- Run scheduled live GitHub audits for manifest compatibility version `4`,
  matching the contract required by this release.

### Migration

- Update manifests to `standards-version: 4` and `standards-release: 3.0.0`.
- Review the synchronization preview because write mode now removes exact paths
  declared absent; repository-owned guards and symlink protections still apply.
- Provision `bug`, `enhancement`, `needs-triage`, `needs-info`,
  `ready-for-agent`, `ready-for-human`, and `wontfix`, then run
  `scripts/audit-live`.
- Create the repository-owned `docs/agents/domain.md` configuration and a
  `CONTEXT.md` or `CONTEXT-MAP.md` only when the repository has resolved domain
  language.
- Replace `docs/_templates/decision.template.md` with
  `docs/_templates/adr.template.md` and move authored decision records to
  `docs/adr/`.

## [2.0.0] - 2026-07-21

### Added

- Added structured dependency-update declarations and deterministic Dependabot
  rendering.
- Added optional live GitHub settings contracts with a read-only authenticated
  auditor.
- Added a checksum-verified, pinned actionlint launcher for managed and
  repository-owned workflows.
- Added scheduled file, workflow, and live-settings drift audits for accessible
  participating repositories.

### Changed

- Defined one complete canonical validation gate and required split CI jobs to
  cover all of its constituent checks.
- Standardized the externally required checks as `CI / Required` and
  `PR Policy / Validate`; product jobs remain internal to their repositories.
- Made the pnpm CI example derive its pnpm version from the repository-owned
  `packageManager` declaration.
- Expanded shared pull-request policy tests to cover the complete valid and
  invalid human pull-request contracts.
- Bumped the manifest compatibility version to 3 for structured dependency
  updates and live GitHub declarations.

## [1.1.0] - 2026-07-17

### Added

- Declared repository, collection, and project README boundaries with
  executable presentation and documentation-navigation checks.
- Required repository and project documentation roots for manifest version 2.
- Project-agnostic examples for collection, project, and documentation indexes.

### Changed

- Established one canonical managed Diataxis template library per repository;
  monorepo projects keep scoped documentation without duplicating templates.
- Bumped the repository manifest compatibility version to 2 for required
  boundary declarations.

## [1.0.3] - 2026-07-16

### Changed

- Removed completed bootstrap-exception commentary from normative workflow and
  contribution guidance.

## [1.0.2] - 2026-07-16

### Fixed

- Exempt Dependabot pull requests by their stable PR author rather than the
  event actor, which may be a maintainer after an update-branch operation.

## [1.0.1] - 2026-07-16

### Fixed

- Build Java 17-compatible Paper plugins on JDK 21 so Google Java Format 1.35
  can run in CI and release workflows.

## [1.0.0] - 2026-07-16

### Added

- Common repository, contribution, issue, and pull-request conventions.
- README, documentation, workflow, versioning, and release standards.
- Profiles for Vite React, pnpm workspaces, Spring Boot, Paper plugins, Node
  protocol packages, Tauri applications, and Codex skills.
- A versioned repository manifest schema and examples.
- Explicit separation between manifest compatibility (`standards-version`) and
  pinned content adoption (`standards-release`).
- Dependency-free audit and synchronization tooling with ownership guards.
