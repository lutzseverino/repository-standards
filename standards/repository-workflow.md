# Repository workflow

## Canonical flow

The repository family owns one canonical repository workflow composed around
the official Matt Pocock skill bundle at
[`84fdeffd`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502)
and repository-family policy. The pinned skills define their execution
contracts. This document defines entry-point routing, readiness, branching,
validation, and GitHub delivery without attributing those additions to
upstream.

The common profile distributes the official 25-skill bundle as exact
repository-local files with source, revision, inventory, and license metadata.
It separately distributes the family-owned repository lifecycle bundle with
its own inventory and license. Lifecycle skills perform one user-invoked
standards operation and compose with, but do not select, the surrounding
workflow. The common profile also supplies the deterministic repository
configuration that the standard skills consume, so participating repositories
do not need to run `setup-matt-pocock-skills` after synchronization.

Skill names below omit the agent-specific invocation prefix. Use the active
agent's syntax, such as `$implement` in Codex.

The workflow separates implementation from GitHub delivery:

```text
incoming request -> triage -> ready work
unresolved idea -> grill-with-docs -> agreed work
agreed small change -> implementation -> validated commit
agreed multi-session change -> specification -> tickets -> implementation
ready specification or ticket -> implementation
huge unresolved effort -> wayfinder -> agreed work
validated commit -> pull request -> CI/review -> squash merge
                 -> tracker reconciliation -> delete branch
```

## Incoming requests

Incoming bugs and enhancement requests begin as blank, unlabelled GitHub
issues. `triage` assigns exactly one category and one state. Pull requests are
not an incoming-request or triage surface.

The common profile requires these categories:

- `bug`;
- `enhancement`.

It also requires these states:

- `needs-triage`;
- `needs-info`;
- `ready-for-agent`;
- `ready-for-human`;
- `wontfix`.

`ready-for-agent` means specification readiness: an agent can take the work and
implement it autonomously. Selection and startup are external dispatch actions;
the label does not provide an automatic pickup system or describe execution
state. Repositories may define additional labels.

## Self-authored work

Unresolved self-authored work begins with `grill-with-docs`, not triage.

```text
small build:
  grill-with-docs -> implement in the same context

multi-session build:
  grill-with-docs -> to-spec -> to-tickets
    -> one fresh implement <full issue URL> session per ticket
```

Invoke `implement <reference>` directly when a specification or ticket is
already ready. Use `wayfinder` first when a large effort still has unresolved
directional decisions.

Work implementation tickets blockers-first. Use native GitHub sub-issues and
dependencies where available. Planning skills may mark specifications and
tickets `ready-for-agent`; a human or separate orchestrator may select one for
autonomous implementation.

## Branch, commit, and implementation

Branch from current `main` before implementation:

```text
<type>/<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`.

Commits use Conventional Commits 1.0.0:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

`implement` works on the current branch, validates and reviews the change, and
creates a commit. It does not create a branch, open or merge a pull request, or
close tracked work.

Each repository documents one canonical local validation command. That command
is the complete merge-readiness gate; do not hide additional required checks
behind a second, stronger command. CI may split the gate into jobs, but those
jobs must collectively run every constituent check.

## Manual GitHub delivery

GitHub delivery begins after implementation:

1. Push the branch and open a pull request.
2. Use a Conventional Commit subject for the pull-request title so it becomes
   the squash commit subject.
3. Pass CI and complete any required review.
4. Squash merge the pull request.
5. Close the implementation ticket after its change reaches the default branch.
6. Close a parent specification after all of its implementation tickets are
   delivered.
7. Delete the merged branch.

Closing references are permitted but not required. Automated dependency-update
pull requests remain exempt from the human planning flow.

## Repository settings

- allow squash merge only;
- use the pull-request title as the squash title;
- use the pull-request body as the squash message;
- automatically delete merged branches;
- require `CI / Required` before merge;
- require pull requests for `main`, with zero mandatory approvals;
- prevent force pushes and deletion of `main`;
- keep Issues enabled;
- disable Wiki and repository Projects unless actively used.

The common profile declares the required label names. `scripts/audit-live`
checks their presence together with declared repository settings and rulesets.
Label provisioning remains a deliberate manual action.
