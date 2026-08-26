# Define the public repository environment

## Status

Accepted in [issue #45](https://github.com/lutzseverino/repository-standards/issues/45)

## Context

Repository Standards was described as shared conventions for repositories
maintained by one author. That framing obscured the useful public contract:
unrelated maintainers can adopt a recognizable repository-level environment
without surrendering ownership of their product implementation. Existing
descriptions also mixed repository presentation and lifecycle policy with
ecosystem build choices, making the mandatory boundary difficult to identify.

## Decision

Define Repository Standards as an opinionated, harness-portable repository
environment for GitHub projects. The mandatory environment governs
recognizable repository structure, the canonical workflow, documentation and
agent guidance, lifecycle interfaces, managed community files, and declared
GitHub behavior.

Product implementation, application architecture, package policy, runtime and
deployment choices, and repository-owned tooling remain under repository
ownership. A participating repository may add supplementary workflows, but the
canonical workflow remains mandatory. Alternative workflow sets and community
templates are future directions rather than current selectable interfaces.

Treat a participating repository as any repository whose maintainer
deliberately adopts an exact standards release. Support Linux, macOS, and WSL
as the initial public platform contract. Native Windows remains unsupported
future work.

## Supersedes

This decision supersedes ADR 0002 where its repository-family framing limits
the public audience to the author's repositories. It does not change the
provenance distinction between repository policy and external skills.

## Consequences

- Public orientation can make an honest adoption promise to unrelated
  maintainers.
- Repository conformance can remain opinionated without regulating product
  architecture or every repository-owned tool.
- Required environment interfaces cannot be waived while retaining a
  standards-complete conclusion.
- Supplementary workflows can provide evidence for future workflow-set design
  without creating a speculative interface now.

## Alternatives considered

- Limit the standards to repositories maintained by one author. Rejected
  because it hides the public adoption contract and excludes unrelated
  maintainers without a technical reason.
- Govern product architecture and package policy as part of conformance.
  Rejected because product implementation remains repository-owned and would
  create brittle ecosystem-specific policy.
- Make the canonical workflow optional. Rejected because removing the shared
  change process would make the repository environment unrecognizable.
