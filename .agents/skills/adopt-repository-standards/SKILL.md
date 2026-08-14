---
name: adopt-repository-standards
description: Adopt an exact or latest stable repository standards release.
disable-model-invocation: true
---

# Adopt repository standards

Prepare the current repository for one stable standards release.

1. Read the repository guidance and identify its single canonical validation
   command. Stop and ask the user when no single command is documented.
2. From the repository root, run the bundled adoption runner, passing the
   user's version when one was supplied and omitting it to select the latest
   stable release:

   ```sh
   python3 .agents/skills/adopt-repository-standards/scripts/adopt \
     --validation-command '<canonical validation command>' [VERSION]
   ```

3. Surface every preview and recovery instruction from the runner. The
   adoption is complete only when canonical validation plus the release's
   offline and live audits pass.
4. Report the prepared release and leave the resulting working tree and all
   surrounding repository state to the user.
