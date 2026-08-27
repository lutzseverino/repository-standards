# Documentation

Documentation for the Repository Standards source, lifecycle tooling, and
public repository environment.

## Standards

- [README conventions](../standards/README-conventions.md): presentation and
  navigation rules for repository, collection, project, and documentation
  boundaries.
- [Documentation conventions](../standards/documentation-conventions.md):
  documentation placement, ownership, and Diataxis organization.
- [Managed files](../standards/managed-files.md): managed-content modes and
  repository ownership guards.
- [Repository lifecycle](../standards/repository-lifecycle.md): repository
  conformance, creation, publication, adoption, and GitHub delivery policy.
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
  GitHub delivery; superseded in part by ADR 0002, ADR 0003, and ADR 0005.
- [Own the workflow and distribute pinned agent skills](adr/0002-own-workflow-and-distribute-agent-skills.md):
  distinguish repository policy from upstream skill contracts and make the
  official skill bundle available in every participating repository;
  superseded in part by ADR 0004, ADR 0010, and ADR 0013.
- [Distribute dependency-free repository lifecycle skills](adr/0003-distribute-dependency-free-repository-lifecycle-skills.md):
  ship family-owned adoption and repository-creation operations without
  coupling them to a planning or implementation workflow; superseded in part
  by ADR 0005 and ADR 0006.
- [Separate workflow policy from execution tooling](adr/0004-separate-workflow-policy-from-execution-tooling.md):
  define the canonical workflow as actor-neutral repository policy independent
  of the tools that execute it.
- [Add family-owned GitHub delivery](adr/0005-add-family-owned-github-delivery.md):
  require exact lifecycle-proposal confirmation while keeping ordinary
  delivery separate from implementation.
- [Assign repository lifecycle transitions explicitly](adr/0006-assign-repository-lifecycle-transitions.md):
  separate prepared creation, first publication, and ordinary delivery, and
  make adoption own future manifest-protocol transitions.
- [Resolve one repository contract and GitHub reconciliation](adr/0007-resolve-one-repository-contract-and-live-delta.md):
  normalize repository-contract knowledge once for assessment, correction,
  and lifecycle evidence.
- [Replace the repository standards interface without deprecation](adr/0008-replace-conformance-commands-without-deprecation.md):
  make the repository-level task grammar an intentional incompatible cutover;
  superseded in part by ADR 0011.
- [Assign one living owner to each policy](adr/0009-assign-one-living-owner-to-each-policy.md):
  separate ordinary workflow, repository lifecycle, maintenance, orientation,
  and adapter mechanics by living owner.
- [Define the public repository environment](adr/0010-define-the-public-repository-environment.md):
  make the standards adoptable by unrelated maintainers while leaving product
  implementation and repository-owned tooling under repository ownership.
- [Advertise only operational lifecycle interfaces](adr/0011-advertise-only-operational-lifecycle-interfaces.md):
  remove the delivery command stub, present agent-owned delivery through its
  Agent Skill, and separate concise human output from complete evidence.
- [Declare structured canonical validation](adr/0012-declare-structured-canonical-validation.md):
  persist one executable and literal argument sequence, execute it without a
  shell, and keep repository readiness distinct from standards conformance.
- [Curate skills and adapt harness discovery](adr/0013-curate-skills-and-adapt-harness-discovery.md):
  distribute only the canonical workflow's transitive skill closure, retire
  former managed skills explicitly, and expose canonical artifacts to Claude
  through drift-checked pointers.

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
