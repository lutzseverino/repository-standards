# Repository lifecycle

This document is the living owner of repository conformance and lifecycle
policy. [Contributing](../CONTRIBUTING.md) separately owns the ordinary change
workflow. Skills are execution adapters and do not define either policy.

## Task grammar

One actor-neutral `standards` executable exposes six repository goals:

| Goal | Result |
| --- | --- |
| `check` | assess the participating repository without mutation |
| `repair` | apply safe corrections after complete preflight |
| `create` | produce a prepared creation baseline |
| `publish` | perform first publication |
| `adopt` | create a validated standards-adoption commit |
| `deliver` | carry a validated change through GitHub |

The participating repository is the default subject. It includes repository
content and declared GitHub state. Restricted `content` or `github` scope is
available only for CI, outage recovery, and diagnostics; restricted work never
proves whole-repository standards completeness.

## Repository assessment

A repository assessment is the complete conformance account. It owns:

- one conclusion;
- satisfied requirements and known differences;
- evidence gaps;
- safe automatic corrections and required maintainer work;
- deterministic preservation evidence;
- exact completed, failed, and remaining application work.

Whole-repository assessment has exactly three conclusions:

- `standards-complete` (exit status 0);
- `not-standards-complete` (exit status 1);
- `unverified` (exit status 2).

Missing authentication, insufficient permissions, ambiguous lifecycle state,
or incomplete observability retains useful known evidence but cannot produce a
standards-complete conclusion.

`standards check` is read-only. `standards repair` freshly observes and
calculates the complete assessment, renders every proposed automatic
correction before the first mutation, applies safe corrections, and assesses
the repository again. Default repair performs no mutation unless the complete
whole-repository preflight succeeds. Explicit restricted repair changes only
the requested scope and remains unverified.

Repository-owned content and undeclared GitHub resources are preserved. Every
deterministic blocker is collected before mutation. Application rejects stale
observations, remains safe to retry, re-observes final state, and reports
partial progress without rollback claims.

## Repository creation and first publication

Repository creation produces validated, uncommitted content on unborn `main`,
an empty GitHub repository configured as `origin`, and no claim of standards
completeness. It creates no commit, push, pull request, merge, product scaffold,
or build manifest.

Every created repository selects `common` and `documentation`. An ecosystem
profile is selectable only when it has explicit applicability and observable
managed or assessed behavior. Creation infers one profile only when exactly
one matches settled facts; ambiguity requires an explicit choice before
mutation.

First publication is a separate transition. It presents one exact lifecycle
proposal covering the initial commit, publication of `main`, default-branch
establishment, declared GitHub corrections, and final verification. The
proposal binds the action to its observed starting state and requires exact
human confirmation. Relevant state change or partial execution invalidates it.
Publication retains successful work, reports failures precisely, creates no
pull request, and succeeds only when final assessment proves a
standards-complete repository.

## Standards adoption

Standards adoption selects an exact or latest stable release, uses that
release's own task grammar, repairs the participating repository, runs its
canonical validation, and performs a final standards check. Success creates
the validated adoption commit required by GitHub delivery. Failed validation
or final assessment creates no commit that claims readiness.

Adoption does not authorize GitHub delivery. A repository becomes durably
standards-complete only after the adoption commit reaches the default branch
and complete evidence is observed.

## GitHub delivery

GitHub delivery starts from a validated commit and does not edit implementation
work. It validates the exact candidate, preserves unrelated local state,
pushes the branch, reuses or creates a ready pull request, and gathers current
CI and review evidence.

Delivery then presents one exact lifecycle proposal containing the pull
request, prepared head, linked work, evidence, proposed squash merge, tracker
reconciliation, cleanup, warnings, and observed starting state. A pull-request
reference is not authorization. After exact human confirmation, delivery
re-observes the starting state, rejects stale evidence, reverifies merge policy,
squash merges, reconciles tracked work, and safely cleans up the branch.

Failures report exact completed, failed, uncertain, and remaining work without
rollback. Changed state or partial execution requires a fresh proposal and
confirmation.

## Declared GitHub state

The repository contract declares required labels, settings, features, and an
optional named ruleset. Extra labels, rulesets, and other undeclared resources
are preserved. The standard settings are squash merge only, pull-request title
as squash title, pull-request body as squash message, automatic merged-branch
deletion, protected `main`, `CI / Required`, Issues enabled, and Wiki and
Projects disabled unless deliberately declared.

GitHub may hide ruleset bypass actors from callers without Administration
write permission. An assessment reports that missing evidence as unverified
instead of guessing conformance.
