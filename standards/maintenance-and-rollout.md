# Maintenance and rollout

This document is the living owner of standards release and migration policy.
Repository conformance and transitions are defined in
[Repository lifecycle](repository-lifecycle.md).

## Operating model

`repository-standards` is a public maintenance-time source of truth, not a
runtime service, package dependency, submodule, or reusable-workflow
dependency. Managed files are copied into participating repositories and
committed there so each repository remains self-contained.

## Release identity

`standards-version` is the integer compatibility version of the repository
manifest. Increment it only when a release cannot interpret the preceding
manifest contract.

`standards-release` is the exact semantic version of published standards
content and tooling. It matches `VERSION`, an immutable annotated tag, and a
GitHub Release. Changes accumulate under `Unreleased` while `VERSION` continues
to identify the latest stable release.

- patch releases clarify or correct compatible standards;
- minor releases add compatible standards, profiles, or managed artifacts;
- major releases intentionally replace an incompatible family interface or
  convention.

The release major and manifest compatibility integer have different jobs and
need not advance together.

## Publish a standards release

Standards changes use the ordinary issue and pull-request workflow:

1. Change the normative document, profile, managed file, schema, or tool.
2. Update tests and examples.
3. Record user-visible changes under `Unreleased` in `CHANGELOG.md`.
4. Merge only after canonical validation and CI pass.

Prepare a release in a separate change:

1. Choose the semantic version and update `VERSION`.
2. Move `Unreleased` entries into a dated release section.
3. Merge after validation, then push an annotated stable tag for that exact
   commit.
4. Wait for release automation to publish the matching changelog section as a
   non-draft, non-prerelease GitHub Release.

Never move or reuse a pushed stable tag.

### Recover a failed release publication

Keep the existing tag fixed. Rerun a transient workflow failure. If the
automation itself cannot be rerun, fetch current remote evidence and use the
same publication gate:

```sh
git fetch origin main --tags
git checkout vMAJOR.MINOR.PATCH
GITHUB_REPOSITORY=OWNER/REPOSITORY \
  scripts/publish-release vMAJOR.MINOR.PATCH
```

The publisher requires an annotated tag on `origin/main`, successful required
CI, and coherent tag, `VERSION`, and changelog inputs. Correct a source defect
on `main` and publish a new version; never retarget the existing tag.

## Adopt a compatible release

Invoke `adopt-standards VERSION` in an existing repository for an exact stable
release, or omit `VERSION` to select the latest stable GitHub Release. Manifest
absence starts initial adoption; manifest presence starts an upgrade. The
adapter requires a clean, committed Git tree, obtains an isolated checkout of
the selected tag, and executes that release's adoption behavior.

Initial adoption and upgrades first render a complete proposal and perform no
mutation. An upgrade shows the current and selected manifest declarations plus
the selected release's normalized whole-repository assessment, including
validation migration, managed skills, harness adapters, retirements, lifecycle
interfaces, ownership conflicts, preservation evidence, and declared GitHub
changes. Only the exact confirmation from the current proposal authorizes
manifest migration, safe repository-environment and declared GitHub
corrections, canonical validation, final assessment, and the validated adoption
commit. GitHub delivery remains separate.

Repository-owned conflicts and manifest migrations remain explicit. Failed
validation or final assessment leaves applied changes uncommitted for
diagnosis. Partial application preserves successful work and supports an
idempotent retry.

## Bootstrap from v4 to the incompatible interface

The first release containing the six-goal task grammar requires a one-time
bootstrap because a v4 repository does not contain its current adoption
adapter. The bootstrap uses immutable release trees and leaves no compatibility
code in the new release:

1. Start from a clean, published repository pinned to `4.0.0`. Obtain exact,
   clean checkouts of tag `v4.0.0` and the new stable tag.
2. Compare the lifecycle-profile trees at those two immutable commits. Remove
   from the participating repository only adapter files that the newer tree
   deleted, then commit that mechanical bootstrap. Do not infer deletions from
   an untagged checkout.
3. From the new release checkout, invoke its current goal directly:

   ```sh
   /path/to/new-release/scripts/standards adopt NEW_VERSION \
     --repository /path/to/participating-repository \
     --validation-executable scripts/validate \
     [--validation-argument='LITERAL ARGUMENT' ...] \
     [--validation-working-directory RELATIVE/DIRECTORY]
   ```

4. Verify the resulting validated adoption commit with the new release's
   `standards check`, then use normal GitHub delivery.

This procedure is forward-tested from the v4 lifecycle-profile inventory. It
uses v4 only as immutable migration evidence and introduces no alias, wrapper,
or deprecated command into the new release.

## Assess released repositories

Assessment is meaningful only when the standards checkout matches the
manifest's `standards-release`; a mismatch is rejected. Ordinary target builds
and validation remain self-contained.

Checking declared GitHub state requires authentication and repository-settings
visibility. Ruleset assessment requires Administration write permission when
GitHub withholds bypass-actor data. Repair additionally requires Issues and
Administration write permissions.

The scheduled standards workflow lists only participating repositories already
migrated to the six-goal interface and checks each against its selected release.
Add a repository to that list only after its incompatible adoption lands. It
does not announce newer releases. The standards source is the development-time
exception: while changes are under `Unreleased`, its scheduled job uses current
`main` against the current source checkout.

Configure its `STANDARDS_CHECK_TOKEN` Actions secret with a fine-grained token
limited to every repository in the matrix. The token needs Contents read,
Issues read, and Administration write permission so the assessment can observe
branches, labels, repository settings, rulesets, and ruleset bypass actors. The
automatic `GITHUB_TOKEN` does not provide the complete Administration evidence
required for a `standards-complete` conclusion.
