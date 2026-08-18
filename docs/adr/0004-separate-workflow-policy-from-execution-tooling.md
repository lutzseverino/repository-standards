# Separate workflow policy from execution tooling

## Status

Accepted in [issue #23](https://github.com/lutzseverino/repository-standards/issues/23)

## Context

ADR 0002 distinguishes repository-family policy from pinned external skill
contracts, but still defines the canonical workflow around that skill bundle.
The same repository states, authorization boundaries, and completion criteria
must apply when work is performed by humans, agents, or mixed teams.

## Decision

Define canonical workflow policy as an actor-neutral sequence of repository
states and operations. Repository policy owns the sequence, boundaries, and
acceptance criteria. Skills and other tools are execution adapters: they may
perform lifecycle operations, but their identity and internal procedure do not
define those operations.

Continue distributing the pinned external skill bundle and family-owned
lifecycle skills with distinct provenance. Changes to either execution
capability do not redefine the canonical workflow.

This decision supersedes ADR 0002 only where it defines the canonical workflow
around the external skill bundle.

## Consequences

- Workflow policy remains stable when its actors or tools change.
- Human and automated execution must satisfy the same state and authorization
  boundaries.
- Execution tooling can deepen independently while repository policy remains
  the authority for lifecycle behavior.
