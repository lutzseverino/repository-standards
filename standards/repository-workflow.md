# Repository workflow

## Canonical flow

The repository family uses the canonical manual Matt Pocock skills workflow.
The standard follows upstream commit
[`84fdeffd`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502)
and documents the full process locally. Installed skills automate parts of the
process but are not vendored into participating repositories.

The workflow separates implementation from GitHub delivery:

```text
incoming request -> triage -> ready work
self-authored work -> planning -> implementation -> validated commit
validated commit -> pull request -> CI/review -> squash merge
                 -> tracker reconciliation -> delete branch
```

## Incoming requests

Incoming bugs and enhancement requests begin as blank, unlabelled GitHub
issues. `/triage` assigns exactly one category and one state. Pull requests are
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

`ready-for-agent` means specification readiness: no further triage is needed.
It is not a dispatch signal and does not describe execution state. Repositories
may define additional labels.

## Self-authored work

Self-authored work begins with `/grill-with-docs`, not triage.

```text
small build:
  /grill-with-docs -> /implement in the same context

multi-session build:
  /grill-with-docs -> /to-spec -> /to-tickets
    -> one fresh /implement <full issue URL> session per ticket
```

Work implementation tickets blockers-first. Use native GitHub sub-issues and
dependencies where available. Planning skills may mark specifications and
tickets `ready-for-agent`; no automation starts work from that label.

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

`/implement` works on the current branch, validates and reviews the change, and
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
