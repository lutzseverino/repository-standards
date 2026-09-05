# Compose product-neutral ecosystem profiles

## Status

Superseded for replacement product planning by
[ADR 0017](0017-independent-profiles-and-shared-adoption.md#relationship-to-earlier-decisions):
one complete profile replaces composition of every matching ecosystem profile;
contextual requirements can govern project-owned content, and profiles need not
supply automation. Advisory-only guidance, rejection of guidance-only profiles,
and blanket exclusion of product conventions do not constrain the replacement.
The decision below still describes the existing implementation until a deliberate
production cutover.

Originally accepted in [issue #48](https://github.com/lutzseverino/repository-standards/issues/48).

## Context

The former initial-selection rule treated several matching ecosystem profiles
as ambiguity, even though one repository can legitimately combine package,
framework, and desktop profiles. Profile guidance also used requirement language
for product-owned choices that Repository Standards did not mechanically
assess.

## Decision

Treat selectable ecosystem profiles as composable parts of the repository
environment. Each selectable profile declares applicability and owns observable
managed or assessed behavior. Initial selection retains `common` and
`documentation` and adds zero, one, or every matching profile; applicability
facts may carry several values for repositories that span ecosystems.

Profile guidance remains advisory. Package-manager and lockfile policy,
product scripts, framework layouts, build design, and product content remain
repository-owned. A profile with applicability but no environment behavior is
invalid rather than selectable, and mandatory environment interfaces cannot be
waived while claiming standards completeness.

## Consequences

- Unsupported ecosystems remain adoptable without fabricated profiles.
- A Tauri repository can compose Rust, package-manager, and UI profiles.
- Repository ownership conflicts invalidate the contract before mutation.
- Guidance can evolve without silently changing conformance.

## Alternatives considered

- Require one ecosystem profile. Rejected because repositories commonly span
  ecosystems and profiles.
- Enforce package locks, scripts, and framework layouts to strengthen profiles.
  Rejected because those are product implementation choices.
- Keep advice-only profiles selectable. Rejected because selection would have
  no observable repository-environment effect.
