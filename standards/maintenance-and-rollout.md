# Maintenance and rollout

## Operating model

`repository-standards` is a source of truth used at maintenance time. It is not
a runtime service, build dependency, Git submodule, package dependency, or
private reusable-workflow dependency.

Managed files are copied into participating repositories and committed there.
Each repository therefore remains self-contained: contributors can read its
workflow, CI can run, and public builds can complete without access to this
private repository.

## Two versions with different jobs

`standards-version` is an integer compatibility version for the repository
manifest and audit/sync protocol. Version `4` includes boundary declarations,
structured dependency updates, required live GitHub contracts, profile-owned
required labels, and managed absence. Increment it only for an incompatible
manifest or tooling contract.

`standards-release` is the exact semantic version of this repository's content,
also stored in `VERSION` and represented by a Git tag such as `v1.0.0`. Increment
it whenever managed content or normative guidance changes:

- patch: clarification or backward-compatible managed-file correction;
- minor: new backward-compatible standard, profile, or managed artifact;
- major: intentionally incompatible family convention or migration.

The standards release major and the manifest compatibility integer need not
move together. Repositories remain pinned to older tags until they deliberately
adopt a compatible manifest and content release.

## Publish a standards change

Standards changes use the normal issue and pull-request workflow.

1. Change the normative document, profile, managed file, schema, or tool.
2. Update tests and examples.
3. Record the user-visible change under `Unreleased` in `CHANGELOG.md`.
4. Choose the next semantic release and update `VERSION`.
5. Move changelog entries into the dated release section.
6. Merge only after CI passes, then tag the merged commit.

## Adopt a standards release

Rollout is deliberate and repository-aware:

1. Check out the intended `repository-standards` release tag.
2. Update the target's `standards-release` manifest field.
3. Run `scripts/audit /path/to/target` to inspect current drift.
4. Run `scripts/sync /path/to/target` and review every write and managed
   deletion in the preview.
5. Run `scripts/sync --write /path/to/target` to update managed files and remove
   exact paths declared absent.
6. Apply any repository-owned migration required by the written guidance.
7. Provision the canonical GitHub labels when the common profile is selected.
8. Run the target repository's canonical check and CI.
9. Run the standards audit once more and commit the self-contained result.
10. If the manifest declares GitHub settings, run `scripts/audit-live` after
    label and ruleset migration.

The sync tool never deploys, commits, pushes, opens pull requests, changes
GitHub settings, or schedules later work. Those actions remain explicit rollout
steps. A future orchestrator may automate preparation, but it must preserve the
same review and ownership boundaries.

## Drift checks

An audit is meaningful only when the standards checkout matches the manifest's
`standards-release`. The tool rejects a mismatch rather than silently comparing
against newer or older content.

Teams may run audits locally or in CI after making the private standards source
available. Target repository CI must not require private-source access for its
ordinary build and test gate.

Live audits require `gh` authentication and repository-settings visibility.
They are read-only and intentionally separate from offline managed-file audits.

The scheduled `Standards Audit` workflow covers participating repositories
accessible with its repository token. Private repositories owned elsewhere are
excluded until a dedicated read-only GitHub App or fine-grained token is
configured; personal maintainer tokens must not be reused as automation
credentials.
