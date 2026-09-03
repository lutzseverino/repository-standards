# Curate skills and adapt harness discovery

## Status

Superseded in part by
[ADR 0016](0016-separate-capability-platform-from-policy-packs.md). Accepted in
[issue #47](https://github.com/lutzseverino/repository-standards/issues/47).

## Context

ADR 0002 pinned and distributed the complete upstream skill bundle. That made
participating repositories self-contained, but it also installed capabilities
outside the mandatory canonical workflow and enlarged every repository's
review, context, and migration surface. Removing an upstream skill from the
source tree alone would not remove its previously managed files during
adoption.

Agent Skills and `AGENTS.md` are the canonical, harness-portable artifacts.
Claude Code discovers project skills and guidance through `.claude/skills/`
and `CLAUDE.md`, so it needs an additional discovery path without a second copy
of repository workflow or lifecycle policy. Optional harness invocation
metadata cannot be the only protection around mutation.

## Decision

Distribute the tested transitive closure of the mandatory canonical workflow.
Record its workflow roots and complete dependency graph with the selected skill
names, upstream source, immutable revision, upstream manifest, and license file
in the standard skill inventory. Contract tests require the inventory, bundled
directories, and dependency closure to agree exactly.

Remove skills outside that closure through file-level managed absences covering
their former managed artifacts. Repository content reconciliation continues to
preserve every skill that is neither in the standard inventory nor named by a
managed absence.

Keep `AGENTS.md` and `.agents/skills/` canonical. Provide the initial
Claude-compatible harness adapter with a `CLAUDE.md` import of `AGENTS.md` and
minimal `.claude/skills/` entrypoints. Each entrypoint mirrors only its
canonical skill's discovery frontmatter and points Claude to the canonical
instructions and relative resources. Contract tests reject missing adapters,
metadata divergence, extra adapter skills, and policy copied into an adapter.

Invocation metadata may improve harness behavior, but repository-level safety
remains in the canonical skill instructions and lifecycle interfaces:
proposals, explicit confirmations, validation, stale-state checks, and separate
lifecycle transitions continue to apply when a harness ignores optional
metadata.

## Supersedes

This decision supersedes ADR 0002 where it distributes the complete upstream
plugin bundle. It preserves that decision's provenance, immutable revision,
licensing, release pinning, and repository-local ownership boundaries.

## Consequences

- Creation and adoption install only workflow capabilities required by the
  selected standards release, together with the separately inventoried
  lifecycle skills.
- A skill added to the workflow dependency graph cannot ship accidentally; the
  closure and profile must change together.
- Retiring a managed skill requires enumerating its former files, so adoption
  removes known standard content without treating `.agents/skills/` as an
  exclusive directory.
- Claude users discover the same agent guidance and skill behavior through
  thin repository-local adapters, with no independent workflow policy to
  maintain.
- Further harness adapters require a real discovery mismatch and the same
  canonical-source and drift-rejection contract.

## Alternatives considered

- Continue distributing every upstream skill. Rejected because upstream
  availability does not make a capability part of the mandatory workflow.
- Copy canonical skills into `.claude/skills/`. Rejected because complete
  copies can drift into a second policy source.
- Use symlinked adapter trees. Rejected because managed content intentionally
  rejects symlink targets and the supported platforms do not share identical
  symlink setup behavior.
- Depend on user-scoped skills after bootstrap. Rejected because mutable global
  state would break release pinning and cross-repository independence.
