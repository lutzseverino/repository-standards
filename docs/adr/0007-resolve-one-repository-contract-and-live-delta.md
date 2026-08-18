# Resolve one repository contract and live delta

## Status

Accepted in [issue #23](https://github.com/lutzseverino/repository-standards/issues/23)

## Context

Repository creation, offline synchronization, live audit, live writes, and
delivery had reconstructed overlapping knowledge from raw manifests, selected
profiles, repository policy, and GitHub state. Schema and runtime validation
could disagree, while separately derived audit findings and write operations
could describe different notions of conformance.

## Decision

Place repository-contract knowledge behind one deep interface. It validates and
normalizes release and protocol identity, resolved profiles, managed content
and ownership, required labels, dependency updates, boundaries, and the desired
GitHub contract for lifecycle callers. Raw manifest dictionaries and profile
loading order remain internal, and schema and runtime validation must agree at
this interface.

Place live comparison knowledge behind one live-reconciliation interface. It
accepts a normalized repository contract and one observed GitHub snapshot and
returns the complete live desired-state delta applicable to the repository's
lifecycle state. Audit renders that delta, synchronization applies it, and
lifecycle operations consume it as evidence instead of deriving separate
findings or write plans. Undeclared live resources remain preserved, and
application remains idempotent and reports partial progress without rollback.

The standards repository is subject to the same live contract as every other
participating repository. Live reconciliation is complete only when its actual
GitHub state is reconciled through the shared delta and a subsequent audit
proves conformance.

## Implementation status

Before this record was added,
[issue #24](https://github.com/lutzseverino/repository-standards/issues/24)
had delivered the normalized repository-contract interface, schema/runtime
parity, and complete offline synchronization planning before mutation.
[Issue #25](https://github.com/lutzseverino/repository-standards/issues/25)
was opened for the live-reconciliation interface and the migration of live
audit and synchronization to one shared delta.
[Issue #29](https://github.com/lutzseverino/repository-standards/issues/29)
was opened to reconcile this standards repository through that shared delta
and publish the hardened lifecycle after the dependent work is delivered.

## Consequences

- Contract changes have one validation and normalization seam shared by callers
  and behavioral tests.
- Live read and write paths cannot silently diverge in settings, label, ruleset,
  protection, or repository-feature semantics.
- An empty remote may report publication-dependent requirements as pending, but
  cannot pass as a standards-complete repository.
- GitHub access remains replaceable behind an adapter so reconciliation can be
  tested with observed snapshots and controlled writes.
