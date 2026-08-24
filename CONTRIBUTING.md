# Contributing

Thank you for improving this repository.

## Workflow

This repository uses the actor-neutral canonical repository workflow.
Repository documentation defines how work moves between states and how
validated changes reach GitHub.

The official Matt Pocock skill bundle at
[`84fdeffd`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502)
supplies pinned execution contracts. Its skills are execution adapters; they
do not define workflow policy.

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

### GitHub delivery

Use the family-owned `deliver-change` skill to execute its accepted phases. The
agent presents one exact lifecycle proposal and stops for explicit human
confirmation between preparation and finalization.

Prepare after implementation:

1. Validate the exact candidate, push the branch, and reuse and update its
   existing pull request or open a ready pull request. For tracked work,
   include an unambiguous non-closing link to the applicable incoming request,
   implementation ticket, or specification.
2. Use a Conventional Commit subject for the pull-request title.
3. Pass CI, complete any required review, and present the prepared head and
   current evidence for delivery.

Prepare stops for explicit human confirmation. A pull-request reference alone
does not authorize Finalize.

After confirmation, Finalize:

4. Reverify the prepared head, canonical validation, required checks, review
   evidence, mergeability, and repository merge policy. If that evidence is
   failed or stale, return the work and diagnostic evidence to implementation;
   delivery does not edit the implementation work.
5. Squash merge the pull request.
6. Reconcile the linked tracked work after the change reaches `main`, including
   an incoming request, implementation ticket, or directly implemented
   specification.
7. Close a parent specification after all of its implementation tickets are
   delivered.
8. Delete the merged branch.

Both phases preserve and restore unrelated local state.
Where repository conformance is required as evidence, both phases consume the
normalized repository contract and shared live desired-state delta.

Closing references may supplement but do not replace a required tracked-work
link.
