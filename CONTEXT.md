# Repository Standards

Canonical language for the conventions shared by participating repositories.

## Language

**Canonical workflow**:
The actor-neutral change process defined by the workflow policy selected for a
repository. A workflow is canonical for repositories selecting it, not for
every repository compatible with the capability platform.
_Avoid_: Skill workflow, universal workflow

**Workflow policy**:
A versioned, independently selectable definition of a repository change
process. A policy pack may recommend one, but an ecosystem profile does not own
it and it does not own an ecosystem profile.
_Avoid_: Workflow profile, capability skill

**Response language**:
English by default for agent responses, regardless of the language used to
address the agent. Another language is appropriate when the subject itself
requires it, such as quoted documents or translation content.
_Avoid_: Input language, English-only content

**Capability skill bundle**:
A platform-release-pinned, explicitly inventoried set of shared capability
skills. Policy packs select and configure its capabilities but do not contain
or replace them.
_Avoid_: Standard skill bundle, pack-specific skill bundle, global skill
installation

**Bootstrap skill**:
A thin user-scoped Agent Skill that lets a maintainer create a participating
repository or adopt standards before repository-local standard skills exist.
It delegates substantive behavior to a selected immutable standards release;
the resulting repository remains release-pinned and self-contained.
_Avoid_: Globally installed standard skill bundle, custom skill installer,
standards source of truth

**Capability platform**:
The stable operational half of the product, providing reusable repository
capabilities and non-configurable boundaries independently of selected policy.
It owns the capability skill bundle and the deterministic operations behind it.
_Avoid_: Policy pack, repository setup, standards profile

**Capability skill**:
A reusable repository operation that applies the resolved repository contract
without owning its configurable policy. Its implementation is shared across
compatible policy packs.
_Avoid_: Policy skill, workflow policy

**Policy pack**:
A versioned, attributable, shareable collection of repository policy and
defaults that a maintainer can select, author, or fork. It contains no hidden
executable capability.
_Avoid_: Repository setup, repository configuration, ecosystem profile,
capability skill bundle

**Policy document**:
The authoritative prose source for policy that requires human or agent
judgment. Deterministic tooling identifies but does not interpret it.
_Avoid_: Repository configuration, generated policy summary

**Policy subject**:
The platform-defined identity of one judgment-based policy area. A selected
policy document owns its subject regardless of the document's package-relative
path, and two selected documents cannot own the same subject.
_Avoid_: Policy document path, documentation category

**Repository configuration**:
The repository-owned selection of one policy pack, one workflow policy,
ecosystem profiles, and explicit local choices. It owns repository-local
machine-readable facts, not prose policy.
_Avoid_: Policy pack, resolved repository contract, agent configuration

**Repository setup**:
The operation that selects, authors, or forks policy packs and produces or
updates repository configuration.
_Avoid_: Setup file, policy pack, repository configuration

**Resolved repository contract**:
The single validated effective result of selected policy and repository
configuration, including the applicable policy documents, consumed by every
repository capability.
_Avoid_: Merged setup, skill-specific configuration

**Incoming request**:
Work proposed outside the repository's own planning flow and awaiting
classification.
_Avoid_: Self-authored work

**Self-authored work**:
Work initiated through the repository's own planning flow rather than received
as an incoming request.
_Avoid_: Incoming request

**Specification readiness**:
The condition in which work is sufficiently specified for an agent to take and
implement autonomously. It does not imply that this standards repository
selects or starts the work.
_Avoid_: Dispatch, execution state

**Dispatch**:
The external act of selecting ready work and starting implementation, performed
manually today and potentially by a separate automation system in the future.
_Avoid_: Specification readiness, `ready-for-agent`

**Implementation**:
The work that turns an agreed change into a validated commit.
_Avoid_: GitHub delivery, shipping

**GitHub delivery**:
The work that carries a validated commit through repository review and into the
default branch.
_Avoid_: Implementation

