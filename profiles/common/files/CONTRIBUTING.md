# Contributing

Thank you for improving this repository. This file is the living owner of the
ordinary change workflow. Repository conformance and lifecycle transitions are
defined separately by the selected standards release.

## Start work

GitHub Issues track incoming requests, published specifications, and generated
implementation tickets. Incoming bugs and enhancements begin unlabelled and
use `triage` to receive exactly one canonical category and state. Self-authored
work does not pass through triage.

Start unresolved self-authored work with `grill-with-docs`, then choose a
rhythm that matches its size:

```text
small build:
  grill-with-docs -> implement in the same context

multi-session build:
  grill-with-docs -> to-spec -> to-tickets
    -> one fresh implement <full issue URL> session per ticket
```

Invoke `implement <reference>` directly when a specification or ticket is
already ready. Use `wayfinder` first when a large effort still has unresolved
directional decisions. Work generated tickets blockers-first.

`ready-for-agent` means the work is specified well enough for autonomous
implementation. Selecting and starting that work is a separate dispatch act.

## Implement a change

Branch from current `main` before implementation:

```text
<type>/<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`.

Use Conventional Commits:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

Keep changes scoped to their agreed work. Update tests and user-visible
documentation with the behavior. Record release-facing changes under
`Unreleased` in `CHANGELOG.md`.

Run the single canonical validation command before considering implementation
complete:

```sh
scripts/validate
```

`implement` changes the current branch, validates and reviews the work, and
creates a commit. It does not open or merge a pull request or reconcile tracked
work.

## Deliver a validated change

Use the repository's GitHub delivery operation after implementation. Follow
the transition and confirmation policy owned by the selected standards
release's Repository lifecycle guidance.

For tracked work, the pull request must contain an unambiguous non-closing link
to the applicable request, ticket, or specification. Its title must be a
Conventional Commit subject. Closing references may supplement but do not
replace the tracked-work link.
