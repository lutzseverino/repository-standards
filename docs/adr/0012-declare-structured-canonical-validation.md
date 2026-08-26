# Declare structured canonical validation

## Status

Accepted in [issue #46](https://github.com/lutzseverino/repository-standards/issues/46)

## Context

Participating repositories need one repository-owned aggregate command that
answers whether a change is ready for GitHub delivery. Repository creation and
standards adoption previously accepted that command as one shell string, while
delivery relied on documentation or agent interpretation. The command was not
part of the durable repository contract, and shell strings could reinterpret
spaces, metacharacters, globs, redirects, or expansions instead of preserving
the maintainer's intended argument boundaries.

Canonical validation is also easy to confuse with standards conformance. The
former evaluates repository-owned change readiness; the latter evaluates the
repository environment against its selected standards release.

## Decision

Require every current manifest to declare `canonical-validation` as one
non-empty executable and an ordered sequence of non-empty literal arguments.
Allow an optional normalized repository-relative working directory that
defaults to `.` and cannot escape the repository, including through a symbolic
link at execution time.

Normalize this declaration into the shared repository contract. Lifecycle
operations execute its process argument vector directly and never pass it
through a shell. They preserve exact arguments and report unavailable
executables, signals, and nonzero statuses accurately.

Repository creation settles and persists the declaration before validating the
prepared baseline. Standards adoption consumes an existing declaration without
allowing an override; migration from a preceding contract may supply structured
fields only to create the missing declaration. GitHub delivery resolves and
executes the isolated candidate's declaration.

The declaration remains the single aggregate delivery-readiness interface even
when repositories retain subordinate commands or CI-only evidence. Standards
assessment remains a separate operation and conclusion.

## Consequences

- Commands with spaces or metacharacters in their arguments execute literally
  and portably across supported environments.
- Participating repositories make their delivery-readiness interface
  machine-readable and release-pinned.
- Creation and preceding-contract migration must collect structured command
  facts instead of one shell command line.
- A missing executable, unsafe working directory, or nonzero process result is
  an explicit validation failure rather than an implicit shell outcome.
- Repository-owned build and test design remains outside the standards
  contract; only the aggregate invocation shape is standardized.

## Alternatives considered

- Keep a free-form shell command string. Rejected because argument boundaries
  and shell interpretation vary and are unsafe to infer.
- Prescribe `scripts/validate` for every repository. Rejected because product
  implementation and repository-owned tooling remain under repository
  ownership.
- Treat CI status or standards conformance as canonical validation. Rejected
  because CI-only evidence, repository readiness, and environment conformance
  answer different questions.
