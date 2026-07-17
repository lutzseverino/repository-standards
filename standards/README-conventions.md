# README conventions

A README describes the boundary represented by its directory. Repository,
collection, project, and documentation boundaries use related but distinct
presentations.

## Repository README

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
to match the outline. Every repository README links its repository
documentation from `## Documentation`.

## Nested READMEs

Nested READMEs use plain, left-aligned Markdown with no badges or HTML identity
header. Their first line is one Markdown H1 naming the current boundary. They
do not reproduce repository-wide badges, support, license, or setup material.

The manifest declares significant README boundaries:

- `collection` is an index of sibling boundaries, such as `# Applications`,
  `# Packages`, or `# Services`;
- `project` is an independently built, deployed, published, or versioned
  workspace boundary, such as `# Polity Web` or `# Polity Service`.

A collection README briefly defines the collection and links its direct
children. It includes shared development instructions only when they apply at
the collection boundary.

A project README leads with the project's identity and scope. It contains only
sections meaningful to that project and always includes `## Documentation`
linking `docs/README.md`. Development, validation, contracts, architecture, and
deployment remain optional project-owned sections.

Other nested READMEs may document source, asset, generated, or specification
directories without becoming declared project boundaries. They follow the same
left-aligned, badge-free presentation.

## Documentation indexes

Every repository and declared project owns `docs/README.md`. It begins with
`# Documentation`, identifies the boundary in its opening paragraph, and links
only documentation sections or documents that exist. The path already carries
the project identity, so headings such as `# Polity Service Documentation` are
not used.

See [Documentation conventions](documentation-conventions.md) for placement,
Diataxis organization, and cross-boundary ownership.

## Content rules

- Lead with what the repository or boundary is and who it is for.
- Keep setup commands executable and use the repository's declared package or
  build manager.
- Prefer links to detailed documentation over duplicating operational guides.
- Link across boundaries instead of copying the same guidance.
- Do not advertise a release, deployment, or quality gate that does not exist.
- Keep generated output, version numbers, and screenshots current or omit them.
