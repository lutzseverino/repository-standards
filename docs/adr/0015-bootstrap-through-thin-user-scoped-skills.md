# Bootstrap through thin user-scoped skills

## Status

Accepted in [issue #49](https://github.com/lutzseverino/repository-standards/issues/49)

## Context

A prospective adopter needs `create-repository` or `adopt-standards` before a
participating repository can provide repository-local Agent Skills. Installing
the substantive lifecycle bundle at user scope would make mutable global state
an unpinned policy source and would let repositories on different releases
interfere with one another. Requiring a Repository Standards source checkout
would preserve pinning but leave the public entry experience dependent on
source-repository knowledge.

## Decision

Publish only `create-repository` and `adopt-standards` as thin user-scoped
Agent Skills, installable from the dedicated `bootstrap` subtree with an
established Agent Skills installer. Each bootstrap selects one exact immutable
stable release, using an explicit stable semantic version when supplied and
otherwise resolving the latest stable GitHub Release. It discloses that exact
version before repository or GitHub mutation, verifies the matching clean tag
and `VERSION`, and delegates all substantive behavior to the selected
release's canonical skill.

The selected release creates or adopts the repository environment and installs
its release-pinned local workflow and lifecycle skills. The user-scoped skills
remain entry adapters only: they do not embed the current repository contract,
perform product scaffolding, or become the ongoing standards source. Creation
still ends at a prepared creation baseline; first publication remains a
separate release-owned transition.

## Consequences

- A prospective adopter can begin without a Repository Standards source
  checkout or a participating repository.
- Updating a global bootstrap cannot redefine an existing participating
  repository, whose local environment remains pinned to its adopted release.
- Release resolution and checkout are replaceable deterministic seams in CI;
  production resolution continues to use immutable Git tags and GitHub
  Releases.
- The public installer source must contain exactly the two bootstrap skills,
  while the repository-local bundle may contain the complete release-owned
  workflow and lifecycle closure.

## Supersedes

This decision supersedes ADR 0003 where initial use required a documented
manual source-checkout bootstrap. It complements ADR 0013's repository-local
skill curation and preserves its rejection of ongoing user-scoped policy.
