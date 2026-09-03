# Separate the capability platform from policy packs

## Status

Accepted in the repository architecture design session completed on 2026-09-02
and recorded in
[issue #68](https://github.com/lutzseverino/repository-standards/issues/68).
The replacement specification will reconcile the existing issue tree before
implementation begins.

## Context

The current repository environment couples one mandatory workflow, managed
profiles, release-pinned skills, and lifecycle implementations into one
standards release. That makes the environment consistent, but it does not give
a maintainer a simple way to reuse the operational capabilities with different
repository policy or to share and fork a coherent policy setup.

Adding configurable packs beside the current resolution and skill-distribution
models would create competing sources of truth. The new model therefore needs
to replace those parts of the architecture rather than wrap them.

## Decision

Repository Standards has two product halves:

- a capability platform, which owns shared capability skills, deterministic
  resolution and mutation operations, and non-configurable safety boundaries;
- a policy system, whose versioned policy packs, workflow policies, ecosystem
  profiles, and repository-local choices describe desired repository behavior.

A policy pack is declarative. It can select and configure shared capabilities,
but it cannot contain, replace, or hide executable capabilities. New executable
behavior belongs to the platform or to an explicit extension capability.

Version one resolves exactly one primary policy pack, exactly one workflow
policy, zero or more ecosystem profiles, and zero or more declared local
choices. A policy pack may recommend a workflow or profiles, but workflow and
ecosystem selection remain orthogonal. Duplicate ownership, incompatible
selections, and ambiguous precedence are errors; there is no last-wins merge
and no composition of multiple primary policy packs. A maintainer who needs a
different primary policy authors or forks a pack.

Every operation consumes one normalized resolved repository contract. The
platform exposes that boundary through resolution, planning, application, and
explanation rather than allowing each skill or lifecycle operation to interpret
configuration independently.

Machine-evaluable facts have one structured owner in policy or repository
configuration. Judgment-based guidance has one authoritative policy document,
such as `CONTRIBUTING.md`. The resolved contract identifies applicable policy
documents, but deterministic tooling does not infer exact facts from prose.

The capability platform owns integrity and provenance checks, deterministic
resolution and conflict rejection, ownership preservation, preview and
confirmation boundaries, stale-state detection, literal process execution,
and truthful partial-progress reporting. Packs cannot weaken those guarantees.

The ordinary consumer surface remains inspectable: repository configuration is
the normal author-facing control, while locks, acquired packages, and generated
adapters are managed internals. The complete file layout, schemas, capability
inventory, and migration sequence belong to the replacement specification and
prototypes rather than this decision.

## Consequences

- Policy setups can be selected, authored, copied, and forked without forking
  the operational implementation.
- Shared skills such as assessment, repair, update, publication, planning, and
  delivery can work across compatible packs through the same contract.
- The source repository requires a material reorganization of profiles, skill
  inventories, registries, and lifecycle implementations. The old and new
  resolution paths must not coexist as alternative authorities.
- A first-party pack can preserve today's opinionated behavior while no longer
  making that behavior universal platform policy.
- Extensibility is deliberately narrower than arbitrary plugin execution so
  that humans and agents can still understand the effective system.

## Supersedes and extends

This decision extends ADR 0007's single resolved-contract boundary and ADR
0004's separation of policy from execution tooling. It preserves ADR 0009's
single-owner rule while assigning exact machine policy to structured sources
and judgment-based policy to documents.

It supersedes ADR 0010 where that decision makes one canonical workflow
mandatory for every participating repository, and ADR 0013 where skill curation
is defined only as the transitive closure of that mandatory workflow. It
preserves ADR 0013's canonical Agent Skills format and thin harness adapters,
and it retains ADR 0014's composable ecosystem profiles while making them
independent of workflow selection.
