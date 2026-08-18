# Assign repository lifecycle transitions explicitly

## Status

Accepted in [issue #23](https://github.com/lutzseverino/repository-standards/issues/23)

## Context

ADR 0003 leaves repository creation with uncommitted content and no published
branch while calling that result standards-complete. ADR 0005 starts ordinary
GitHub delivery from a validated commit and a pull-request-capable base branch.
Those operations cannot compose for an empty GitHub repository.

## Decision

Repository creation ends with a prepared creation baseline: validated,
uncommitted local content and an empty GitHub repository. It owns no commit,
push, pull request, merge, or delivery action and does not claim standards
completeness.

Define first publication as a separate actor-neutral lifecycle operation. Its
read-only **Plan** validates the prepared baseline and previews the initial
commit, publication and establishment of `main`, and the complete applicable
live desired-state delta. After explicit human confirmation, **Publish** checks
that the plan remains current, performs those operations in a valid order, and
re-observes the committed content and live state before reporting a
standards-complete repository. Partial failures retain successful work and
report completed, failed, and remaining operations without rollback.

A family-owned, user-invoked skill may execute first publication without
becoming its policy source. After successful publication, later changes use
implementation and ordinary GitHub delivery. Standards adoption owns explicit,
tested manifest-protocol transitions before a stable release introduces a
future incompatible protocol.

This decision supersedes ADR 0003 only where that record calls creation's
uncommitted, unpublished result standards-complete. Its no-commit and no-push
boundary remains in force.

## Implementation status

At acceptance, prepared creation and first publication had not been
implemented. [Issue #26](https://github.com/lutzseverino/repository-standards/issues/26)
was opened for prepared creation, and
[issue #27](https://github.com/lutzseverino/repository-standards/issues/27)
was opened for first publication.

## Consequences

- Empty-remote publication has one named owner and is not a special case of
  pull-request delivery.
- Standards completeness has one meaning: committed content and observed live
  state satisfy every applicable rule of the selected release.
- First publication must reject stale plans before mutation and report exact
  partial state after application-time failures.
- Future protocol changes cannot strand adopters behind an unnamed manual
  transition.
