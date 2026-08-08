# Contributing

Thank you for improving this repository.

## Workflow

This repository uses the canonical manual Matt Pocock skills workflow. GitHub
Issues track incoming requests, published specifications, and generated
implementation tickets. They are not a required starting point for every
change.

The workflow follows the upstream skills at
[`84fdeffd`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502).
Repository documentation defines the full process in plain language; installed
skills provide its automated steps.

### Incoming requests

Use `/triage` for bugs and enhancement requests submitted outside the
repository's own planning flow. Incoming issues begin unlabelled. Triage assigns
exactly one category and one canonical state using the mapping in
`docs/agents/triage-labels.md`.

Do not run `/triage` on self-authored work.

### Self-authored work

Start at `/grill-with-docs` and choose the implementation rhythm by size:

```text
small build:
  /grill-with-docs -> /implement in the same context

multi-session build:
  /grill-with-docs -> /to-spec -> /to-tickets
    -> one fresh /implement <full issue URL> session per ticket
```

Work generated tickets blockers-first. `ready-for-agent` means that the work
needs no further triage; it is not a dispatch signal.

### Branch and implementation

Before `/implement`, branch from current `main`:

```text
<type>/<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`.

Use Conventional Commits:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

`/implement` changes the current branch, runs validation and review, and creates
a commit. It does not open or merge a pull request or close tracked work.

Run the single canonical validation command documented by this repository
before considering implementation complete.

### Manual GitHub delivery

After implementation:

1. Push the branch and open a pull request.
2. Use a Conventional Commit subject for the pull-request title.
3. Pass CI and complete any required review.
4. Squash merge the pull request and delete the branch.
5. Close the delivered implementation ticket after the change reaches `main`.
6. Close a parent specification after all of its implementation tickets are
   delivered.

A pull request may use closing references, but they are not required.
