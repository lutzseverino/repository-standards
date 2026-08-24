---
name: publish-repository
description: Publish a prepared creation baseline for the first time.
disable-model-invocation: true
---

# Publish repository

Move one prepared creation baseline to a standards-complete repository.

Read `standards/repository-lifecycle.md` from the selected release before
operating this transition.

1. Run the bundled adapter from the prepared repository. It obtains the exact
   selected release and invokes that release's publication goal:

   ```sh
   python3 .agents/skills/publish-repository/scripts/publish \
     /ABSOLUTE/PATH/TO/REPOSITORY
   ```

2. Surface the complete lifecycle proposal, including the initial commit,
   publication, default branch, declared GitHub state, verification, and exact
   confirmation phrase. Stop and ask the human for that exact phrase. Invoking
   this skill, supplying a repository reference, or asking to continue is not
   confirmation.
3. Only after exact confirmation, invoke the same goal with the phrase:

   ```sh
   python3 .agents/skills/publish-repository/scripts/publish \
     /ABSOLUTE/PATH/TO/REPOSITORY \
     --confirm 'EXACT PHRASE FROM THE LIFECYCLE PROPOSAL'
   ```

4. Surface final verification or the exact completed, failed, uncertain, and
   remaining work. Do not roll back successful work. Any relevant state change
   or partial execution requires a fresh lifecycle proposal and confirmation.

Proposal persistence, serialization, identity, privacy, and storage location
are internal adapter details. Do not ask the user to supply or manage them.
