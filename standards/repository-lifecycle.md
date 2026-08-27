# Repository lifecycle

This document is the living owner of repository conformance and lifecycle
policy. [Contributing](../CONTRIBUTING.md) separately owns the ordinary change
workflow. Skills are execution adapters and do not define either policy.

Repository Standards governs the repository environment: its recognizable
structure, documentation, agent guidance, lifecycle interfaces, and declared
GitHub behavior. Product implementation, application architecture, package
policy, and repository-owned tooling remain outside that mandatory boundary.
The environment is opinionated and harness-portable so unrelated maintainers
can deliberately adopt it without becoming part of an author-owned repository
family.

## Lifecycle interfaces

Lifecycle vocabulary names repository operations without promising that one
executable implements all of them. Deterministic operations use the
actor-neutral `standards` executable; operations that require agent judgment
use repository-local Agent Skills.

| Public interface | Result |
| --- | --- |
| `standards check` | assess the participating repository without mutation |
| `standards repair` | apply safe corrections after complete preflight |
| `standards create` | produce a prepared creation baseline |
| `standards publish` | perform first publication |
| `standards adopt` | create a validated standards-adoption commit |
| `$deliver-change` Agent Skill | carry a validated change through GitHub |

The participating repository is the default subject. It includes repository
content and declared GitHub state. Restricted `content` or `github` scope is
available only for CI, outage recovery, and diagnostics; restricted work never
proves whole-repository standards completeness.

## Canonical validation

The repository manifest declares canonical validation as one executable, an
ordered sequence of literal arguments, and an optional normalized
repository-relative working directory. The argument sequence may be empty;
individual arguments must be non-empty strings. The working directory defaults
to the repository root and must not escape it, including through a symbolic
link.

Lifecycle operations execute the declaration with preserved process argument
boundaries. They do not invoke a shell or perform quoting, variable or command
expansion, globbing, redirects, pipelines, or other implicit interpretation.
An unavailable executable and the exact nonzero process status are reported as
validation failures.

The declared command is the one aggregate interface that decides whether a
change is ready for GitHub delivery. Repository-owned subordinate commands and
CI-only evidence may coexist without becoming alternative canonical gates.
Canonical validation is not a standards check: validation concerns the
repository's own change readiness, while a standards check concerns conformance
with this repository environment.

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

Default human output shows the conclusion, scope, lifecycle, compact category
counts, differences, evidence gaps, automatic corrections, and required
maintainer work. `--verbose` restores complete satisfied-requirement and
preservation evidence. JSON is the stable complete automation contract;
verbosity does not remove JSON fields or change exit meanings.

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

Creation settles and persists the canonical-validation declaration in the
prepared baseline, then executes that declaration before its first remote
mutation.

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
release's own task grammar, repairs the participating repository, executes its
declared canonical validation, and performs a final standards check. A
preceding contract without the declaration must persist a structured migration
declaration before repair; an existing declaration cannot be overridden.
Success creates the validated adoption commit required by GitHub delivery.
Failed validation or final assessment creates no commit that claims readiness.

Adoption does not authorize GitHub delivery. A repository becomes durably
standards-complete only after the adoption commit reaches the default branch
and complete evidence is observed.

## GitHub delivery

GitHub delivery is invoked through the repository-local `$deliver-change`
Agent Skill. It starts from a validated commit and does not edit implementation
work. It validates the exact candidate by executing the isolated candidate's
declared canonical validation with literal process boundaries, preserves
unrelated local state, pushes the branch, reuses or creates a ready pull
request, and gathers current CI and review evidence.

Delivery then presents one exact lifecycle proposal containing the pull
request, prepared head, linked work, evidence, proposed squash merge, tracker
reconciliation, cleanup, warnings, and observed starting state. A pull-request
reference is not authorization. After exact human confirmation, delivery
re-observes the starting state, rejects stale evidence, reverifies merge policy,
squash merges, reconciles tracked work, and safely cleans up the branch.
Tracked-work reconciliation closes each delivered implementation ticket after
the merge is verified. A parent specification closes only when every
implementation ticket is delivered.

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

## Supported environments

The public lifecycle interfaces support Linux, macOS, and WSL. Native Windows
is unsupported future work; portable-looking commands do not imply current
native Windows support.
