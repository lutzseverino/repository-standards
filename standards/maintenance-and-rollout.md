# Maintenance and rollout

## Operating model

`repository-standards` is a public source of truth used at maintenance time.
It is not a runtime service, build dependency, Git submodule, package
dependency, or reusable-workflow dependency.

Managed files are copied into participating repositories and committed there.
Each repository therefore remains self-contained: contributors can read its
workflow, CI can run, and builds can complete without access to the standards
source.

## Two versions with different jobs

`standards-version` is an integer compatibility version for the repository
manifest and audit/sync protocol. Version `5` includes boundary declarations,
structured dependency updates, required live GitHub contracts without bypass
actors, profile-owned required labels, and managed absence. Increment it only
for an incompatible manifest or tooling contract.

`standards-release` is the exact semantic version of published repository
content, also stored in `VERSION` and represented by a Git tag such as
`v1.0.0`. Changes accumulate under `Unreleased` while `VERSION` continues to
identify the latest stable release. Release preparation increments it once for
all accumulated managed-content and normative-guidance changes:

- patch: clarification or backward-compatible managed-file correction;
- minor: new backward-compatible standard, profile, or managed artifact;
- major: intentionally incompatible family convention or migration.

The standards release major and the manifest compatibility integer need not
move together. Repositories remain pinned to older tags until they deliberately
adopt a compatible manifest and content release.

## Publish a standards change

Standards changes use the normal issue and pull-request workflow:

1. Change the normative document, profile, managed file, schema, or tool.
2. Update tests and examples.
3. Record the user-visible change under `Unreleased` in `CHANGELOG.md`.
4. Merge only after CI passes.

Prepare a release in a separate change after the intended changes accumulate:

1. Choose the next semantic release and update `VERSION`.
2. Move the `Unreleased` entries into the dated release section.
3. Merge only after CI passes, then push an annotated stable tag for the merged
   commit. The release workflow validates the tag, `VERSION`, and matching
   changelog release before publishing its section as the GitHub Release body.

Do not move or reuse a pushed stable tag. Publishing the repository must retain
its existing history and author metadata.

### Recover a tag whose release failed

If a stable tag exists but GitHub Release creation failed, keep the tag fixed.
For a transient GitHub or runner failure, rerun the failed workflow. If the
release automation itself cannot be rerun, fetch the current remote state and
route recovery through the same complete publication gate:

```sh
git fetch origin main --tags
git checkout vMAJOR.MINOR.PATCH
GITHUB_REPOSITORY=OWNER/REPOSITORY \
  scripts/publish-release vMAJOR.MINOR.PATCH
```

Replace `OWNER/REPOSITORY` with the repository's GitHub name. The publisher
requires an annotated tag on `origin/main`, a successful `CI / Required` check,
and coherent tag, `VERSION`, and changelog inputs before it creates the release.
If any gate fails, do not work around it and do not retarget the tag. Correct the
source on `main`, assign a new version, and publish a new stable tag.

## Adopt a standards release

Invoke `adopt-repository-standards VERSION` in the participating repository for
an exact stable release, or omit `VERSION` to select the latest stable GitHub
Release. The skill requires a clean Git tree, obtains an isolated checkout of
the exact tag, and uses that release's own tooling. It previews offline writes
and deletions plus live labels, settings, and the named ruleset before applying
them. The adoption is prepared only after the target's canonical validation and
the release's offline and live audits pass.

The skill leaves successful changes uncommitted and leaves the surrounding
workflow and GitHub delivery to the user. Repository-owned conflicts and
migrations stay explicit. Live application is idempotent; a partial failure
reports completed and remaining operations and preserves the applied state for
a safe rerun.

The release that first introduces the lifecycle bundle requires one manual
bootstrap. Check out that exact standards tag, update the target manifest,
preview and apply `scripts/sync`, preview and apply `scripts/sync-live`, then run
the target's canonical validation plus `scripts/audit` and `scripts/audit-live`.
Later releases use the installed adoption skill.

## Drift checks

An audit is meaningful only when the standards checkout matches the manifest's
`standards-release`. The tool rejects a mismatch rather than silently comparing
against newer or older content.

Teams may run audits locally or in CI from an exact public standards release.
Target repository CI remains self-contained for its ordinary build and test
gate.

Live audits require `gh` authentication and repository-settings visibility.
Live writes additionally require Issues and Administration write permissions.
Both operations remain intentionally separate from offline managed-file work.

The scheduled `Standards Audit` workflow covers participating repositories
accessible with its repository token. Repositories owned elsewhere are
excluded until a dedicated read-only GitHub App or fine-grained token is
configured; personal maintainer tokens must not be reused as automation
credentials.

The scheduled audit validates each repository against its adopted release. It
does not announce that a newer standards release is available; release
discovery and adoption remain separate maintenance work.

The standards source is the one development-time exception: while changes are
still under `Unreleased`, its scheduled job uses current `main` tooling against
the current source checkout. Every participating target continues to use the
exact stable tooling named by its manifest.
