# Adopt independent complete profiles through shared system skills

## Status

Accepted as the replacement direction in
[specification #79](https://github.com/lutzseverino/repository-standards/issues/79).
Supersedes the earlier replacement model and the inherited requirements listed
in the [predecessor applicability map](#relationship-to-earlier-decisions).
The existing implementation has not yet migrated.

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

### Relationship to earlier decisions

This map defines how every predecessor applies to replacement planning under
#79. Superseding ADR 0016 does not revive requirements it had already displaced.
“Retain” identifies principles compatible with the accepted direction; it does
not import each predecessor's implementation, inventory, or migration scope.

The existing operational owners—`README.md`, `CONTRIBUTING.md`,
`standards/repository-lifecycle.md`, `standards/maintenance-and-rollout.md`, and
the bootstrap and repository-local skills—continue to govern the implemented
workflow, including Unreleased functionality. Their commit-producing standards
adoption, copied tooling, coupled release identity, and delivery gates do not
specify the replacement's uncommitted profile adoption or independent pins.
They change only through a deliberate production cutover. The glossary names
these operations separately as **Standards adoption** / **Profile adoption**
and **Bootstrap skill** / **Profile bootstrap**.

| Earlier decision | Applicability to the replacement |
| --- | --- |
| [ADR 0001](0001-adopt-one-canonical-skills-workflow.md) | Superseded: universal workflow, mandatory common/documentation/GitHub contract, and inherited retirement deletion. Existing source workflow: triage, branches, delivery, labels, documentation paths, and historical cutovers. |
| [ADR 0002](0002-own-workflow-and-distribute-agent-skills.md) | Superseded: mandatory official bundle/common inheritance and file-level managed-absence retirement. Retain provenance, immutable pins, complete local skills, unrelated-skill preservation, deliberate upgrades, and readiness distinct from dispatch. |
| [ADR 0003](0003-distribute-dependency-free-repository-lifecycle-skills.md) | Existing lifecycle only: named skill inventory, creation, built-in GitHub correction, and coupled stable release. Retain shared adoption separate from ordinary workflow and truthful partial progress. Author scripts may declare runtime prerequisites. |
| [ADR 0004](0004-separate-workflow-policy-from-execution-tooling.md) | Retain actor-neutral policy and separation of policy from execution. The existing fixed external/family skill bundles are not a required publisher inventory. |
| [ADR 0005](0005-add-family-owned-github-delivery.md) | Existing source delivery contract: preparation, exact confirmation, GitHub merge, and tracker reconciliation remain active here. They do not prescribe every publisher's ordinary workflow; #79 does not change review or delivery automatically. |
| [ADR 0006](0006-assign-repository-lifecycle-transitions.md) | Existing lifecycle only: creation, publication, committed-plus-GitHub completeness, and manifest transitions. These do not become profile-adoption success conditions or additional proof scope. Retain stale-state rejection and truthful partial progress. |
| [ADR 0007](0007-resolve-one-repository-contract-and-live-delta.md) | Retain one normalized selection, schema/runtime agreement, and separation of comparison from application. Fixed label/dependency/GitHub inventory and live completeness belong to the existing implementation, not the replacement profile contract. |
| [ADR 0008](0008-replace-conformance-commands-without-deprecation.md) | Existing/historical interface: six-goal grammar, retired aliases, v4 bootstrap, and migration. Preserve immutable history; replacement command grammar and cutover remain undecided. |
| [ADR 0009](0009-assign-one-living-owner-to-each-policy.md) | Retain one authoritative owner per policy. Specific living-owner paths and source skill adapters describe this repository, not a compulsory publisher layout or a ban on independently authored ordinary-work skills. |
| [ADR 0010](0010-define-the-public-repository-environment.md) | Superseded: universal opinionated environment/workflow and blanket restrictions preventing selected contextual requirements. Retain adoption by unrelated maintainers and project ownership. Existing Linux/macOS/WSL support is not new prototype portability evidence. |
| [ADR 0011](0011-advertise-only-operational-lifecycle-interfaces.md) | Retain operational advertised capabilities, the distinction between agent judgment and deterministic output, and complete evidence. Named commands, delivery entry point, and exit schema describe the existing interface, not settled replacement grammar. |
| [ADR 0012](0012-declare-structured-canonical-validation.md) | Retain literal argument vectors, safe working directories, accurate process failures, and readiness distinct from conformance. The mandatory aggregate manifest field and its creation/adoption/delivery integration remain the existing lifecycle contract; replacement profiles supply applicable authored checks. |
| [ADR 0013](0013-curate-skills-and-adapt-harness-discovery.md) | Superseded: universal workflow skill closure and mandatory file-level managed-absence retirement. Retain Agent Skills, provenance, preservation outside governed targets, and canonical discovery. Exact harness adapters and lifecycle confirmation inventory remain existing implementation details. |
| [ADR 0014](0014-compose-product-neutral-ecosystem-profiles.md) | Superseded: composing all matching ecosystem profiles, mandatory common/documentation selection, advisory-only guidance, rejection of guidance-only profiles, and blanket exclusion of product conventions from contextual requirements. Retain explicit ownership conflicts and project ownership; contextual assessment remains distinct from scripted verification. |
| [ADR 0015](0015-bootstrap-through-thin-user-scoped-skills.md) | Superseded as universal replacement requirements: exactly two bootstrap skills, one semantic release coupling tool/standards/skills, and GitHub tag/VERSION acquisition. Retain thin first entry, source-checkout independence, repository-local pinned system behavior, and global updates that cannot change project pins. |
| [ADR 0016](0016-separate-capability-platform-from-policy-packs.md) | Superseded: pack/workflow/ecosystem matrix, platform-only executables, repository-local policy choices, and first-party compatibility-first migration. Retain deterministic resolution, provenance, ownership/conflict protection, literal invocation, and truthful progress where adopted by #79. Exact schemas and layout remain findings. |

## Consequences

[Proof #80](../independent-standards-proof.md) tests these boundaries with two
independently authored fixtures and actual fresh agents. Its syntax, local
artifact distribution, and explicit retain-and-relinquish retirement operation
are provisional experiments. They do not finalize production packaging or
prove public publication/discovery. No accepted decision is silently reopened
by a prototype shortcut; unresolved decisions and evidence limits remain in the
proof report and parent specification before further production ticketing.

This reconciles accepted product direction and observed evidence. It does not
migrate the existing lifecycle implementation. Earlier lifecycle
terms remain existing-implementation vocabulary until a deliberate
production cutover, and the historical resolver proof remains unchanged.

## Alternatives considered

- Retain independently selected packs, workflows, and ecosystem profiles.
  Rejected because the accepted direction makes one complete profile the
  coherent adoption choice, with only defaults and profile declarations.
- Let publishers implement adoption hooks or replace system skills. Rejected
  because shared adoption must coordinate author material consistently while
  keeping operation results, conflicts, and completion inspectable.
