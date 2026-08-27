# Own the workflow and distribute pinned agent skills

## Status

Superseded in part by ADR 0004, ADR 0010, and ADR 0013

## Context

Matt Pocock publishes composable skills rather than one complete change
workflow. The repository family had combined those skills with local routing,
branching, validation, and GitHub delivery policy while describing the result
as the canonical Matt Pocock workflow. The skills were also available only
through machine-global installation even though participating repositories are
intended to remain self-contained.

## Decision

Treat the process as the repository family's canonical repository workflow,
composed around the official `mattpocock-skills` bundle at
`84fdeffd12f2ee307994d1eb6feb48173b6e0502`. Attribute skill execution contracts
to upstream and identify routing, readiness, branching, validation, and GitHub
delivery as repository-family policy.

Distribute the official 25-skill plugin bundle as exact repository-local files
through an `agent-skills` profile inherited by the mandatory common profile.
Ship a managed inventory containing bundle source, revision, upstream manifest,
license, and selected skill names, and retain the upstream MIT license. The
common profile continues to supply the deterministic `AGENTS.md` and
`docs/agents/` configuration, so synchronized repositories do not rerun the
interactive setup skill.

Define `ready-for-agent` as specification readiness: an agent can implement the
work autonomously after it is selected. Selection and startup remain external
dispatch actions; this repository does not provide an automatic pickup system.

This decision supersedes ADR 0001 only where that record attributes a complete
workflow to upstream or decides not to vendor the skills.

ADR 0013 supersedes this decision where it distributes the complete 25-skill
plugin bundle. Provenance, immutable pinning, repository-local distribution,
and preservation of unrelated local skills remain in force.

## Consequences

- New and adopting repositories receive the same pinned execution capability
  without relying on machine-global installation.
- Skill additions and upgrades become deliberate, reviewable standards
  releases.
- Removing a previously managed skill or supporting file requires an explicit
  managed-absence migration; unrelated repository-local skills may coexist.
- Existing repositories remain pinned until they deliberately adopt the new
  standards release.
