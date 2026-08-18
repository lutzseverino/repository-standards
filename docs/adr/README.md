# Architectural decision records

Durable decisions for the repository standards source and repository-family
conventions.

- [Adopt one canonical skills workflow](0001-adopt-one-canonical-skills-workflow.md):
  historical decision that replaced the issue-first workflow and separated
  GitHub delivery; superseded in part by ADR 0002, ADR 0003, and ADR 0005.
- [Own the workflow and distribute pinned agent skills](0002-own-workflow-and-distribute-agent-skills.md):
  distinguish repository policy from upstream skill contracts and make the
  official skill bundle available in every participating repository;
  superseded in part by ADR 0004.
- [Distribute dependency-free repository lifecycle skills](0003-distribute-dependency-free-repository-lifecycle-skills.md):
  ship family-owned adoption and repository-creation operations without
  coupling them to a planning or implementation workflow; superseded in part
  by ADR 0005 and ADR 0006.
- [Separate workflow policy from execution tooling](0004-separate-workflow-policy-from-execution-tooling.md):
  define the canonical workflow as actor-neutral repository policy independent
  of the tools that execute it.
- [Add family-owned GitHub delivery](0005-add-family-owned-github-delivery.md):
  accept Prepare and Finalize around explicit human confirmation while keeping
  ordinary delivery separate from implementation.
- [Assign repository lifecycle transitions explicitly](0006-assign-repository-lifecycle-transitions.md):
  separate prepared creation, first publication, and ordinary delivery, and
  make adoption own future manifest-protocol transitions.
- [Resolve one repository contract and live delta](0007-resolve-one-repository-contract-and-live-delta.md):
  normalize repository-contract knowledge once and derive live audit, writes,
  and lifecycle evidence from one desired-state delta.
