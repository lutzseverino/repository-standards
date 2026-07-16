# Documentation conventions

Code repositories use a Diataxis-oriented documentation tree when they carry
more guidance than the root README can responsibly hold:

```text
docs/
├── README.md
├── _templates/
├── decisions/
├── explanation/
├── how-to/
├── reference/
└── tutorials/
```

- Tutorials teach by guiding a learner through a complete outcome.
- How-to guides solve a focused task for a reader who knows the context.
- Reference documents describe exact interfaces, configuration, and behavior.
- Explanation documents build understanding and discuss trade-offs.
- Decisions record durable architectural choices and their consequences.

The tree is a baseline, not a demand for empty directories. Add a category when
the repository has content for it. A repository with a purpose-built knowledge
model, such as a Codex skill using `skill/references`, may document that model
instead.

Repositories using this tree select the `documentation` profile. Its seven
files under `docs/_templates` are exact managed files; indexes, document lists,
and authored documents remain repository-owned.

## Indexes

`docs/README.md` explains the local documentation scope and links documents by
type. Directory indexes use a left-aligned title, a short purpose statement,
and concise entries in the form `Title: description`.

Indexes and document lists are repository-owned because they describe actual
content. The standards repository provides examples and wording conventions,
but the sync tool does not overwrite them.

## Templates

Document templates should prompt for audience, purpose, prerequisites, and
validation where relevant. Remove prompt text when publishing a document. Keep
decision records immutable after acceptance except for status and links to a
superseding decision.

## Writing

- Use sentence case for new authored headings; preserve the exact managed
  template wording during the v1 cohesion rollout.
- Prefer short paragraphs and executable examples.
- State versions only when behavior depends on them.
- Link to primary sources for external contracts.
- Separate current behavior from proposals and future work.
