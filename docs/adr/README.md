# Architectural decision records

Durable decisions for the Repository Standards source and public repository
environment.

- [Adopt one canonical skills workflow](0001-adopt-one-canonical-skills-workflow.md):
  historical decision that replaced the issue-first workflow and separated
  GitHub delivery; superseded in part by ADR 0002, ADR 0003, and ADR 0005.
- [Own the workflow and distribute pinned agent skills](0002-own-workflow-and-distribute-agent-skills.md):
  distinguish repository policy from upstream skill contracts and make the
  official skill bundle available in every participating repository;
  superseded in part by ADR 0004, ADR 0010, and ADR 0013.
- [Distribute dependency-free repository lifecycle skills](0003-distribute-dependency-free-repository-lifecycle-skills.md):
  ship family-owned adoption and repository-creation operations without
  coupling them to a planning or implementation workflow; superseded in part
  by ADR 0005 and ADR 0006.
- [Separate workflow policy from execution tooling](0004-separate-workflow-policy-from-execution-tooling.md):
  define the canonical workflow as actor-neutral repository policy independent
  of the tools that execute it.
- [Add family-owned GitHub delivery](0005-add-family-owned-github-delivery.md):
  require exact lifecycle-proposal confirmation while keeping ordinary
  delivery separate from implementation.
- [Assign repository lifecycle transitions explicitly](0006-assign-repository-lifecycle-transitions.md):
  separate prepared creation, first publication, and ordinary delivery, and
  make adoption own future manifest-protocol transitions.
- [Resolve one repository contract and GitHub reconciliation](0007-resolve-one-repository-contract-and-live-delta.md):
  normalize repository-contract knowledge once and derive GitHub findings,
  corrections, and lifecycle evidence from one reconciliation.
- [Replace the repository standards interface without deprecation](0008-replace-conformance-commands-without-deprecation.md):
  make the repository-level task grammar an intentional incompatible cutover;
  superseded in part by ADR 0011.
- [Assign one living owner to each policy](0009-assign-one-living-owner-to-each-policy.md):
  give ordinary workflow, repository lifecycle, maintenance, orientation, and
  adapter mechanics distinct living owners.
- [Define the public repository environment](0010-define-the-public-repository-environment.md):
  make the standards adoptable by unrelated maintainers while leaving product
  implementation and repository-owned tooling under repository ownership;
  superseded in part by ADR 0016.
- [Advertise only operational lifecycle interfaces](0011-advertise-only-operational-lifecycle-interfaces.md):
  remove the delivery command stub, present agent-owned delivery through its
  Agent Skill, and separate concise human output from complete evidence.
- [Declare structured canonical validation](0012-declare-structured-canonical-validation.md):
  persist one executable and literal argument sequence, execute it without a
  shell, and keep repository readiness distinct from standards conformance.
- [Curate skills and adapt harness discovery](0013-curate-skills-and-adapt-harness-discovery.md):
  distribute only the canonical workflow's transitive skill closure, retire
  former managed skills explicitly, and expose canonical artifacts to Claude
  through drift-checked pointers; superseded in part by ADR 0016.
- [Compose product-neutral ecosystem profiles](0014-compose-product-neutral-ecosystem-profiles.md):
  select every applicable ecosystem profile while keeping product
  implementation and guidance outside mechanical conformance.
- [Bootstrap through thin user-scoped skills](0015-bootstrap-through-thin-user-scoped-skills.md):
  install only the two public entry skills globally, select one immutable
  release, and delegate lifecycle behavior to its release-pinned environment.
- [Separate the capability platform from policy packs](0016-separate-capability-platform-from-policy-packs.md):
  provide shared safe repository operations independently of declarative,
  selectable, authorable, and forkable policy; superseded by ADR 0017.

- [Adopt independent complete profiles through shared system skills](0017-independent-profiles-and-shared-adoption.md):
  replace the former policy matrix with independently authored complete profiles,
  trusted author scripts, retained independent pins, and real contextual adoption.
