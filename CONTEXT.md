# Repository Standards

Canonical language for the conventions shared by participating repositories.

## Language

**Canonical workflow**:
The actor-neutral, repository-owned change process expected of every
participating repository. Skills and other tools may execute its operations,
but they do not define the process.
_Avoid_: Skill workflow, workflow option, workflow profile

**Response language**:
English by default for agent responses, regardless of the language used to
address the agent. Another language is appropriate when the subject itself
requires it, such as quoted documents or translation content.
_Avoid_: Input language, English-only content

**Standard skill bundle**:
A release-pinned, explicitly inventoried set containing the transitive closure
of Agent Skills required by the canonical workflow. It is distributed to every
participating repository through the common profile. Agent Skills is the
canonical skill format; harness-specific discovery uses adapters rather than a
second skill format.
_Avoid_: Global skill installation, harness-native skill format, every upstream
skill

**Bootstrap skill**:
A thin user-scoped Agent Skill that lets a maintainer create a participating
repository or adopt standards before repository-local standard skills exist.
It delegates substantive behavior to a selected immutable standards release;
the resulting repository remains release-pinned and self-contained.
_Avoid_: Globally installed standard skill bundle, custom skill installer,
standards source of truth

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
