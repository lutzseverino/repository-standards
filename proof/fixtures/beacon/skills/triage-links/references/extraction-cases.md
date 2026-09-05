# Extraction cases

| Case | Decision to establish from source and tests |
| --- | --- |
| `[Manual](guide.md)` | Baseline inline link: preserve label and destination. |
| `[Status](https://status.example.invalid)` | Extract the URL without fetching it. |
| `[Topic](#heading)` | Check whether anchors are included, rather than assuming. |
| `[A [nested] label](guide.md)` | Nested syntax requires an explicit support decision. |
| A reference-style link | Determine whether the tool intentionally supports only inline syntax. |

For regex-based implementations, nested labels and balanced destination
parentheses are likely syntax boundaries. Confirm the actual behavior with a
small input. Expanding the parser's supported syntax is a product decision;
a report can be complete by demonstrating a limitation accurately.
