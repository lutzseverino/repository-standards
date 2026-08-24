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
A pinned, explicitly inventoried set of repository-agnostic agent skills
distributed to every participating repository through the common profile.
_Avoid_: Global skill installation, every upstream skill

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

**Standards adoption**:
The deliberate work that brings a participating repository into full
conformance with a specific standards release, including repository content
and its declared live GitHub contract.
_Avoid_: File synchronization, standards update

**Prepared creation baseline**:
The uncommitted local repository content and empty GitHub repository produced
by repository creation. It still requires first publication.
_Avoid_: Published repository, standards-complete repository

**First publication**:
The separate lifecycle transition from a prepared creation baseline to a
standards-complete repository.
_Avoid_: GitHub delivery, initial delivery, repository creation

**Standards-complete repository**:
A published repository whose committed content and observed live GitHub state
satisfy every applicable rule of its selected standards release.
_Avoid_: Lifecycle-relative conformance, prepared creation baseline

**Repository assessment**:
One complete account of how repository content and declared GitHub state
compare with the selected standards release, including known differences,
missing evidence, safe corrections, and required maintainer work.
_Avoid_: Local audit, live audit, synchronization plan

**Selectable ecosystem profile**:
The prepared-creation lifecycle treats an ecosystem profile as selectable only
when it has explicit applicability and observable managed or audited behavior.
Unenforced ecosystem guidance is not selectable.
_Avoid_: Applicability label, ecosystem advice

**Live desired-state delta**:
The complete difference between a repository's applicable desired live
contract and its observed GitHub state, shared by audit, synchronization, and
lifecycle operations.
_Avoid_: Audit-only findings, write-only plan

**Canonical validation**:
The single complete command that determines whether a change is ready for
GitHub delivery.
_Avoid_: Test suite, partial check, stronger quality gate

**Tracker reconciliation**:
The work that updates or closes tracked work after its change reaches the
default branch.
_Avoid_: Implementation, dispatch

**Agent configuration**:
Repository-local documentation that tells standard skills where tracked work
and domain documentation live and which triage labels to use.
_Avoid_: Vendored skill, agent implementation
