# Managed files and ownership

The synchronization tool supports three file modes:

- `exact`: copy the source bytes exactly;
- `template`: replace `{{ variable_name }}` placeholders from manifest
  variables;
- `compose`: concatenate ordered fragments targeting the same file, followed
  by optional repository-local fragments.

A selected profile declares its managed targets in `profile.json`. Duplicate
exact or template targets are rejected. Multiple compose fragments may share a
target and are ordered first by `order`, then by profile selection order.

`repository-owned` patterns are hard guards. A plan fails before reading or
writing targets if a managed target matches one. Use forward-slash paths and
shell-style patterns such as `docs/**`.

Typical repository-owned content includes:

- `README.md`, `LICENSE`, and product documentation;
- source, tests, schemas, and migrations;
- `package.json`, lockfiles, POMs, and other build manifests;
- runtime, deployment, and release configuration;
- specialized CI workflows.

The common `.gitignore` is intentionally composed. A repository may keep
earned local patterns in `.repository-standards/gitignore.local`; the target is
then regenerated from standard fragments plus that repository-owned source.

Synchronization never deletes files and never touches a path absent from the
resolved managed plan.
