# Changelog

All notable changes to the repository standards are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and standards releases use semantic versioning.

## [Unreleased]

Implementation entries describe the existing lifecycle. The independent-profile
proof records accepted replacement direction, with earlier decisions reconciled
in [ADR 0017](docs/adr/0017-independent-profiles-and-shared-adoption.md#relationship-to-earlier-decisions);
production migration has not been implemented.

### Added

- Record the independent-author adoption proof and reconcile the replacement
  profile model, shared adoption boundary, retained pins, and discovery gaps
  before production ticketing.
- Preserve the tested policy-resolver model as historical evidence of pack and
  workflow selection, ownership, offline integrity, and `5.0.0` migration inputs.
  ADR 0017 supersedes its matrix and production-layout assumptions.
- Install only thin `create-repository` and `adopt-standards` bootstrap skills
  at user scope through the open Agent Skills installer, then resolve and
  disclose one immutable stable release before delegating creation or adoption
  to its release-owned skill.
- Prove the clean-room creation journey from isolated bootstrap installation
  through structured canonical validation, prepared creation, separate first
  publication, and the selected release's standards-complete assessment.
- Bootstrap initial adoption of a clean, committed repository without a
  standards manifest through a complete state-bound proposal, exact
  confirmation, release-pinned local environment installation, validation,
  final assessment, and a validated adoption commit.
- Exercise creation, initial adoption, and upgrade as clean-room consumer
  journeys through the documented public bootstrap installation, add macOS and
  fresh Claude-adapter evidence, and retain a controlled live rehearsal plus
  scheduled observation of the separate demonstration repository.

### Changed

- Adopt independently authored complete profiles and shared system skills as
  the replacement design, superseding the former pack/workflow/profile matrix
  and universal workflow closure. Tool and standards pins are independent;
  profile adoption leaves verified changes uncommitted.
- Simplify creation, adoption, and consumer-acceptance tests around shared
  lifecycle support for isolated environments, executable substitutes, and
  immutable release fixtures without changing their public journey coverage.
- In the existing lifecycle, compose applicable ecosystem profiles during initial
  contract selection, reject guidance-only profiles, and keep profile
  conformance limited to observable repository-environment behavior rather
  than product implementation conventions.
- In the existing lifecycle, curate the repository-local skill bundle to the canonical
  workflow's tested transitive closure, retire former managed skills through
  explicit absences, and add drift-checked Claude discovery adapters.
- Present issue-tracker, triage-label, and domain-documentation guidance as
  independent agent configuration without obsolete interactive setup
  commentary.
- Define Repository Standards as a harness-portable repository environment for
  unrelated GitHub maintainers, with explicit product-implementation,
  workflow-extension, and supported-platform boundaries.
- Make human repository assessments concise and actionable by default, add a
  verbose complete-evidence mode, and preserve complete JSON and exit meanings.
- Persist canonical validation as one executable, ordered literal arguments,
  and a safe repository-relative working directory; execute it without shell
  interpretation across creation, adoption, and delivery.
- Route `adopt-standards` by manifest presence so initial adoption reuses
  settled repository evidence and collects only unresolved contract facts,
  while upgrades now present current and selected manifest declarations plus a
  normalized whole-repository assessment of the complete contract change for
  exact confirmation before mutation.

### Fixed

- Preserve committed product symlinks in initial-adoption previews and
  revalidate the confirmed repository and GitHub assessment immediately before
  mutation.
- Accept expected default-branch and ruleset evidence that is pending first
  publication through a structured assessment field when creation verifies an
  otherwise reconciled prepared baseline.

### Removed

- Remove the non-operational `standards deliver` stub and present GitHub
  delivery through the repository-local `deliver-change` Agent Skill.

### Migration

- Upgrade repositories pinned to `5.0.0` through the same `adopt-standards`
  entry point, migrating the structured canonical-validation declaration,
  curated standard skill inventory, harness adapters, retired managed skills,
  and changed lifecycle surface in one forward-tested adoption commit. The
  manifest remains at `standards-version: 5`; no alias or permanent
  compatibility wrapper is retained.

## [5.0.0] - 2026-08-25

### Added

- Resolve manifest identity, profile inheritance, managed content, ownership,
  labels, boundaries, and GitHub declarations through one normalized
  repository-contract interface with schema and runtime parity.
- Build the complete offline repository-content preflight before mutation and
  report every deterministic blocker, previewed operation, and partial
  application result through shared plan semantics.
- Reconcile repository settings and features, required labels, and the named
  branch-protection ruleset through one shared declared GitHub reconciliation,
  including publication-pending and idempotent application evidence.
- Create prepared creation baselines with mandatory profiles and deterministic
  ecosystem-profile selection, leaving validated local content uncommitted and
  the GitHub repository empty for first publication.
- Publish prepared creation baselines through an explicit proposal and
  confirmation boundary that commits and publishes `main`, applies declared
  GitHub corrections, and verifies the standards-complete result.
- Add one repository-assessment interface and actor-neutral `standards check`
  and `standards repair` goals across repository content and declared GitHub
  state, including evidence-aware conclusions and safe partial recovery.
- Expose one `standards` task grammar for check, repair, create, publish, adopt,
  and deliver, backed by goal-oriented lifecycle skills and replaceable GitHub
  observation.
- Document and forward-test a one-time bootstrap from the immutable v4
  lifecycle profile into the current standards-adoption goal.
- Prove the complete public surface, retired-interface absence, and concrete
  fresh-agent maintainer goals in dedicated tests.
- Forward-test GitHub delivery preparation and confirmed completion through
  isolated repositories, controlled GitHub responses, and confirmation gates.

### Changed

- Make `scripts/validate` the canonical complete validation gate for standards
  changes and reserve standards-conformance conclusions for `standards check`.
- Record a successful standards adoption as its own validated commit while
  keeping GitHub delivery a separately confirmed lifecycle transition.
- Build repository-creation contracts through the selected release's
  `standards` executable while keeping contract construction private.
- Assign ordinary workflow, repository lifecycle, release and migration,
  orientation, and skill mechanics to distinct living documentation owners.

### Removed

- Remove the retired subject-specific command families, standalone manifest
  initializer, user-managed proposal records, and phase-specific command
  interfaces.
- Remove old lifecycle skill sources, aliases, managed-absence compatibility,
  public plan and delta types, legacy command implementations, and duplicate
  command-level test suites.

### Fixed

- Derive ignored managed-absence targets from structured
  repository-assessment correction evidence so adoption rejects a present
  ignored target before repair can delete it.
- Run the new repository's canonical validation before creation performs its
  first remote mutation.

### Migration

- Repositories pinned to `4.0.0` use the documented immutable-tree bootstrap,
  then invoke the new release's current `standards adopt` goal; the new release
  contains no permanent compatibility adapter.
- Keep manifest compatibility at `standards-version: 5`; this major release
  replaces the public lifecycle interface without introducing a new manifest
  protocol or a hypothetical future transition.

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
