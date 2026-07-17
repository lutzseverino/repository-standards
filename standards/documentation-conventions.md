# Documentation conventions

Documentation belongs to the boundary that owns its subject.

Every repository has a root `docs/` directory. Every independently built,
deployed, published, or versioned project in a monorepo has its own `docs/`
directory. Coupled implementation layers, generated trees, vendored code, and
Git submodules do not become separate documentation boundaries merely because
they contain a build manifest.

For example:

```text
docs/                         # repository-wide documentation
apps/web/docs/                # web application documentation
packages/design/docs/         # design package documentation
services/polity/docs/         # backend service documentation
```

Root documentation owns repository-wide development, architecture,
integration, release processes, and cross-project decisions. Project
documentation owns that project's behavior, contracts, architecture,
operation, and consumer guidance. Place a document at the narrowest boundary
that fully owns it and link across boundaries instead of duplicating it.

## Documentation roots

Every documentation root contains `README.md`. That index uses
`# Documentation`, names its owning boundary in the opening paragraph, and
links only content that exists.

The repository root also owns the single canonical `docs/_templates/` set.
Project documentation roots use those repository templates rather than
duplicating `_templates/`. The documentation profile manages the canonical set
exactly; indexes and authored documents remain repository-owned.

The repository or project README links its local documentation index from
`## Documentation`. Repository-wide documentation may link every declared
project index to make the monorepo navigable.

## Diataxis organization

Use a Diataxis-oriented tree as documentation earns each category:

```text
docs/
├── README.md
├── _templates/              # repository root only
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

The categories are a vocabulary, not a demand for empty directories. Create a
category and its index when the boundary has real content for it. Specialized
knowledge models may remain authoritative—for example, a Codex skill keeps its
runtime guidance in `skill/references`—while the repository still provides a
root documentation index for maintainers.

## Indexes

Directory indexes use a left-aligned title, a short purpose statement, and
concise entries in the form `Title: description`. Document lists describe
actual content and do not contain placeholder entries for future documents.

Indexes and document lists remain repository-owned because their contents are
specific to the boundary. The standards repository provides examples and
wording conventions, but synchronization does not overwrite them.

## Templates

Document templates prompt for audience, purpose, prerequisites, and validation
where relevant. Remove prompt text when publishing a document. Keep decision
records immutable after acceptance except for status and links to a superseding
decision.

## Writing

- Use sentence case for new authored headings.
- Prefer short paragraphs and executable examples.
- State versions only when behavior depends on them.
- Link to primary sources for external contracts.
- Separate current behavior from proposals and future work.
