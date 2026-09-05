# Planning, evidence, and final-change review investigation

This report answers the next planning step in
[issue #81](https://github.com/lutzseverino/repository-standards/issues/81)
for maintainers of this repository's ordinary workflow. It proposes focused
changes and observable acceptance criteria. It does not adopt those changes,
establish that the process defects are fixed, or specify a production tree for
the independent-profile product.

## Findings and scope

The handoffs need to carry applicable requirements, discovery findings,
required evidence, and exact source identities. Ordering tickets alone carries
none of that information. A successful product prototype likewise cannot prove
that planning and review skills reliably preserve it.

The source baseline inspected is
[`23b4d34`](https://github.com/lutzseverino/repository-standards/tree/23b4d349792dd8d8485c941cb02c35a94398dcde).
The links to local policy and skills below describe that baseline; future
changes to those files do not retroactively alter this investigation.
[Specification #79](https://github.com/lutzseverino/repository-standards/issues/79)
and [proof #80](https://github.com/lutzseverino/repository-standards/issues/80)
explicitly preserve this follow-up. The
[delivered proof report](independent-standards-proof.md) supplies a positive
product result with limits, not acceptance evidence for these proposed process
changes.

## Current handoffs

| Handoff | Existing instruction | Gap to address |
| --- | --- | --- |
| Planning to specification | [to-spec](../.agents/skills/to-spec/SKILL.md) explores the repository, respects ADRs, discusses test seams, then applies readiness when publishing. | No explicit distinction between an agreed discovery program and implementation-ready work; no required inherited-requirement or evidence map. |
| Specification to tickets | [to-tickets](../.agents/skills/to-tickets/SKILL.md) reads the supplied reference and comments, creates vertical slices and blocking edges, and defaults approved tickets to ready. | Approval of a breakdown and dependency ordering do not demonstrate that unresolved discovery findings have been incorporated. |
| Ticket to implementation | [implement](../.agents/skills/implement/SKILL.md) implements the supplied work, tests, reviews, and commits. | No explicit parent/decision/prior-review discovery procedure, early evidence feasibility check, or source identity binding between validation, review, and the final commit. |
| Implementation to review | [code-review](../.agents/skills/code-review/SKILL.md) resolves a base, finds a spec, and runs separate Standards and Spec agents over a diff. | A resolved base and a command containing moving `HEAD` do not freeze the reviewed candidate. The spec search does not explicitly traverse inherited requirements or require actual acceptance artifacts. |
| Review to delivery | [deliver-change](../.agents/skills/deliver-change/SKILL.md) isolates a candidate and rejects stale delivery evidence under [lifecycle policy](../standards/repository-lifecycle.md#github-delivery). | Useful existing precedent, but its delivery checks do not repair an earlier incomplete requirements or evidence handoff. |

These are observations about the instructions, not proof that every invocation
fails. [CONTRIBUTING.md](../CONTRIBUTING.md) already separates specification
readiness from dispatch and owns ordinary workflow policy.

## Concrete historical examples

The following first-party records were inspected on 2026-09-05. Issue bodies and
comments can be edited; review permalinks and immutable commits identify the
evidence where available. Public records do not reveal every local review.

### Inherited requirements found incrementally

PR #78's review found that rejecting duplicate managed targets lost existing
`.gitignore` composition across supported profiles. The
[finding](https://github.com/lutzseverino/repository-standards/pull/78#discussion_r3924086096)
led to a [corrected model and proof source](https://github.com/lutzseverino/repository-standards/pull/78#discussion_r3924185789).
Further reviews identified
[ADR 0012's canonical-validation ownership](https://github.com/lutzseverino/repository-standards/pull/78#discussion_r3924601009)
and [ADR 0009's policy authority across packages](https://github.com/lutzseverino/repository-standards/pull/78#discussion_r3924601041),
then [the same authority requirement within a package](https://github.com/lutzseverino/repository-standards/pull/78#discussion_r3924979680).
These are recorded omissions, not evidence that nobody read the parent.

The pattern also appeared during replacement-document reconciliation:
[ADR 0014 remained incompatible](https://github.com/lutzseverino/repository-standards/pull/82#discussion_r3941990588),
followed by [additional predecessor-chain omissions](https://github.com/lutzseverino/repository-standards/pull/82#discussion_r3942044974).
The process lesson is to trace the whole applicable requirement and supersession
chain rather than stop at the hunk named in one finding. The historical product
constraints themselves are not reinstated by this proposal.

### A dependency edge coexisted with premature readiness

[Ticket #70](https://github.com/lutzseverino/repository-standards/issues/70)
declared proof #69 as a blocker but received `ready-for-agent` on
2026-09-02 at 23:22:44 UTC, as recorded by its
[label event](https://api.github.com/repos/lutzseverino/repository-standards/issues/events/30451864781).
The [proof completion comment](https://github.com/lutzseverino/repository-standards/issues/69#issuecomment-5518871668)
was created on 2026-09-03 at 01:22:15 UTC and later edited. Its current contents
do not establish which findings existed at its creation time. #79 explicitly
records that downstream tickets were specified before the discovery intended to
inform them; [#70's later reconciliation](https://github.com/lutzseverino/repository-standards/issues/70#issuecomment-5554298628)
removed readiness and closed the superseded plan. This establishes premature
readiness, not that production implementation was dispatched.

### Evidence timing needs a prospective behavioral test

#81 explicitly identifies late evidence, especially actual fresh-agent runs,
as a concern. The [PR #78 validation report](https://github.com/lutzseverino/repository-standards/pull/78)
reports 21 authentication-gated test skips. However, #69's narrower resolver
prototype did not itself require fresh-agent contextual adoption. Those skips
do not establish a violation or a late attempted run. The inspected history
does not supply a timestamped incident proving that fresh-agent execution was
first attempted at completion.

By contrast, [#80's completion report](https://github.com/lutzseverino/repository-standards/issues/80#issuecomment-5554522882)
reports five actual consumer-agent runs and links retained evidence. Its
[immutable proof](https://github.com/lutzseverino/repository-standards/tree/3f0f48b95aba0aac67015f71db7e14f32ae4b7b7/proof)
and delivered acceptance map demonstrate how evidence can be made inspectable.
This investigation did not rerun those journeys. A controlled failure scenario
is needed to test early evidence handling in the proposed workflow.

### The last recorded review and final correction differ

The [last submitted PR #78 review](https://github.com/lutzseverino/repository-standards/pull/78#pullrequestreview-5102434117)
targets `fd253f6934835a9dae89eda65e1428230e4b8cbf` at 13:21:29 UTC on
2026-09-03. The final
[corrective commit](https://github.com/lutzseverino/repository-standards/commit/c1d37ce7f4a300090e9616a2ed9175fb140513b1)
is timestamped 13:22:11 UTC. The inspected public record contains no later
submitted review for that commit. Resolving the finding's thread does not
associate a review verdict with the changed source. This is an evidence gap;
it does not prove that no local rereview occurred or that the fix was wrong.

PR #82 provides a corrective example: its
[final rereview request](https://github.com/lutzseverino/repository-standards/pull/82#issuecomment-5554859661)
and [review response](https://github.com/lutzseverino/repository-standards/pull/82#issuecomment-5554891922)
identify `5fadf6e87236d8bcbafddd7049f74e94ab8c3868`, and the
[delivery report](https://github.com/lutzseverino/repository-standards/issues/80#issuecomment-5554919462)
records equality between the merged tree and that validated/reviewed candidate.
One corrected delivery does not establish reliable behavior across future
planning and implementation sessions.

## Proposed workflow changes

These proposals preserve [ADR 0004](adr/0004-separate-workflow-policy-from-execution-tooling.md)
and [ADR 0009](adr/0009-assign-one-living-owner-to-each-policy.md): ordinary
workflow rules belong in `CONTRIBUTING.md`; skills supply execution mechanics
and links to that owner. Delivery continues to use its existing lifecycle
owner. No additional approval ceremony or automatic dispatch service is proposed.

### Discover inherited requirements before narrowing work

At specification, ticketing, implementation, and Spec-review entry, collect the
referenced issue's full body/comments, parent specification, applicable linked
decisions, and prior review findings relevant to the changed behavior. Follow
explicit requirement and supersession links until their applicability is
resolved; keep visited references so cycles terminate. Unrelated tracker
history does not need exhaustive traversal.

Carry a compact requirement map with source reference, requirement, disposition
and reason, acceptance criterion, and required evidence. Dispositions distinguish
applicable, explicitly superseded, deferred by the authoritative scope, and
unresolved. A child ticket's omission is not a supersession. If sources conflict
or cannot be read, expose the affected gap and continue independent work without
claiming that the affected scope is settled. Ask only for a decision that cannot
be recovered from the existing authority.

Use the current accepted direction to interpret historical constraints.
[ADR 0017's predecessor map](adr/0017-independent-profiles-and-shared-adoption.md#relationship-to-earlier-decisions)
is a concrete example: it preserves applicable principles without reviving
superseded product requirements or changing the still-operational source
workflow. Record source revisions or retained issue snapshots and retrieval
times because issue bodies can change.

### Reconcile discovery before production readiness

Change `to-spec` and `to-tickets` mechanics so publication and breakdown approval
do not alone imply readiness. An agreed discovery program can remain unready
while one bounded proof is executable. Downstream implementation scope that
depends on its findings remains unspecified until the findings, unresolved
decisions, and acceptance-to-evidence map have been reconciled into the parent
and relevant domain/decision documents.

After reconciliation, assess each proposed ticket for complete scope, inherited
requirements, and achievable evidence. Dependencies still represent ordering;
they do not substitute for reconciliation. Independent sufficiently specified
work may remain ready. Readiness does not select, assign, or start any work.
If newly discovered evidence invalidates an existing readiness claim, report
the stale claim and reconcile it through the authorized tracker workflow;
never silently dispatch it.

### Identify required evidence before implementation

At planning and implementation entry, map each acceptance criterion to its
evidence producer, prerequisites, execution point, retained artifacts, and
failure meaning. Exercise feasibility early for scarce or external evidence,
such as availability of an authenticated fresh-agent harness. Do not silently
install prerequisites or expose credentials in retained records.

When actual fresh-agent behavior is required, plan an actual isolated run with
the skill, task inputs, and consumer-visible context. Retain the prompt, tool
execution record, source/input identities, before/after artifacts, outcome,
and contextual assessment. A mock harness can test orchestration but cannot
satisfy that behavioral criterion. An unavailable or skipped required run
remains a gap even if canonical validation passes. Continue useful independent
work, but report the required outcome incomplete until evidence exists.

Use the existing [fresh-agent delivery tests](../scripts/tests/test_delivery_fresh_agents.py)
as harness prior art, including their explicit opt-in skip behavior, and the
[proof acceptance map](independent-standards-proof.md#acceptance-to-evidence-map)
as reporting prior art. Neither is evidence that the proposed workflow changes
have been exercised.

### Bind validation and both reviews to the final source

Have `implement` pass an immutable base and candidate identity to `code-review`,
plus the requirement map and actual evidence references. Both review agents
receive the same identities. For uncommitted work, use an isolated snapshot
with a recorded tree identity covering all intended files, including new files;
exclude and preserve unrelated dirty work explicitly. Do not label a moving
`HEAD` command or an incomplete tracked-only diff as a frozen review input.

Record canonical validation's literal executable, ordered arguments, working
directory, result and skips against that source identity. Record the two review
verdicts against the same candidate and the identities of their evidence.
For an external proof, include the immutable proof source and its artifact
identities as well as the documentation candidate. A hash establishes identity,
not that an assertion is true; reviewers still inspect the relevant evidence.

Immediately before reporting completion, compare the committed tree with the
validated and reviewed tree and check evidence inputs for changes. Any
post-review change requires explicit renewed review of its effects. A narrow
documentation correction can receive a focused review when the reviewer states
why the remaining conclusions still apply; a changed requirement, executable,
fixture, or evidence producer requires the affected behavioral evidence and
reviews again. The resulting verdict must name the new candidate. Execute
canonical validation on the final content; never transfer an old pass merely
because an edit looks small.

Keep Standards and Spec verdicts separate. Missing required evidence is a Spec
gap, not a pass inferred from Standards or deterministic checks. Delivery
retains its existing candidate confirmation and stale-state gates.

## Observable acceptance criteria for a later implementation

The following scenarios are proposed tests, not executed results. Run them in
disposable repositories with a controlled tracker and actual fresh agents using
the distributed skills. Assert visible reads, writes, labels, source identities,
and completion claims from tool records and resulting artifacts; word matching
against a final response alone is insufficient.

| Scenario | Required observable result |
| --- | --- |
| Child omits an inherited constraint | A parent alone requires literal process arguments; an ADR explains ownership and an earlier review identifies the failure. Given only the child URL, implementation and Spec review retrieve those sources and include the requirement in their acceptance/evidence map. An otherwise passing child-only implementation is reported incomplete. |
| Explicit supersession and cyclic links | A replacement decision supersedes one old constraint while retaining another; linked issues cycle. Discovery terminates, cites the supersession, retains the still-applicable constraint, and does not resurrect the retired model. |
| Unreadable or conflicting authority | An applicable parent cannot be fetched, or two unreconciled decisions conflict. The missing/conflicting source is recorded; affected scope is not declared settled or complete. Independent work can continue. |
| Discovery before production scope | A parent approves a proof and leaves a schema decision open. Ticketing produces only the executable proof, with no ready downstream production tree, even if a proposed dependency edge exists. Closing the proof without reconciling its findings does not open that gate. |
| Reconciled findings and independent work | After evidence and decisions are incorporated into the parent/domain documents, only sufficiently specified tickets become eligible for readiness. An unrelated ready ticket remains unchanged. No readiness action starts an implementation session. |
| Required fresh-agent evidence unavailable | The implementation agent checks harness feasibility before substantial implementation. Missing access is recorded early; skipped tests or mocked output cannot yield an acceptance pass. Useful independent changes are retained with an incomplete verdict. |
| Required fresh-agent evidence available | A real fresh process receives only permitted fixture inputs, performs the contextual work, and leaves an inspectable prompt, execution trace, before/after content, and assessment. The acceptance map identifies that run and distinguishes it from scripted checks. |
| Mutation during or after review | Candidate A passes; change code, documentation, a new file, or required evidence to B in separate cases, including while one reviewer is running. Completion rejects A's stale verdict, obtains appropriate renewed review and validation, and reports B's exact identity. A failing B cannot inherit A's pass. |
| Multiple source artifacts | A report and a throwaway proof use different immutable commits. Both reviews identify both sources and inspect acceptance evidence; changing either source or evidence invalidates the affected conclusions. |
| Final commit and unrelated work | Review a complete candidate snapshot while unrelated dirty work exists. The final committed tree equals the validated/reviewed tree, includes intended new files, and preserves unrelated work. A commit-message-only change can preserve the source-tree evidence with an explicit identity association. |

Before accepting a future implementation, demonstrate at least one representative
failure with the existing skills, then execute all applicable scenarios against
the changed distributed skills. Retain exact source identities, raw records,
per-scenario assertions, and a requirements-to-evidence report. Report harness
availability, failures, skips, and review limits explicitly. Canonical validation
remains required; passing it alone does not establish these behavioral outcomes.

## Implementation boundary and remaining decision

The smallest proposed scope is ordinary workflow policy plus the `to-spec`,
`to-tickets`, `implement`, and `code-review` adapters and behavioral coverage of
their handoffs. Prefer their existing context/spec artifacts over a new package
model, workflow engine, or mandatory general-purpose evidence service. Planning
entry points can link to the common policy without duplicating it.

There is one distribution decision to settle before changing those adapters.
The current [skill inventory](../.agents/standard-skills.json) identifies an
exact upstream revision, and the [agent-skills profile](../profiles/agent-skills/README.md)
distributes that bundle. Recommend an upstream change and deliberate pin update
if available; otherwise specify an attributable maintained fork and its update
contract. Do not edit installed copies while claiming they are unchanged
upstream content. The release source, installed skills, provenance, and harness
adapters must agree in the eventual implementation.

This report supplies the investigation and proposed acceptance criteria. The
distribution choice and proposal acceptance remain planning decisions; no
workflow behavior is changed here. Independent #67, historical #69/#78, and the
product's production ticketing remain outside this follow-up's change scope.
