# Changelog

All notable changes to the repository standards are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and standards releases use semantic versioning.

## [Unreleased]

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
