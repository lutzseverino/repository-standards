# README conventions

## Root README

The repository root is the public front door. Center only its compact identity
header:

```html
<div align="center">
  <h1>Product Name</h1>
  <p>One-sentence identity.</p>

  [![CI](...)](...)
  [![Releases](...)](...)
  [![License: SPDX-ID](...)](LICENSE)
</div>
```

Use two-space indentation and Markdown badge links. Do not repeat
`align="center"` on child elements.

Badge order is CI, releases when applicable, useful runtime or platform facts,
then license. Static metadata badges use the neutral Shields color `2f3437`.
Every badge must be truthful and link to its evidence. A private repository may
use access, type, or license-status badges in place of public CI/release badges.

After the header, write repository-specific content. Prefer this shared tail:

1. Development
2. Documentation
3. Support, when useful
4. License

The license section is last. Do not force empty or irrelevant sections merely
to match the outline.

## Internal READMEs

Internal READMEs use plain, left-aligned Markdown with no badges. The H1 names
the boundary described at that level:

- `services/README.md` uses `# Services` because it is a directory index.
- `services/polity/README.md` uses `# Polity Service` because it describes a
  leaf service.

Internal pages should link upward or to the root documentation index where that
helps navigation, but should not reproduce the root repository identity shell.

## Content rules

- Lead with what the repository or boundary is and who it is for.
- Keep setup commands executable and use the repository's declared package or
  build manager.
- Prefer links to detailed documentation over duplicating operational guides.
- Do not advertise a release, deployment, or quality gate that does not exist.
- Keep generated output, version numbers, and screenshots current or omit them.
