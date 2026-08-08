# Triage labels

The canonical Matt Pocock triage vocabulary maps directly to GitHub labels.

## Categories

| Canonical role | GitHub label | Meaning |
| --- | --- | --- |
| `bug` | `bug` | Existing behavior is incorrect |
| `enhancement` | `enhancement` | New or improved behavior is requested |

## States

| Canonical role | GitHub label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer evaluation is required |
| `needs-info` | `needs-info` | More information is required from the reporter |
| `ready-for-agent` | `ready-for-agent` | The work needs no further triage |
| `ready-for-human` | `ready-for-human` | Human implementation is required |
| `wontfix` | `wontfix` | The work will not be actioned |

An incoming request has exactly one category and one state after triage.
Self-authored specifications and implementation tickets do not pass through
triage; planning skills apply `ready-for-agent` directly.

`ready-for-agent` expresses specification readiness. It does not dispatch work
or describe an execution state.

This mapping follows the upstream triage contract at
[`84fdeffd`](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/triage/SKILL.md).
