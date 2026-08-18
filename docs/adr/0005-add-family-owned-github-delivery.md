# Add family-owned GitHub delivery

## Status

Accepted in [issue #23](https://github.com/lutzseverino/repository-standards/issues/23)

## Context

Implementation ends with a validated commit, while ordinary GitHub delivery
must carry that exact change through a pull request and into the default branch.
The repository family owns that policy, but the pinned external skill bundle
does not provide the operation.

## Decision

Provide ordinary GitHub delivery through a family-owned, user-invoked skill
whose interface follows the actor-neutral policy established by ADR 0004.
Delivery remains separate from implementation and has two phases:

- **Prepare** validates the exact candidate, preserves and restores the caller's
  local state, pushes the prepared head, and reuses or creates a ready pull
  request with unambiguous tracked-work links and the evidence needed for a
  merge decision.
- **Finalize** begins only after explicit human confirmation. It verifies the
  current head, canonical validation, checks, review evidence, mergeability,
  and repository merge policy before merging, reconciling tracked work, and
  performing safe branch cleanup while preserving unrelated caller state.

Both phases consume the normalized repository contract and shared live
desired-state delta wherever repository conformance is required as evidence.
Failed or stale validation, checks, review evidence, or mergeability return the
work to implementation with evidence; delivery does not edit implementation
work.

Observable forward tests of Prepare, Finalize, state preservation, failure
routing, and the confirmation seam are required before the delivery skill is
released. A deterministic delivery engine remains deferred until those tests
show which internal seams should be deepened.

This decision supersedes ADR 0001 where GitHub delivery is manual-only and ADR
0003 where delivery is excluded from the family-owned lifecycle bundle.

## Implementation status

At acceptance, the delivery skill had not been released.
[Issue #28](https://github.com/lutzseverino/repository-standards/issues/28)
was opened for its forward testing and prerequisite delivery-skill work.

## Consequences

- A pull-request reference identifies the delivery target but never authorizes
  a merge.
- Preparation and finalization expose one explicit human authorization boundary.
- Delivery failures preserve implementation ownership and provide evidence for
  the next implementation attempt.
- The family can deepen deterministic mechanics without reopening the accepted
  external interface.
