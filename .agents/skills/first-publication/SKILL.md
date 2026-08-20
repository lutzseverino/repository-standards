---
name: first-publication
description: Publish a prepared creation baseline for the first time.
disable-model-invocation: true
---

# First publication

Move one prepared creation baseline to a standards-complete repository.

1. Create a temporary directory outside the target repository and run the
   bundled adapter in Plan mode. Keep the reported Plan file available across
   the confirmation pause.

   ```sh
   PUBLICATION_PLAN_DIRECTORY="$(mktemp -d)"
   python3 .agents/skills/first-publication/scripts/publish plan \
     --plan-file "$PUBLICATION_PLAN_DIRECTORY/plan.json" \
     /ABSOLUTE/PATH/TO/REPOSITORY
   ```

2. Surface the complete Plan, including its initial commit contents and
   metadata, ordered publication and live operations, and exact confirmation
   phrase. Stop and ask the human for explicit confirmation of that current
   Plan. Invoking this skill, supplying a repository or Plan reference, or
   asking to continue is not confirmation. Do not enter Publish unless the
   human provides the exact phrase printed by Plan.
3. After that explicit confirmation, run Publish with the retained Plan and
   the exact phrase:

   ```sh
   python3 .agents/skills/first-publication/scripts/publish publish \
     --plan-file /ABSOLUTE/PATH/TO/plan.json \
     --confirm 'EXACT PHRASE FROM PLAN'
   ```

4. Surface the runner's verification or exact completed, failed, and remaining
   work. Do not roll back successful work. Success means committed content and
   re-observed GitHub state satisfy the selected release, `main` is published
   and established as default, and no pull request exists. Route every later
   change through ordinary implementation and GitHub delivery.

The skill is an execution adapter. Repository policy defines first
publication and its Plan/confirmation/Publish boundary.
