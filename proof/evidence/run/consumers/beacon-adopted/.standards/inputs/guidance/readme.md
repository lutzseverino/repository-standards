# Beacon: operator-facing README contract

Write the consumer README after inspecting its source and running
`python3 app.py --help`. Document the command that actually exists. This is a
small offline Markdown link inventory: one Markdown input file produces a JSON
array of `text` and `url` objects. It performs no HTTP requests.

Organize the README as a concise operational reference, in this order:

1. A project title followed by a one-sentence purpose.
2. `## Command reference`: a table with invocation, input, output, and exit
   behavior. Derive exit behavior from a real successful and a missing-file run.
3. `## Worked inventory`: show a tiny Markdown input containing a local link
   and an HTTPS link, the actual command, and its observed JSON output.
4. `## Boundaries`: explain offline operation and the regex parser's actual
   limitations, including nested Markdown. Distinguish URL extraction from
   checking whether a target exists or a remote service responds.
5. `## Operator notes`: show how to save output to a file and interpret an
   empty array. If docs/link-policy.json exists, link to it as the executable
   example contract; describe only the fields actually present.

Keep it useful for someone running an existing tool. Use tables and concrete
inputs and outputs; avoid a project origin story. All commands and behavior
claims must come from the consumer, not from a publisher example. The output
is the consumer's own prose, not a copied template.
