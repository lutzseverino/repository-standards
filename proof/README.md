# Throwaway independent-author journey (#80)

This is an isolated experiment, outside the production implementation. It asks
whether unrelated publisher material can use one installed adoption mechanism.
It does not establish production packaging, a migration, or public discovery.
Atlas and Beacon were authored independently by two fresh agents given only the
provisional format and consumer behavior, without reading one another or the
CLI implementation. They are simulated outside authors, not recruited users.

Requirements and accepted decisions are captured in `evidence/spec-79.md` and
`evidence/ticket-80.md`. The latter requires real execution and focused observable
assertions, overriding the general prototype skill's HTML/no-tests defaults.

## Reproduce

Requires Python 3.12+, Git, and an authenticated `codex` executable for real agent
runs. Python/Git tooling uses the standard library; authors declare Python 3
and use its ordinary standard-library dependencies. Nothing installs missing
author dependencies. Choose a new disposable absolute output directory, `RUN`.
From this branch, run these commands with that path in place of `RUN`:

```text
python3 proof/run.py prepare RUN
python3 proof/run.py agent RUN --consumer atlas --stage initial
python3 proof/run.py agent RUN --consumer beacon --stage initial
python3 proof/run.py verify-initial RUN
python3 proof/run.py probes RUN
python3 proof/run.py update-setup RUN
python3 proof/run.py agent RUN --consumer atlas --stage update
python3 proof/run.py verify-update RUN
python3 proof/run.py recovery-setup RUN
python3 proof/run.py agent RUN --consumer recovery --stage recovery
python3 proof/run.py verify-recovery RUN
python3 proof/run.py offline RUN
```

Agent phases invoke fresh ephemeral Codex processes without user configuration,
passing only consumer location, the supplied bootstrap/installed CLI, and exact
selection. Prompts, actual JSONL command/edit events, stdout/stderr, final
responses, and whole-worktree inventories are saved. Agents are real model
calls and cost time/usage; contextual prose need not reproduce byte-for-byte.
The scenarios assert observable outcomes rather than prewriting their prose.

All publisher repositories, consumer repositories, CLI depots, installations,
and failure state live under RUN. `offline` explicitly commits verified consumer
inputs after the no-commit assertion, clones them, removes the publisher paths,
and acquires the pinned artifact into a new installation directory. It does not
copy the tool implementation into the consumer. `commands.jsonl` records actual
literal argv, working directories, exits, and outputs. Snapshot inventories
cover every worktree file (including hidden files), symlinks, executable bits,
Git HEAD and the Git index tree; Git administrative cache/reflog files are not
compared. Before/after consumer copies retain actual sample content.

## Provisional public format and contract

`standards.yaml` currently accepts the JSON subset of YAML. This deliberate
standard-library shortcut is not a production YAML parser proposal. The root
has `publisher`, `defaults`, and named `profiles`. Each defaults/profile map
keys a complete declaration by stable ID. Absence inherits; a full declaration
replaces all metadata; `{"exclude":true}` removes governance as a unit. Exactly
one profile is selected; unknown IDs, references, targets, and reserved skills
produce errors. Examples are ordinary small files in `fixtures/atlas` and
`fixtures/beacon`.

A declaration distinguishes `kind` (`file`, `skill`, or repository `concern`)
from `mode` (`exact` or `contextual`). Exact files reference a whole file; exact
skills reference a complete Agent Skills directory. Contextual files reference
guidance for current project-owned content. A concern has no invented output
target. Checks and fixes belong to declarations, so replacement/exclusion
removes their previous operations. Named concerns express relationships, but
arbitrary script effects cannot be inferred from their names.

Operations have `id`, literal `argv`, and executable `requires` entries. The
single substitution `{inputs}` resolves to retained publisher inputs. The CLI
runs argv directly, with consumer cwd and JSON stdin containing `selection`
(identity, effective declarations, resolution, material, prerequisites) and the
current `declaration` ID. Exit zero plus JSON `{status:"pass",message:"..."}`
is success; failures and malformed results retain stdout/stderr and partial
progress. Requirements are probed before application and again before their
operation. This prototype detects executable presence, not dependency versions
or arbitrary module imports. All fixtures need only declared Python + stdlib.

Ordering is: resolve/inspect; validate prerequisites and the complete installed
baseline; retain inputs; replace exact content and system skill; execute fixes
in sorted declaration order and declared array order; agent adapts current
project content; agent supplies factual assessment; rerun all checks; record
completion, leaving changes uncommitted. Resume skips recorded completed fixes
and reruns the failed fix. A script that partly changes files and fails must
therefore explain how to retry safely; there is no arbitrary-script rollback.

The CLI checks result shape and declared paths; scripts remain trusted tooling.
The assessment is a separately attributed agent claim, not a machine proof of
prose truth. The CLI can enforce presence of that assessment and passing checks,
but evaluating its factual usefulness requires reading the actual agent work.

Pins independently record CLI version/artifact SHA-256 and publisher source,
full immutable Git revision, and one profile. Setup is a small acquisition and
verification script; a local depot substitutes for production distribution.
A changed general installation is rejected against the project pin. Upgrading
the tool is a deliberate bootstrap operation and preserves standards selection.

Known edits to previously installed files or skill directories block all update
mutation. A changed selection that retires installed content blocks until an
explicit `--retain-retired` acknowledgement preserves its bytes and relinquishes
ownership. There is no implicit deletion on exclusion. Production retirement
choices, baseline storage, YAML syntax, runtime version constraints, package
transport/signatures, concurrent operation protection, crash-safe installation,
and richer assessment freshness checks remain unresolved.
