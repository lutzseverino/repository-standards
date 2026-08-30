---
name: adopt-standards
description: Adopt an exact or latest stable repository standards release.
disable-model-invocation: true
---

# Adopt standards

Prepare and commit one standards adoption without delivering it.

Read `standards/repository-lifecycle.md` from the selected release before
operating this transition.

1. Detect whether a repository standards manifest exists. Its absence means
   initial adoption; do not ask the maintainer to hand-author a manifest or
   other bootstrap artifact. Its presence means an upgrade.
2. For initial adoption, reuse settled repository evidence and collect only
   facts that remain genuinely unresolved. Infer the GitHub `owner/name` from a
   GitHub `origin` and the boundary title from the repository directory when
   unambiguous. Inspect repository files and supplied context before asking for
   applicability facts; establish enough positive or conflicting facts to
   prove whether every selectable ecosystem profile applies. Settle one
   canonical-validation executable, its ordered literal arguments, and an
   optional safe repository-relative working directory. Confirm any
   non-default repository-owned declarations or deliberate absence of the
   standard ruleset instead of guessing them.
3. For an upgrade, read the manifest's `canonical-validation` declaration. It
   is the sole validation source when already declared; do not pass an
   override. When migrating a preceding contract without the declaration,
   settle one executable, its ordered literal arguments, and an optional safe
   repository-relative working directory for the adapter to persist.
4. Run the bundled adapter, passing an exact release when supplied and
   otherwise selecting the latest stable release. For initial adoption, repeat
   `--fact NAME=VALUE` for settled applicability facts, including repeated
   names for multi-value facts. Pass `--profile NAME` only for deliberate
   explicit ecosystem-profile selection. Use `--github-repository OWNER/NAME`,
   `--title TITLE`, `--repository-owned PATTERN`, or `--no-ruleset` only when
   settled evidence requires an explicit value:

   ```sh
   # Initial adoption: first produce the complete proposal without mutation.
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --validation-executable scripts/validate \
     [--validation-argument='LITERAL ARGUMENT' ...] \
     [--validation-working-directory RELATIVE/DIRECTORY] \
     [--fact NAME=VALUE ...] [--profile NAME ...] \
     [--github-repository OWNER/NAME] [--title TITLE] \
     [--repository-owned PATTERN ...] [--no-ruleset] [VERSION]

   # After the maintainer reviews that exact complete proposal, pass its exact
   # confirmation while preserving every proposal argument.
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --validation-executable scripts/validate \
     [SAME INITIAL ARGUMENTS ...] \
     --confirm 'EXACT CONFIRMATION FROM CURRENT PROPOSAL' [VERSION]

   # Upgrade: first produce the complete proposal without mutation.
   python3 .agents/skills/adopt-standards/scripts/adopt [VERSION]

   # After reviewing that exact upgrade proposal, confirm it exactly.
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --confirm 'EXACT CONFIRMATION FROM CURRENT PROPOSAL' [VERSION]

   # Migration proposal, when canonical-validation is absent:
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --validation-executable scripts/validate \
     [--validation-argument='LITERAL ARGUMENT' ...] \
     [--validation-working-directory RELATIVE/DIRECTORY] [VERSION]
   ```

5. Stop after rendering an initial-adoption or upgrade proposal. Surface its
   selected exact release, complete proposed manifest declaration and normalized
   assessment, managed environment,
   declared GitHub state, ownership boundaries, canonical validation,
   conflicts, automatic corrections, required maintainer work, and exact
   confirmation. An upgrade also shows the current manifest declaration, and
   its assessment must cover the standard skill inventory, harness adapters,
   managed retirements, and lifecycle interfaces.
   Do not treat the original adoption request or a proposal identifier as
   confirmation. Resume mutation only after the maintainer deliberately
   supplies the exact confirmation from the current proposal. A stale
   confirmation requires a new proposal and review.
6. Surface the selected release's repair, validation, final standards check,
   retained partial state, and recovery instructions. Success produces the
   validated adoption commit required by GitHub delivery. Failed validation or
   final assessment produces no commit claiming readiness.
7. Report the validated adoption commit and state that GitHub delivery remains
   a separate lifecycle transition. Do not open, push, or merge a pull request.
