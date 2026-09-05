# Adopt one canonical skills workflow

## Status

Superseded in part by ADR 0002, ADR 0003, and ADR 0005

Universal workflow, mandatory common/documentation/GitHub selection, and
inherited retirement deletion are superseded for replacement planning. See
[ADR 0017](0017-independent-profiles-and-shared-adoption.md#relationship-to-earlier-decisions)
for retained principles and existing-implementation scope.

## Context

The common profile couples baseline repository files to an issue-first change
process, issue-number branches, structured issue and pull-request forms, and a
custom pull-request policy check. The canonical Matt Pocock skills distinguish
incoming requests from self-authored work and define implementation only
through a validated commit. They do not define GitHub delivery. Odonta's
adoption of that workflow exposed a family-wide conflict with the existing
managed files.

## Decision

Use one canonical skills workflow for every participating repository. Incoming
requests enter without classification and pass through triage. Self-authored
work begins with planning and uses published specifications and implementation
tickets only when the work needs multiple sessions.

Keep GitHub delivery as a separate manual stage after implementation. Delivery
uses a pull request, CI, squash merge, and branch deletion, but does not require
an issue-number branch, a closing issue reference, or the custom pull-request
policy check. Branches use `<type>/<short-kebab-slug>`, and commits and
pull-request titles continue to use Conventional Commits.

GitHub delivery includes tracker reconciliation after the change reaches the
default branch. Close its implementation ticket then; close a parent
specification after all of its implementation tickets are delivered. A pull
request may use closing references, but they are not required.

Remove the managed issue forms and pull-request template. Permit blank incoming
issues so triage can classify them.

The common profile manages the invariant agent configuration: a generic
`AGENTS.md` skill block, the GitHub issue-tracker instructions, and the
canonical triage-label mapping. Each repository owns its domain configuration,
glossary or context map, and ADRs because their layout and content vary. The
profiles do not vendor Matt Pocock's skills; they document the workflow in
plain language and cite the upstream revision that defines it.

Require the canonical category and state labels and check their presence with a
read-only live audit. Label creation and changes remain deliberate manual
actions. Other labels remain permitted, and the audit does not enforce label
colors or descriptions. The common profile declares the required labels, and
the live audit derives them from the selected profiles.

Declare retired workflow files as managed absences. Audit fails when one is
present; synchronization previews its removal and write mode deletes only the
exact declared file.

Increase the manifest and synchronization compatibility version to `4` and
publish the incompatible family convention as standards release `3.0.0`. Add
`scripts/check` as this repository's canonical validation command and make CI
run that same gate.

Require version 4 manifests to select the common and documentation profiles and
to declare a GitHub contract. This makes the family-wide workflow and its live
label audit mandatory for every participating repository.

Use `docs/adr/` for architectural decision records because the domain-modeling
skills read and write that path. Retain the other Diataxis categories and the
managed documentation templates because participating repositories use them;
`docs/explanation/` remains the canonical explanation directory.

## Consequences

- The common profile will stop imposing the old issue-first policy.
- Participating repositories will need a deliberate migration for retired
  managed files and live labels.
- Synchronization gains a narrow, explicit file-removal capability.
- Documentation must keep implementation and GitHub delivery separate.
- Agent configuration is self-contained while the installed skills remain an
  external execution capability.
- Existing tutorials, how-to guides, reference documents, and explanations
  remain supported by the documentation profile.
- The change is an incompatible family convention and requires a major
  standards release.

## Alternatives considered

- Keep a selectable profile for the old workflow. This would preserve a second
  process when the family wants one canonical workflow.
- Keep the current issue-first policy. This conflicts with self-authored small
  work and with the skills' implementation boundary.
- Vendor the skills in every participating repository. This would duplicate
  externally maintained code and create another update obligation.
