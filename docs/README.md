# Documentation

Documentation for the repository standards source, synchronization tooling,
and repository-family conventions.

## Standards

- [README conventions](../standards/README-conventions.md): presentation and
  navigation rules for repository, collection, project, and documentation
  boundaries.
- [Documentation conventions](../standards/documentation-conventions.md):
  documentation placement, ownership, and Diataxis organization.
- [Managed files](../standards/managed-files.md): synchronization modes and
  repository ownership guards.
- [Repository workflow](../standards/repository-workflow.md): incoming-request,
  planning, implementation, GitHub-delivery, and reconciliation conventions.
- [Versioning and releases](../standards/versioning-and-releases.md): release
  and changelog policy.
- [Maintenance and rollout](../standards/maintenance-and-rollout.md): standards
  publication and deliberate adoption.

## Templates

Use the [canonical documentation templates](_templates/README.md) when adding
standards documentation.

## Architectural decision records

- [Adopt one canonical skills workflow](adr/0001-adopt-one-canonical-skills-workflow.md):
  historical decision that replaced the issue-first workflow and separated
  GitHub delivery; superseded in part by ADR 0002.
- [Own the workflow and distribute pinned agent skills](adr/0002-own-workflow-and-distribute-agent-skills.md):
  distinguish repository policy from upstream skill contracts and distribute
  the pinned official skill bundle.

## Agent configuration

- [Issue tracker](agents/issue-tracker.md): GitHub operations and relationship
  conventions used by the planning skills.
- [Triage labels](agents/triage-labels.md): canonical category and state label
  mapping.
- [Domain docs](agents/domain.md): repository-owned domain-document layout and
  consumer rules.

## Domain language

- [Repository Standards context](../CONTEXT.md): canonical terms used by the
  workflow, tooling, and documentation.
