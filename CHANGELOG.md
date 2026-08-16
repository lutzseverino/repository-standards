# Changelog

All notable changes to the repository standards are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and standards releases use semantic versioning.

## [Unreleased]

## [4.0.0] - 2026-08-16

### Added

- Distribute the dependency-free `adopt-repository-standards` lifecycle skill
  with previewed offline and live synchronization, exact-release tooling,
  complete validation, and uncommitted handoff.
- Add idempotent live preview and write commands for required labels,
  repository settings, and the manifest's named ruleset.
- Distribute session-level discovery of newer stable standards releases with a
  bounded silent check and one portable adoption notice.
- Add dependency-free changelog validation and stable release-note extraction.
- Publish stable tags through a GitHub Release workflow after validating the
  tag, source version, and matching changelog section.
- License the standards source for public distribution under the MIT License.

### Changed

- Make changelog structural audit an explicit opt-in through the exact
  repository-owned `CHANGELOG.md` path.
- Document public release consumption and recovery when a stable tag exists but
  GitHub Release creation fails.
- Document the one-time public rollout through the `v3.1.0` backfill, the
  introducing release, and manual downstream bootstrap handoffs.
- Advance the manifest compatibility contract to version `5` and reject bypass
  actors until the manifest can identify them explicitly. Because this is an
  incompatible contract change, the next stable release must be `4.0.0`.

### Fixed

- Reject symlinks in every ancestor of a managed target before audit or
  synchronization can follow them.
- Treat heading-like lines inside fenced changelog examples as literal content.
- Route manual GitHub Release recovery through the complete publication gate.
- Read only the manifest's top-level `standards-release` field during session
  release discovery, including multiline JSON and quoted YAML keys.
- Reconcile managed files and live GitHub state and run every completion check
  when adoption is invoked for the already-pinned release.
- Reject ignored managed absences before adoption can omit their deletion from
  its isolated preview.
- Audit unreleased changes in the standards source with current `main` tooling
  while keeping participating repositories pinned to their adopted releases.

### Migration

- Update manifests to `standards-version: 5` and set
  `github.ruleset.allow-bypass-actors` to `false`.
- Use the documented manual bootstrap for the release that introduces both the
  lifecycle skill and compatibility version `5`; later version-5 releases use
  the installed adoption skill.
- Remove or unignore any present path declared as a managed absence before
  rerunning standards adoption.

## [3.1.0] - 2026-08-13

### Added

- Distribute the official pinned `mattpocock-skills` bundle as repository-local
  managed files, with an explicit inventory and upstream license.
- Add managed tree expansion for exact profile-owned file collections.
- Set English as the default agent response language while permitting explicit
  and content-driven language changes.

### Changed

- Define the canonical repository workflow as family-owned orchestration around
  Matt Pocock's skill contracts, with entry points for ready and unresolved
  work.
- Define `ready-for-agent` as autonomous implementation readiness while keeping
  work selection and startup outside this repository's scope.

### Fixed

- Name every managed deletion in synchronization previews, including empty
  files, and report non-file managed absences as blocked.
- Authenticate scheduled live audits and run them from each repository's
  adopted standards release.

### Migration

- Update each target manifest to `standards-release: 3.1.0`, preview the
  synchronization, and commit the new `.agents/` inventory, license, and skill
  files with the other managed changes.
- Keep repository-local skills that do not collide with standard skill names;
  synchronized repositories do not need to run `setup-matt-pocock-skills`.

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
