---
name: trace-csv
description: Implement or debug CSV summarizer behavior by tracing a small input through its actual command-line output.
---

Start with a CSV that exposes the requested behavior. Inspect the consumer's
entry point and run its real command with that file; save the observed result.
For parsing or numeric conversion changes, use the relevant cases in
[references/input-cases.md](references/input-cases.md) to choose a boundary
example. Change the behavior and rerun the original example plus that boundary.
Report the input, command, and observed result so another person can reproduce
it. Follow the repository's CONTRIBUTING.md for review and delivery.
