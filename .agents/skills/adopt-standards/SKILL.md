---
name: adopt-standards
description: Adopt an exact or latest stable repository standards release.
disable-model-invocation: true
---

# Adopt standards

Prepare and commit one standards adoption without delivering it.

Read `standards/repository-lifecycle.md` from the selected release before
operating this transition.

1. Read the manifest's `canonical-validation` declaration. It is the sole
   validation source for a repository that already declares it; do not pass an
   override. When migrating a preceding contract without the declaration,
   settle one executable, its ordered literal arguments, and an optional safe
   repository-relative working directory for the adapter to persist.
2. Run the bundled adapter, passing an exact release when supplied and
   otherwise selecting the latest stable release:

   ```sh
   python3 .agents/skills/adopt-standards/scripts/adopt [VERSION]

   # Migration only, when canonical-validation is absent:
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --validation-executable scripts/validate \
     [--validation-argument='LITERAL ARGUMENT' ...] \
     [--validation-working-directory RELATIVE/DIRECTORY] [VERSION]
   ```

3. Surface the selected release's assessment, repair preview, validation, final
   standards check, and recovery instructions. Success produces the validated
   adoption commit required by GitHub delivery. Failed validation produces no
   commit claiming readiness.
4. Report the commit and leave GitHub delivery as a separate transition.
