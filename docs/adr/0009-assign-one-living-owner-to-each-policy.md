# Assign one living owner to each policy

## Status

Accepted in [issue #35](https://github.com/lutzseverino/repository-standards/issues/35)
and implemented by
[issue #38](https://github.com/lutzseverino/repository-standards/issues/38).

## Context

Workflow, conformance, transition, release, and migration procedures had grown
across several living documents and skills. Repeating mutable policy for each
audience allowed copies to drift and left humans and agents with competing
instructions about the same operation.

## Decision

Assign each mutable policy one living owner:

- `CONTRIBUTING.md` owns ordinary change workflow policy.
- `standards/repository-lifecycle.md` owns repository conformance and transition
  policy, including GitHub delivery state.
- `standards/maintenance-and-rollout.md` owns release and migration policy.
- `README.md` provides orientation and a quick start.
- Skills contain adapter mechanics and refer to the owning policy document.

Other documents link to these owners instead of restating their normative
procedures.

## Consequences

- Each policy change has one authoritative edit location.
- Readers may need to follow a link from orientation or adapter documentation
  to the owning policy document.
- Owner documents must remain precise and discoverable for both humans and
  agents.

## Alternatives considered

- Repeat policy in audience-specific documents. Rejected because the copies
  would drift and could conflict.
- Put all lifecycle policy in one large document. Rejected because it would mix
  ordinary contribution, conformance, release, and migration audiences.
- Make skills the policy source. Rejected because policy would become hidden in
  actor-specific adapter instructions.
