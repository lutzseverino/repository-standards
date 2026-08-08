# Repository Standards

Canonical language for the conventions shared by participating repositories.

## Language

**Canonical workflow**:
The single change process expected of every participating repository. It is a
family-wide standard, not a selectable alternative.
_Avoid_: Workflow option, workflow profile

**Incoming request**:
Work proposed outside the repository's own planning flow and awaiting
classification.
_Avoid_: Self-authored work

**Self-authored work**:
Work initiated through the repository's own planning flow rather than received
as an incoming request.
_Avoid_: Incoming request

**Specification readiness**:
The condition in which work needs no further triage before implementation can
be considered.
_Avoid_: Dispatch, execution state

**Dispatch**:
The decision to begin implementation of ready work.
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

**Canonical validation**:
The single complete command that determines whether a change is ready for
GitHub delivery.
_Avoid_: Test suite, partial check, stronger quality gate

**Tracker reconciliation**:
The manual work that updates or closes tracked work after its change reaches
the default branch.
_Avoid_: Implementation, dispatch

**Agent configuration**:
Repository-local documentation that tells installed skills where tracked work
and domain documentation live and which triage labels to use.
_Avoid_: Vendored skill, agent implementation