**Delivery preparation**:
The part of GitHub delivery that prepares a validated change and its pull
request for human inspection, ending at an explicit confirmation boundary.
_Avoid_: Implementation, delivery finalization

**Delivery finalization**:
The part of GitHub delivery that, after explicit confirmation, verifies and
merges the prepared change, reconciles tracked work, and cleans up its branch.
_Avoid_: Delivery preparation, implementation

**Required label**:
A GitHub label whose exact name must exist for the canonical workflow. A
repository can also have labels that are not required labels.
_Avoid_: Exclusive label set

**Managed absence**:
A declared repository path that must not exist because its presence would
restore retired or conflicting behavior.
_Avoid_: Unmanaged path, optional file

**Repository environment**:
The recognizable repository-level structure, canonical workflow, documentation
and agent guidance, lifecycle interfaces, managed community files, and declared
GitHub behavior governed by a standards release. Product implementation and
repository-owned tooling may vary or diverge without changing that environment.
_Avoid_: Application skeleton, product architecture, project implementation

**Standards adoption**:
The deliberate work that initially brings a repository, or later updates a
participating repository, into conformance with a specific standards release,
including its repository environment and declared GitHub contract.
_Avoid_: File copying, standards update

**Participating repository**:
A repository whose maintainer deliberately adopts an exact standards release.
Participation is not limited by repository ownership or maintainer identity.
_Avoid_: Repository maintained by Lutz Severino, internal repository

**Prepared creation baseline**:
The uncommitted local repository content, including its settled
canonical-validation declaration, and empty GitHub repository produced by
repository creation. Repository-owned product content may be added before its
still-required first publication.
_Avoid_: Published repository, standards-complete repository

**First publication**:
The separate lifecycle transition from a prepared creation baseline to a
standards-complete repository.
_Avoid_: GitHub delivery, initial delivery, repository creation

**Standards-complete repository**:
A published repository whose committed repository environment and observed
GitHub state satisfy the repository contract of its selected standards release.
Required repository-environment interfaces cannot be waived while retaining
this conclusion.
_Avoid_: Lifecycle-relative conformance, prepared creation baseline

**Repository assessment**:
One complete account of how repository content and declared GitHub state
compare with the selected standards release, including known differences,
missing evidence, safe corrections, and required maintainer work.
_Avoid_: Separate content and GitHub conformance operations

**Consumer acceptance journey**:
A clean-room exercise of public installation and a complete repository
lifecycle path outside the standards source repository. It proves that a
maintainer can enter and use the system without source-checkout knowledge.
_Avoid_: Standards-repository dogfooding, unit test, showcase recording

**Selectable ecosystem profile**:
A profile with explicit applicability and observable managed or assessed
repository-environment behavior. It may also provide maintainer and agent
guidance, but it does not govern product implementation.
_Avoid_: Applicability label, ecosystem advice

**Declared GitHub reconciliation**:
The complete difference between a repository's declared GitHub contract and
its observed GitHub state, consumed by repository assessment and lifecycle
operations.
_Avoid_: Separate conformance result models, write-only correction lists

**Canonical validation**:
The repository-owned aggregate command declared by a participating repository.
It performs every self-contained check required before GitHub delivery, while
additional commands and CI-only evidence may coexist.
_Avoid_: Standards check, one prescribed script, every validation command,
CI-only gate

**Tracker reconciliation**:
The work that updates or closes tracked work after its change reaches the
default branch.
_Avoid_: Implementation, dispatch

**Agent configuration**:
Repository-local documentation that tells standard skills where tracked work
and domain documentation live and which triage labels to use.
_Avoid_: Vendored skill, agent implementation

**Harness adapter**:
A thin repository-environment artifact that exposes canonical agent
configuration or skills through a harness-specific discovery path without
becoming another policy source.
_Avoid_: Harness-specific workflow, duplicated agent policy
