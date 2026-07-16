# Repository workflow

## Standard flow

```text
issue -> branch -> commits -> pull request -> CI/review -> squash merge
      -> delete branch
```

Material behavior, architecture, release, and tooling changes start with an
issue. Automated dependency updates and genuinely trivial typo fixes are
explicit exceptions.

## Issue

Use the project-task form for planned changes. Its sections are Context,
Objective, Scope (Included and Excluded), Architecture Notes, Acceptance
Criteria, Validation, and Notes. Use the bug form when reproduction and
environment details are central.

Issue titles are human-readable:

```text
[Area] Outcome
```

## Branch

Branch from current `main`:

```text
<type>/<issue-number>-<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`.

```text
feat/123-secure-app-updates
fix/124-nullable-search-query
docs/125-standardize-readmes
ci/126-pin-actions
```

Do not encode the author, agent, or tool in the branch prefix.

## Commits and pull-request title

Use Conventional Commits 1.0.0:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

The pull-request title follows the same format because it becomes the durable
squash commit subject. Use `!` and a `BREAKING CHANGE:` footer for breaking
changes.

## Pull request

The standard body begins with `Closes #N`, then contains Summary, Motivation,
Impact, and Validation. Write `None` for genuinely absent user, operator, API,
compatibility, migration, or risk impact. Add Screenshots, Release note, or
Follow-ups only when earned.

CI must pass. Review is encouraged where it adds value. The solo-maintainer
baseline requires a pull request but zero mandatory approvals.

## Merge and repository settings

- allow squash merge only;
- use the pull-request title as the squash title;
- use the pull-request body as the squash message;
- automatically delete merged branches;
- require the `CI` and `PR Policy` checks before merge;
- require pull requests for `main`, with zero mandatory approvals;
- prevent force pushes and deletion of `main`;
- keep Issues enabled;
- disable Wiki and repository Projects unless actively used.

Dependabot branches are exempt from the issue-number branch convention. A
policy check may also exempt trusted automation while still validating human
pull requests.
