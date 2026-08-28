---
name: create-repository
description: Bootstrap a repository from an exact immutable standards release.
disable-model-invocation: true
---

# Bootstrap repository creation

Run `python3 scripts/select-release [VERSION]` from this skill directory.
Omit the version to select the latest stable GitHub Release, or supply an exact
stable semantic version. Disclose the resolver's exact selected version before
any repository or GitHub mutation.

Read and follow the `create-repository` skill from the selected release path
reported by the resolver. From that point, the selected release owns the
operation; this bootstrap skill adds no creation policy or product scaffolding.
Resolve every relative path in those instructions from the reported release
checkout. When invoking its adapter, set `REPOSITORY_STANDARDS_CHECKOUT` to the
reported checkout and pass the reported exact version with `--version`, even
when the original request omitted a version. Do not perform a second mutable
release lookup.
