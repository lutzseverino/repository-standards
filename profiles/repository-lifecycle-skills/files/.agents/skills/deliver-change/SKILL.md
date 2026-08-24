---
name: deliver-change
description: Deliver one validated change through GitHub.
disable-model-invocation: true
---

# Deliver change

Carry one validated commit through review and into the default branch.

Read `standards/repository-lifecycle.md` from the selected release before
operating this transition.

1. Perform delivery preparation through this adapter. Resolve the candidate
   commit, isolate it reversibly, prove the isolated `HEAD` is that commit, and
   only then run canonical validation there as a hard gate. Never run canonical
   validation in the caller's worktree; its current head is not candidate
   evidence. Failure stops before push or
   pull-request mutation and returns unchanged work to implementation. Record
   the caller's branch, head, index, and worktree content, then restore that
   exact state before stopping or reporting, including on failure. Push the head
   and reuse or create a ready pull request with an unambiguous non-closing
   tracked-work link.
2. Present one exact lifecycle proposal containing the pull request, prepared
   head, validation evidence, linked work, checks and review evidence, proposed
   squash merge, cleanup, warnings, and observed starting state. End preparation
   with `Exact confirmation required: Confirm delivery of HEAD via PR`, replacing
   `HEAD` and `PR` with the prepared commit and pull-request URL, then stop. Only
   that exact reply authorizes the proposal; a pull-request reference does not.
3. After exact confirmation, re-observe the proposal's starting state and
   reject stale evidence. A changed head invalidates confirmation; validate the
   new head as a hard gate before presenting its fresh proposal. Before merging,
   collect all current blockers from checks, submitted reviews, inline-thread
   resolution, mergeability, and merge policy; query thread resolution
   separately when the ordinary pull-request view omits it. Pending or failed
   gates and actionable feedback return unchanged work with their evidence.
4. After verifying the merge, close delivered implementation tickets; close a
   parent specification only when every ticket is delivered. Safely clean up the
   branch and report exact completed, failed, uncertain, and remaining work
   without rollback claims. Relevant state change or partial execution requires
   a fresh lifecycle proposal and human confirmation.

Implementation and standards adoption remain separate and must already have
produced the validated commit. Delivery does not edit implementation work.
