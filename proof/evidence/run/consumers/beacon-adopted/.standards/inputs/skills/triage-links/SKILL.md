---
name: triage-links
description: Investigate missing or surprising entries from this repository's Markdown link inventory, and make a focused extraction fix when requested.
---

# Triage link inventory

Read `app.py` and run `python3 app.py --help` to establish the live input and
output contract. Reproduce the reported discrepancy with the smallest Markdown
file that still exhibits it; keep both its exact source and observed JSON.

Read [the extraction cases](references/extraction-cases.md) when deciding
whether the discrepancy is a parser bug or a supported-syntax boundary. Identify
the expected link objects before editing code. A URL being unreachable is a
separate observation from its absence in the extracted inventory.

When a fix is requested, add the reproducer to the consumer's existing tests,
change the parser narrowly, and run the documented validation command. Report
which input changed behavior and any remaining syntax limitation. When only
investigation was requested, return the reproducer, cause, and supported next
step. Use [the report outline](assets/finding.md) for a reusable investigation
record when the user requests a written artifact.
