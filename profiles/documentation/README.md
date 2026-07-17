# Documentation profile

Select this profile in every participating repository. It owns exactly the
seven canonical files in the repository-level `docs/_templates` library.

It does not create empty content sections and does not own `docs/README.md`,
section indexes, decision records, or authored documentation. Those files must
describe the repository's real content.

Monorepos give each declared project its own `docs/README.md` and authored
documentation, but do not duplicate `_templates`. Project indexes link to the
canonical repository template library when contributors need a starting point.

Purpose-built knowledge models remain valid. For example, a Codex skill keeps
operational guidance in `skill/references` while repository-maintainer material
uses the root documentation boundary.
