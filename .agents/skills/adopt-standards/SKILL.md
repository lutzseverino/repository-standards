---
name: adopt-standards
description: Adopt an exact or latest stable repository standards release.
disable-model-invocation: true
---

# Adopt standards

Prepare and commit one standards adoption without delivering it.

1. Read repository guidance and identify its single canonical validation
   command. Stop and ask the user when no single command is documented.
2. Run the bundled adapter, passing an exact
   release when supplied and otherwise selecting the latest stable release:

   ```sh
   python3 .agents/skills/adopt-standards/scripts/adopt \
     --validation-command '<canonical validation command>' [VERSION]
   ```

3. Surface the selected release's assessment, repair preview, validation, final
   standards check, and recovery instructions. Success produces the validated
   adoption commit required by GitHub delivery. Failed validation produces no
   commit claiming readiness.
4. Report the commit and leave GitHub delivery as a separate transition.
