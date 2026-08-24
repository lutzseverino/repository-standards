---
name: deliver-change
description: Deliver one validated change through GitHub.
disable-model-invocation: true
---

# Deliver change

Carry one validated commit through review and into the default branch.

1. Perform delivery preparation through this adapter. Validate the exact
   candidate, preserve and restore unrelated local state, push the head, and
   reuse or create a ready pull request with an unambiguous non-closing
   tracked-work link.
2. Present one exact lifecycle proposal containing the pull request, prepared
   head, validation evidence, linked work, checks and review evidence, proposed
   squash merge, cleanup, warnings, and observed starting state. Stop for
   explicit human confirmation of that exact proposal. A pull-request reference
   never authorizes delivery.
3. After exact confirmation, re-observe the proposal's starting state and
   reject stale evidence. Revalidate changed heads; verify checks, submitted
   reviews, unresolved threads, mergeability, and merge policy before merging.
4. Reconcile tracked work and safely clean up the branch. Report exact completed,
   failed, uncertain, and remaining work without rollback claims. Relevant state
   change or partial execution requires a fresh lifecycle proposal and human
   confirmation.

Implementation and standards adoption remain separate and must already have
produced the validated commit. Delivery does not edit implementation work.
