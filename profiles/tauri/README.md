# Tauri profile

Use this profile alongside the repository's JavaScript package-manager and UI
profiles. Commit `Cargo.lock` for the application. Run Rust formatting, linting,
and tests as part of the canonical check, and preserve the earned operating
system matrix for desktop integration and updater behavior.

Signing, updater metadata, platform packaging, and release permissions are
security-sensitive and repository-owned. Keep them in a specialized release
workflow rather than copying a generic template.
