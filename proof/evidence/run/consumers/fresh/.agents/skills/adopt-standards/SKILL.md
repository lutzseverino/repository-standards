---
name: adopt-standards
description: Adopt or deliberately update one pinned standards profile using the installed CLI and contextual project evidence.
---

Use the project-pinned CLI path returned by `python3 .standards/setup.py`.
At first entry, use the bootstrap and selection supplied by the maintainer.
Invoke the CLI with `python3 <installed-path> <command>` from the consumer root.

1. `inspect` the requested `--source`, full `--revision`, and `--profile`, or omit those flags to inspect retained inputs. Read the effective declarations, guidance material, exact identity, operations, and prerequisites. Settle the complete selection before application.
2. `apply` with that same selection. If blocked, read the error and evidence before retrying. Known conflicts require explicit reconciliation. Retired installed content requires explicit `--retain-retired <target>` to keep its bytes and relinquish ownership. Exclusions preserve existing project-owned files.
3. Read current project code, CLI help, tests, and existing documentation. Apply every effective contextual declaration to current project-owned content. Use actual observed behavior and runnable examples. Ordinary-work skills govern later work; their activities are not automatically adoption steps.
4. Write a JSON object outside the project (or in `.standards/agent-claims.json`) keyed by every contextual declaration ID. Each value explains the evidence you inspected and how current content satisfies its guidance. This is your factual assessment, separate from machine checks. Run `finish --assessment <path>`; success requires all applicable checks and the assessment.

An error is incomplete work. Inspect `.standards/progress.json` and `.standards/events.jsonl`; diagnose the failed operation using retained scripts and actual files. Resume with `apply` without selection flags: completed fixes are skipped, failed fixes retry. Preserve partial work and report any remaining gap. Verify Git HEAD stayed unchanged, inspect the final diff, and leave all adoption changes uncommitted.
