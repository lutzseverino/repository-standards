# Tauri profile

This profile applies when `ecosystem=rust`, `framework=tauri`, and
`project-kind=desktop-application`. Its managed behavior is limited to
composing Rust and Tauri generated-path exclusions into `.gitignore`. Select it
alongside every applicable JavaScript package-manager and UI profile.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance: commit the chosen Rust lockfile, include Rust checks in the
repository-owned aggregate command, and preserve an earned operating-system
matrix. Lockfile policy, source layout, signing, updater metadata, packaging,
release permissions, and workflows remain repository-owned.
