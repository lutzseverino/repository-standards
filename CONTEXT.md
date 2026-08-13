# Repository Standards

Canonical language for the conventions shared by participating repositories.

## Language

**Canonical workflow**:
The repository-owned change process expected of every participating
repository. It composes pinned external skill contracts with family-wide
policy; it is not an upstream workflow or a selectable alternative.
_Avoid_: Workflow option, workflow profile

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

**Canonical validation**:
The single complete command that determines whether a change is ready for
GitHub delivery.
_Avoid_: Test suite, partial check, stronger quality gate

**Tracker reconciliation**:
The manual work that updates or closes tracked work after its change reaches
the default branch.
_Avoid_: Implementation, dispatch

**Agent configuration**:
Repository-local documentation that tells standard skills where tracked work
and domain documentation live and which triage labels to use.
_Avoid_: Vendored skill, agent implementation
