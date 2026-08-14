# Versioning and releases

## Versioning

Use Semantic Versioning for published software and independently consumable
packages. Before `1.0.0`, document compatibility expectations explicitly; a
zero major version does not make breaking changes harmless.

Non-published repositories, websites, and operational skill packages do not
need artificial release numbers or a changelog. They still use Conventional
Commits. A repository opts into the changelog contract by declaring the exact
`CHANGELOG.md` path under `repository-owned`; canonical audit then validates
its structure.

## Release source

- A release is built from a commit already merged to `main`.
- The tag and build metadata agree on the version.
- CI passes before release automation begins.
- Release artifacts are produced by automation, not uploaded from an
  unverified local build.
- Repository-specific publishing destinations remain explicit.

Use annotated tags in the form `vMAJOR.MINOR.PATCH` unless an ecosystem has an
established incompatible convention. Do not move or reuse a published tag.

## Changelog and notes

Human-facing release notes explain outcomes, compatibility, migrations, and
known limitations. A generated commit list may supplement but not replace that
information for material releases.

Keep a changelog when the repository has consumers who need to compare
versions. The accepted structure is deterministic:

- exactly one root `# Changelog` title;
- exactly one `## [Unreleased]` section, before every release;
- release headings in newest-first semantic-version and ISO-date order, using
  `## [MAJOR.MINOR.PATCH] - YYYY-MM-DD`;
- `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`, and
  `Migration` categories only;
- no duplicate or empty categories; omit a category until it has content;
- optional reference-style comparison links.

Link issue or pull-request context where useful. Repositories without
versioned consumers may omit `CHANGELOG.md` entirely.

## Actions policy

- Release workflows are separate from `.github/workflows/ci.yml`.
- Use explicit least-privilege permissions.
- Pin third-party actions to full commit SHAs with a readable version comment.
- Use Dependabot to maintain GitHub Actions pins.
- Pin runners (`ubuntu-24.04` for Linux-only work) instead of relying on
  `ubuntu-latest`.
- Preserve ecosystem-specific signing, provenance, and destination behavior.
