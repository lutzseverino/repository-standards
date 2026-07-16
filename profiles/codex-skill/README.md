# Codex skill profile

Keep operational knowledge in the skill's own `references` model; do not create
an empty parallel Diataxis tree. Extract validation from README prose into a
checked-in script and run it in a workflow named `CI`.

The validation gate should check at least the skill package structure, metadata,
internal links, and any resident-agnostic safety constraints. It must not expose
credentials or assume access to the maintainer's live infrastructure.

Private repositories use truthful access, type, and license-status information
in their root README instead of badges for public behavior they do not have.
