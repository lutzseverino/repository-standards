# Repository Standards

Canonical language for the conventions shared by participating repositories.

## Language

### Replacement product model

**Standards publisher**:
An independent author offering complete standards profiles from an attributable,
versioned source repository.
_Avoid_: Registry member, platform extension author

**Complete profile**:
One coherent selection of guidance, supplied content, ordinary-work skills,
checks, and fixes from a standards publisher, resolved against shared defaults.
_Avoid_: Policy pack, workflow/ecosystem matrix, adoption subset

**Shared defaults**:
The publisher's common declarations inherited by each complete profile unless
that profile replaces or excludes a declaration.
_Avoid_: Parent profile, profile chain

**Standards declaration**:
The complete unit of inheritance, replacement, and exclusion for a file, skill,
or named repository-level concern, including its associated governance.
_Avoid_: Merge fragment, partial override

**Exact supplied content**:
Publisher-owned material installed as a whole file or complete skill directory,
with a retained baseline for detecting local edits.
_Avoid_: Contextual template, prose merge

**Contextual guidance**:
Publisher requirements applied by an agent to current project-owned content,
with factual assessment distinct from scripted verification.
_Avoid_: Exact supplied content, generated proof of correctness

**Repository-level concern**:
A named standards declaration governing a relationship or requirement spanning
repository files without inventing a single output target.
_Avoid_: Fake managed file, lifecycle hook

**Exclusion**:
Removal of a declaration and all of its associated governance from the effective
selection, without permission to delete existing project-owned content.
_Avoid_: Managed absence, deletion instruction

**Retired installed content**:
Previously installed exact material no longer governed by a new selection and
requiring explicit ownership reconciliation during that update.
_Avoid_: Automatically deleted content, excluded project-owned file

**Resolved selection**:
The single effective set of inherited, replaced, and excluded declarations for
one complete profile at an exact publisher revision.
_Avoid_: Merged policy pack, capability-specific interpretation

**System skill**:
A tool-version-pinned shared operation, including profile adoption, whose name
and implementation are reserved against publisher replacement.
_Avoid_: Author adoption hook, ordinary-work skill

**Ordinary-work skill**:
A publisher-authored Agent Skill governing later repository work according to
the selected profile; its activities are not automatically adoption tasks.
_Avoid_: System skill, mandatory adoption checklist

**Profile bootstrap**:
A thin first-entry skill that obtains the pinned installed tool and delegates
to its shared adoption behavior before repository-local system skills exist.
_Avoid_: Publisher adoption procedure, copied CLI implementation

**Tool pin**:
The exact installed tool identity selected by a project, independent of its
standards revision and profile.
_Avoid_: General installation version, standards pin

**Standards pin**:
The immutable publisher revision and single complete profile selected by a
project, with retained inputs and provenance.
_Avoid_: Tool version, moving source branch

**Profile adoption**:
The deliberate application or update of one pinned complete profile through
exact installation, applicable scripted operations, and contextual agent work,
completed with verification and changes left uncommitted.
_Avoid_: File copying, automatic delivery, mandatory human checklist

**Participating repository**:
A repository whose maintainer deliberately adopts pinned standards.
Participation is not limited by repository ownership or maintainer identity.
_Avoid_: Repository maintained by Lutz Severino, internal repository

**Canonical workflow**:
The actor-neutral ordinary change process selected for a repository. Under the
replacement model, it belongs to its complete profile rather than a universal
platform workflow.
_Avoid_: Skill workflow, universal workflow

**Response language**:
English by default for agent responses, regardless of the language used to
address the agent. Another language is appropriate when the subject itself
requires it, such as quoted documents or translation content.
_Avoid_: Input language, English-only content

### Existing implementation workflow vocabulary

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

### Existing implementation lifecycle vocabulary

**Bootstrap skill**:
A thin user-scoped `create-repository` or `adopt-standards` entry skill that
selects an immutable standards release and delegates to its release-owned
lifecycle behavior.
_Avoid_: Profile bootstrap, installed-tool pin

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
The existing lifecycle's deliberate adoption or upgrade into its repository
environment and declared GitHub contract, ending in a validated adoption commit.
_Avoid_: Profile adoption, uncommitted adoption

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
