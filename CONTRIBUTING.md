# Contributing

Thank you for improving this repository.

## Change workflow

The standard flow is:

```text
issue -> branch -> commits -> pull request -> CI/review -> squash merge
      -> delete branch
```

Material behavior, architecture, release, and tooling changes require an issue.
Automated dependency updates and genuinely trivial typo fixes are exceptions.

### Issue

Use the project-task form for planned work or the bug-report form for a defect.
Write a human-readable title in the form `[Area] Outcome` and make acceptance
and validation observable.

### Branch

Branch from current `main`:

```text
<type>/<issue-number>-<short-kebab-slug>
```

Allowed types are `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`,
`chore`, `perf`, and `revert`. Do not include the author, agent, or tool name in
the prefix.

### Commits and pull-request title

Use Conventional Commits:

```text
<type>(<optional-scope>)<optional-!>: <imperative lower-case summary>
```

The pull-request title follows the same format because it becomes the squash
commit subject. Use `!` and a `BREAKING CHANGE:` footer when applicable.

### Pull request

Open the pull request with `Closes #N` and complete Summary, Motivation, Impact,
and Validation. Keep the change focused and update tests and documentation with
the implementation.

Run the canonical validation command documented by this repository. CI must
pass before squash merge. Delete the branch after merge.
