# Contributing

Thank you for improving this repository.

## Workflow

This repository uses the canonical repository workflow. It composes the
official Matt Pocock skill bundle at
[`84fdeffd`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502).
The pinned skills define their execution contracts; repository documentation
defines how to route work between them and how to deliver validated changes
through GitHub.

GitHub Issues track incoming requests, published specifications, and generated
implementation tickets. They are not a required starting point for every
change. The examples below name skills without an agent-specific invocation
prefix; use the active agent's syntax, such as `$implement` in Codex.

### Incoming requests

Use `triage` for bugs and enhancement requests submitted outside the
repository's own planning flow. Incoming issues begin unlabelled. Triage assigns
exactly one category and one canonical state using the mapping in
`docs/agents/triage-labels.md`.

Do not run `triage` on self-authored work.

### Self-authored work

Start unresolved ideas with `grill-with-docs`, then choose the implementation
rhythm by size:

```text
small build:
  grill-with-docs -> implement in the same context

multi-session build:
  grill-with-docs -> to-spec -> to-tickets
    -> one fresh implement <full issue URL> session per ticket
```

Invoke `implement <reference>` directly when a specification or ticket is
already ready. Use `wayfinder` before this flow when a large effort still has
unresolved directional decisions.

Work generated tickets blockers-first. `ready-for-agent` means the work is
sufficiently specified for an agent to implement autonomously. Selecting and
starting that work remains an external dispatch action; this repository does
not provide an automatic pickup system.

### Branch and implementation

Before `implement`, branch from current `main`:

```text
<type>/<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`.

Use Conventional Commits:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

`implement` changes the current branch, runs validation and review, and creates
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
