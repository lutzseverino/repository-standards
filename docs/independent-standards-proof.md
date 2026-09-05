# Independent standards authorship and adoption proof

[Issue #80](https://github.com/lutzseverino/repository-standards/issues/80) tests
[specification #79](https://github.com/lutzseverino/repository-standards/issues/79)
with an isolated installed CLI, independent publisher fixtures, disposable Git
consumers, and actual fresh agents. The throwaway implementation and fixtures
remain on `test/independent-standards-proof-80`; this documentation change carries
only findings and accepted product-direction reconciliation.

## Verdict and scope

The exercised model works across two independently authored sample publishers:
one shared system skill coordinates deterministic installation and trusted
scripts with useful contextual agent work. This supports the accepted complete
profile/shared-adoption direction. It does not establish production readiness,
public distribution/discovery, or usability by recruited human authors.

Atlas and Beacon were authored in separate fresh agent contexts given the same
provisional declaration format and distinct consumer behavior. Neither author
inspected the other fixture or the tool implementation. Atlas supplies task-first
CSV guidance and a data-investigation skill; Beacon supplies an operational
reference format and a link-triage skill. These are controlled simulated outside
authors, with no author-specific branches in the adoption implementation.

The public-format proposal, execution contract, reproducible phased runner, and
full evidence are retained at [the immutable proof source](https://github.com/lutzseverino/repository-standards/tree/3f0f48b95aba0aac67015f71db7e14f32ae4b7b7/proof).
The README there specifies local prerequisites and actual model-call steps.
The prototype currently accepts JSON-compatible YAML in `standards.yaml`, uses
Python standard-library scripts, and obtains immutable zipapps from a local
depot. Those are bounded experiment choices, not finalized production schemas
or packaging decisions. Actual artifact hashes, publisher Git revisions, profile
choices, invocation arguments, and source/consumer Git records are in its proof
package.

## Acceptance-to-evidence map

All paths below are relative to `proof/evidence/run/` in that immutable source.
Raw agent JSONL records include real commands, edits, outputs, and completion
messages. The sample READMEs were written by those agents, not the scenario
runner. Script results and agent assessments have distinct owners and files.

| Acceptance criterion | Inspectable evidence and result |
| --- | --- |
| Independent authors through one system | `fixtures/atlas` and `fixtures/beacon` under `proof/`, their `AUTHOR.md` files, four full/selected inspection records, and both initial agent transcripts. Each has defaults and contrasting complete profiles; the same CLI/skill handles both. `reserved-skill.json` rejects replacement of `adopt-standards`. Human author ergonomics remain untested. |
| Resolution and author feedback | `assertions-prepare.json`, both selected/full inspections, `missing-reference.json`, and `declaration-conflict.json`. Complete replacements remove prior checks/guidance, exclusion removes contribution governance, and a named concern relates two files. The update replaces the entire skill directory. |
| Read-only inspection | Matching `snapshots/*-before-inspect.json` and `*-after-inspect.json`, plus command records, show unchanged file inventories, executable bits, HEAD, and index tree and no author trace. These snapshots cover worktree content; Git administrative caches/reflogs are outside the comparison. |
| Real shared-skill adoption | `agents/atlas-initial.*` and `agents/beacon-initial.*` preserve exact prompts, commands, JSONL execution/edit records, final responses, and exit codes. Before/adopted consumer copies retain actual README content and installed skills. Fresh processes receive only consumer-accessible tool/bootstrap/selection inputs. |
| Usable execution contract | `commands.jsonl`, consumer `.standards/events.jsonl`, and `.author-trace.jsonl` record literal argv, resolved-selection stdin, real stdout/stderr/exit results, and operation ordering. `missing-prerequisite.json` blocks before application; `malformed-result.json` rejects invalid results. Runtime presence is tested, not arbitrary dependency versions or sandboxing. |
| Exclusion under actual execution | `assertions-initial.json` and actual trace absence for excluded operations; employer `CONTRIBUTING.md` is byte-for-byte unchanged through adoption, update, checks, and recovery. Atlas's excluded contribution fix/check would impose a contradictory public policy if invoked. |
| Honest completion | Consumer `.standards/progress.json`, separate assessment and script records, unchanged HEAD snapshots, actual `git status`/diff in agent records, and `assertions-initial.json`. `finish` also rejects bypass of incomplete fixes (`incomplete-fix-gate.json`). Ordinary-work skills are installed for later activity. |
| Retained inputs and independent pins | `assertions-offline.json`, `run.json`, `publisher-history/*.bundle`, offline snapshots and fresh consumer inputs. The runner explicitly commits only after verifying no adoption commit, clones, removes publisher repositories, installs/verifies the pinned CLI outside the consumer, and exercises retained scripts/guidance/skills. A general 0.2.0 install cannot override the 0.1.0 project pin; a deliberate tool upgrade preserves standards selection. |
| Updated installed and contextual content | `agents/atlas-update.*`, `assertions-update.json`, and updated consumer copies. Skill replacement removes obsolete resources and adds `rounding.md`; actual README adaptation explains current `--precision` behavior and preserves the evolved Wednesday 16:00 Madrid note. Tool version remains 0.1.0. Retirement probes block until explicit preservation/relinquishment and remain labelled incomplete adoptions. |
| Conflict blocks whole update | Identical `snapshots/conflict-before.json` and `conflict-after.json`, `conflict.json`, and `conflict-reconciliation.json`. The injected local skill edit is explicitly restored to its baseline before the coherent update proceeds. |
| Failure and recovery | `injected-failure.json`, failure snapshots, `.standards/progress.json`, real `agents/recovery-recovery.*` execution, `.recovery-trace.jsonl`, and `assertions-recovery.json`. Actual partial files survive; the completed first fix runs once and only the failed second fix retries. No rollback is claimed. |
| Inspectable proof package | Immutable source above, `proof/README.md`, `proof/run.py`, exact zipapp hashes/catalogue, raw command and agent records, snapshots, publisher bundles, and before/after consumer content. This is a local deterministic proof with real contextual model calls, not a public distribution rehearsal. |
| Learning reconciled before further work | This report, ADR 0017, supersession notice on ADR 0016, glossary updates, and findings returned to #79. [Review-process follow-up #81](https://github.com/lutzseverino/repository-standards/issues/81) remains unready. #79 stays open without `ready-for-agent`; no downstream production tree was specified or dispatched. |

## Contextual usefulness assessment

The Atlas README demonstrates a real CSV invocation and observed JSON result,
explains actual numeric conversion/error handling, preserves the finance team's
local-data context, and defers to its employer-owned contribution policy.
Updated guidance leads a fresh agent to exercise `--precision`, describe the
observed default and rounding behavior, and preserve the current operational
note rather than overwrite it with publisher text.

The Beacon README uses the requested command-reference table, a real local and
HTTPS-link inventory example, observed error/exit behavior, offline limitations,
and the actual two-file example contract. The agent runs the regex parser and
identifies limitations of nested Markdown without claiming URL availability
checking. The two resulting READMEs are materially different and factually
useful for their existing small programs.

These conclusions come from reviewing source, observed commands, and the actual
prose. Passing structural/scripted checks alone does not establish them. The
experiment supplies a narrow positive result for small consumers; it does not
prove that an agent assessment field guarantees factual truth for arbitrary
projects.

## Findings and unresolved decisions

- Complete declarations are a workable inheritance unit. File/skill ownership
  and contextual guidance must remain explicit; operation metadata disappears
  with the replaced/excluded declaration.
- One shared skill can handle both authors without author adoption procedures.
  It must expose effective guidance and usable script results, with a real
  completion gate and diagnosable partial progress.
- Trusted scripts can act beyond their declaration. Selection input and result
  validation support cooperation and inspection, not containment or proof of
  arbitrary behavior. Fixture scripts demonstrably respect exclusions.
- Independent pins and retained inputs work locally. Production artifact
  acquisition, authentication/signatures, runtime/dependency version contracts,
  full YAML validation, concurrent-run safety, crash-safe installation, and
  assessment freshness still need decisions and evidence.
- Retired installed content needs an explicit decision. The proof's conservative
  option preserves its bytes and relinquishes management; exclusion alone
  grants no deletion authority. Additional retirement choices are unresolved.
- A deliberately failed script can preserve useful work and support retry when
  its effects and retry behavior are understandable. This does not establish
  universal idempotency, rollback, or recovery from every interruption point.
- No accepted product decision needs reopening on the evidence observed here.
  JSON-only YAML, local Git/depot transport, executable-presence prerequisites,
  and simple progress/assessment storage remain provisional limitations.
- A controlled public rehearsal is still required before release: independently
  publish a real author repository and immutable artifact, exercise topic-based
  discovery and known-source entry from a separate account/environment, and
  repeat installation, update, and fresh-checkout use against public transport.

The process concerns remain a separate investigation in #81: inherited
requirements, premature readiness, evidence delayed until the end, and review
bound to the final exact change. This proof and its dependency relationships do
not resolve them by themselves.
