# Replace the repository standards interface without deprecation

## Status

Accepted in [issue #35](https://github.com/lutzseverino/repository-standards/issues/35)
and implemented by
[issue #38](https://github.com/lutzseverino/repository-standards/issues/38).

## Context

The released interface exposed separate subject- and phase-oriented adapters.
Maintainers and agents had to learn implementation structure before they could
express repository-level goals, while retaining old adapters beside new ones
would preserve two mental models and duplicate their tests and maintenance.
Participating repositories pinned to version 4 still needed a safe path to the
incompatible release.

## Decision

Replace the released adapters with one repository-level `standards` task
grammar whose goals are `check`, `repair`, `create`, `publish`, `adopt`, and
`deliver`, plus goal-oriented lifecycle skills. Remove retired executables,
skill names, public plan and delta types, wrappers, compatibility branches,
and duplicate suites in the introducing major release.

Keep older releases executable at immutable tags. Support version 4
repositories through a documented, forward-tested, one-time bootstrap that
compares the immutable old and new managed trees, removes only retired managed
files, and invokes the new release's current adoption interface. Do not retain
that bootstrap as a permanent compatibility layer.

## Consequences

- Maintainers and agents encounter one predictable repository-level grammar.
- The cutover is deliberately breaking, so version 4 repositories must run the
  one-time bootstrap before adopting the new release.
- Historical behavior remains reproducible at immutable tags without requiring
  two interfaces to be maintained in the current release.

## Alternatives considered

- Deprecate the old adapters or retain aliases. Rejected because that would
  preserve the retired mental model and create an open-ended maintenance cost.
- Hide the old implementations behind a new facade. Rejected because duplicate
  implementations and behavioral suites would drift.
- Require version 4 repositories to reconstruct themselves manually. Rejected
  because the migration would not be safe or forward-testable.
