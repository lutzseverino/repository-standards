# Advertise only operational lifecycle interfaces

## Status

Accepted in [issue #45](https://github.com/lutzseverino/repository-standards/issues/45)

## Context

ADR 0008 exposed six lifecycle goals through one executable. Five goals perform
their named operations, but `deliver` was a stub that returned instructions to
use an agent adapter. That surface made documentation look uniform at the cost
of truth: invoking an advertised command did not perform delivery. Routine
human assessments also enumerated every satisfied and preserved item before
the evidence that told a maintainer what to do.

## Decision

Advertise a lifecycle operation only through an interface that performs it.
Keep `check`, `repair`, `create`, `publish`, and `adopt` on the deterministic
`standards` executable. Present GitHub delivery through the repository-local
`$deliver-change` Agent Skill, where current review, CI, tracker, and repository
state can be interpreted without disguising agent judgment as a command.
Remove the delivery stub from the executable surface.

Make default human assessment output lead with the conclusion, compact counts,
differences, evidence gaps, automatic corrections, and required maintainer
work. Provide explicit verbose human output for complete satisfied and
preservation evidence. Keep JSON complete and stable, with unchanged exit
meanings.

## Supersedes

This decision supersedes ADR 0008 where it requires `deliver` to be one of six
goals on the `standards` executable. The actor-neutral lifecycle operation and
its confirmation policy remain unchanged.

## Consequences

- Every advertised command performs its named operation.
- Agent-owned transitions remain visible public capabilities without
  executable stubs.
- Routine successful assessments stay compact while diagnostics and automation
  retain complete evidence.
- Lifecycle policy may name commands and Agent Skills together without
  pretending they share one implementation form.

## Alternatives considered

- Keep the delivery stub to preserve a uniform six-goal command grammar.
  Rejected because redirection is not execution and makes the public surface
  misleading.
- Replace the delivery skill with an unproven deterministic command. Rejected
  because delivery currently requires agent judgment over review, CI, tracker,
  and repository state.
- Always enumerate complete assessment evidence. Rejected because routine
  output should prioritize the conclusion and actionable work; verbose and
  JSON modes retain full evidence.
