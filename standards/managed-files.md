# Managed files and ownership

Repository-content correction supports five managed file modes:

- `exact`: copy the source bytes exactly;
- `template`: replace `{{ variable_name }}` placeholders from manifest
  variables;
- `compose`: concatenate ordered fragments targeting the same file, followed
  by optional repository-local fragments;
- `tree`: expand every regular file below one profile source directory into an
  `exact` managed target while preserving relative paths;
- `absent`: require an exact target path not to exist.

A selected profile declares its managed targets in `profile.json`. Duplicate
exact or template targets are rejected. Multiple compose fragments may share a
target and are ordered first by `order`, then by profile selection order.
Absent declarations have no source file and conflict with every other mode for
the same target.

A `tree` declaration uses `source` and `target` as directory roots and does not
accept `order`. Its source must contain at least one regular file and no
symlinks or special files. The expanded files are managed exactly, but the
target directory is not exclusive: unrelated repository-local files remain
untouched. When a later standards release retires a formerly expanded file, it
must declare that exact target `absent` to remove it deliberately.

`.github/dependabot.yml` is the one structured managed target. It is rendered
deterministically from `dependency-updates` because concatenated YAML fragments
cannot safely express one shared `version` and `updates` document. Profiles may
include guidance, but guidance is not mechanically assessed. The manifest
declares concrete install-unit directories, while package-lock choices, product
scripts, framework layouts, and comparable implementation conventions remain
repository-owned.

`repository-owned` patterns are hard guards. Content calculation fails before
reading or writing targets if a managed target matches one. Use forward-slash
paths and shell-style patterns such as `docs/**`.

Typical repository-owned content includes:

- `README.md`, `LICENSE`, and product documentation;
- source, tests, schemas, and migrations;
- `package.json`, lockfiles, POMs, and other build manifests;
- runtime, deployment, and release configuration;
- specialized CI workflows.

The common `.gitignore` is intentionally composed. A repository may keep
earned local patterns in `.repository-standards/gitignore.local`; the target is
then regenerated from standard fragments plus that repository-owned source.

`standards repair` writes only resolved managed targets. For an `absent`
target, the assessment shows a deletion and repair deletes only that exact
regular file. It does not delete directories, follow symlinks, remove parent
directories, or delete paths that are already absent from the resolved
content. Repository-owned guards apply before inspection or writing.
