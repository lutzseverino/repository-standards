# Distribute dependency-free repository lifecycle skills

## Status

Accepted

## Context

Participating repositories can audit and synchronize managed files, but a
complete standards adoption also requires selecting an exact stable release,
previewing live GitHub changes, validating the result, and retaining user
control of the surrounding workflow. ADR 0001 kept label creation and changes
manual, and ADR 0002 identifies only the pinned upstream standard skill bundle.
Neither decision provides a family-owned repository lifecycle operation.

## Decision

Distribute user-invoked `adopt-repository-standards` and `create-repository`
skills through the common profile as a repository-family-owned bundle with an
identity distinct from the pinned upstream skill bundle. Keep the skills lean
and dependency-free: they perform their repository lifecycle operation but do
not select, name, or invoke planning, documentation, implementation, commit,
push, or delivery workflows, so the user can compose them explicitly with any
workflow skill.

The adoption skill applies and validates an exact stable standards release,
including previewed live GitHub contract changes, and leaves file changes in
the working tree. The creation skill establishes a standards-complete local and
GitHub repository baseline, not product scaffolding, and likewise owns no
commit or push. This boundary preserves standalone usefulness without coupling
family policy to an external workflow implementation.

Expose separate live preview and write commands for required labels, declared
repository settings, and the named ruleset. Preserve extra labels and
undeclared live resources, make writes idempotent, and report partial progress
without rollback.

This decision supersedes ADR 0001 only where it requires label creation and
changes to remain manual. Triage and workflow policy remain unchanged.

## Consequences

- Participating repositories receive a self-contained adoption operation with
  family-owned inventory and license metadata.
- Adoption can be invoked alone or composed with a user-selected workflow.
- GitHub authentication needs Issues and Administration write permissions for
  live application.
- The release introducing the lifecycle bundle needs one documented manual
  bootstrap before participating repositories can invoke the skill.
- Repository creation remains dependent work and must reuse the adoption and
  live synchronization interfaces.

## Alternatives considered

- Keep adoption as a manual checklist. This leaves version selection, live
  application, and complete validation fragmented and easy to omit.
- Add adoption to the pinned upstream bundle. This misstates ownership and
  couples repository-family lifecycle policy to an external skill source.
- Make adoption choose a workflow. This prevents standalone use and removes
  the user's control over composition and delivery.
