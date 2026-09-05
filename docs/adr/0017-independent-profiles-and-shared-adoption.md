# Adopt independent complete profiles through shared system skills

## Status

Accepted as the replacement direction in
[specification #79](https://github.com/lutzseverino/repository-standards/issues/79).
Supersedes [ADR 0014](0014-compose-product-neutral-ecosystem-profiles.md) and
[ADR 0016](0016-separate-capability-platform-from-policy-packs.md) for replacement
product planning; the released implementation has not yet migrated.

## Context

The former model independently selected policy packs, workflows, and ecosystem
profiles. Independent authors need to offer one coherent choice containing their
conventions, content, skills, and executable tooling, while sharing an adoption
mechanism that preserves project-owned work.

## Decision

Authors publish complete profiles from their own repositories; one profile
inherits shared defaults through complete-declaration replacement or exclusion.
This keeps ordinary prose, exact files, skills, checks, and fixes together as
one coherent choice while the system owns shared adoption.

Authors can supply trusted ordinary scripts and ordinary-work Agent Skills.
They cannot replace reserved system skills or provide adoption lifecycle hooks.
Declaration and result validation do not sandbox scripts or prove their effects.
The system distinguishes exact supplied material from contextual guidance for
current project-owned content. Complete skill replacement includes supporting
resources, and exclusion removes associated governance without authorizing
project-owned file deletion.

Tool identity and standards revision/profile are pinned independently. Retained
publisher inputs and provenance support fresh checkouts after publisher loss;
the pinned CLI remains an installed dependency. Known edits to installed content
block the entire update before mutation. Partial failures preserve actual work
and progress for diagnosis and retry. Adoption success requires completed agent
work and applicable passing checks, records contextual assessment separately,
and leaves changes uncommitted for the selected ordinary workflow.

## Consequences

[Proof #80](../independent-standards-proof.md) tests these boundaries with two
independently authored fixtures and actual fresh agents. Its syntax, local
artifact distribution, and explicit retain-and-relinquish retirement operation
are provisional experiments. They do not finalize production packaging or
prove public publication/discovery. No accepted decision is silently reopened
by a prototype shortcut; unresolved decisions and evidence limits remain in the
proof report and parent specification before further production ticketing.

This reconciles accepted product direction and observed evidence. It does not
migrate the existing released lifecycle implementation. Earlier release-specific
lifecycle terms remain historical/current-release vocabulary until a deliberate
production cutover, and the historical resolver proof remains unchanged.

## Alternatives considered

- Retain independently selected packs, workflows, and ecosystem profiles.
  Rejected because the accepted direction makes one complete profile the
  coherent adoption choice, with only defaults and profile declarations.
- Let publishers implement adoption hooks or replace system skills. Rejected
  because shared adoption must coordinate author material consistently while
  keeping operation results, conflicts, and completion inspectable.
