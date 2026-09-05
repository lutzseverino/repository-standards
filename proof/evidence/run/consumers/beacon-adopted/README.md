# Handbook inventory

Editors use this offline helper to inventory Markdown links before archiving a handbook revision.

## Command reference

Run these commands from the repository root with Python 3; no third-party packages are required.

| Invocation | Input | Output | Exit behavior |
| --- | --- | --- | --- |
| `python3 app.py FILE` | One UTF-8 Markdown file | JSON array of `text` and `url` objects on stdout | Observed exit 0 for the worked fixture; a missing file exits 2 with usage and an error on stderr, leaving stdout empty. |
| `python3 app.py --help` | None | Usage and argument help on stdout | Observed exit 0. |

The missing-file case was checked with `python3 app.py tests/fixtures/absent.md`.

## Worked inventory

The shared [fixture](tests/fixtures/link-contract.md) contains this local link and HTTPS link:

```markdown
[Manual](../../README.md) and [Service status](https://status.example.invalid)
```

Run:

```sh
python3 app.py tests/fixtures/link-contract.md
```

Observed stdout:

```json
[{"text": "Manual", "url": "../../README.md"}, {"text": "Service status", "url": "https://status.example.invalid"}]
```

## Boundaries

URLs remain data: the tool performs no HTTP requests and does not check whether local targets exist or remote services respond. It preserves destinations as written, without resolving relative paths. Handbook source documents stay outside this repository.

The parser uses a small regular expression, not a full Markdown parser. A probe containing `[Topic](#heading)`, `[A [nested] label](guide.md)`, `[Balanced](guide(one).md)`, and a reference-style link with its definition returned only `[{"text": "Topic", "url": "#heading"}]`. Anchors are included; nested brackets, destination parentheses, and reference-style links are unsupported. Nested Markdown can be omitted or partially matched, so an inventory is not a complete account of every Markdown link.

## Operator notes

Save the worked inventory to a file using shell redirection:

```sh
python3 app.py tests/fixtures/link-contract.md > inventory.json
```

Check the exit status before using the saved file. An empty array (`[]`) means no supported inline links were matched; plain text with no links produced this result with exit 0. It does not establish that all targets are valid or that the document contains no unsupported link syntax.

The [executable example contract](docs/link-policy.json) records `scope` as `local-only`, `network` as `false`, `reference_case` as the fixture path, and `expected_links` as the expected extracted objects. These fields describe extraction and offline operation.

The [editorial team policy](CONTRIBUTING.md) governs changes to archived handbook inputs, which require editor approval.
