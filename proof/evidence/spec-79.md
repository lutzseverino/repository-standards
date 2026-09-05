## Problem Statement

Repository Standards currently couples its adoption mechanics to one opinionated repository environment. The previous redesign in #68 made some policy configurable, but still prescribed separate pack, workflow, and ecosystem selections; restricted executable capabilities to the platform; and required migration of the maintainer's existing conventions before proving independent authorship.

The intended product is a tool through which anyone can publish complete repository standards profiles containing their own guidance, files, skills, checks, and fixes. Another maintainer should be able to discover and adopt one profile, apply it to project-specific content, and deliberately update it without implementing adoption themselves or understanding this source checkout.

The existing downstream tickets were specified before the prototype intended to inform them. This replacement must first prove the author-to-adopter journey, incorporate the findings, and only then specify production work.

## Solution

Provide one shared adoption system, including the system-owned `adopt-standards` skill, and an author-facing standards format. Authors publish ordinary Git repositories containing shared defaults and complete named profiles. A repository adopts exactly one profile from one selected standards revision. The shared tool resolves that profile deterministically, installs exact supplied content and complete skills, coordinates agent adaptation of project-owned content, executes authored checks and fixes, and reports the evidence of completion.

There are three repository roles:

- This product's source repository maintains the format, CLI, shared system skills, and verification of their behavior.
- Independent standards repositories contain authors' conventions and their implementations, expressed through a root YAML declaration and ordinary referenced files.
- Adopting project repositories retain selected standards material, installed skills, and source/version records alongside their own product content.

The root author-facing declaration is named `standards.yaml`. It contains metadata, shared defaults, and named profiles. The precise public schema, script input/output contract, distribution commands, and internal layout are findings to settle through the first proof, not inherited obligations from #68 or a transcription of an illustrative YAML snippet.

Initial discovery uses a documented GitHub topic, and adoption also accepts a known repository source directly. A custom catalog is not required. Skills retain the Agent Skills format. Our own opinionated standards, their compatibility migration, and a broader community marketplace are deferred.

**Readiness:** this issue records the agreed product direction and discovery program. It is not a production implementation ticket and must not carry `ready-for-agent`. Ticketing is deferred to a separate session. That session should initially specify only the end-to-end prototype as executable work. Defining and dispatching downstream production work requires incorporating that proof's findings into this specification.

## User Stories

1. As a standards author, I want to publish from my own Git repository, so that publication does not require changes to this tool or admission to a hosted registry.
2. As an adopter, I want to discover profiles through GitHub topics or use a known source directly, so that discovery is useful without being mandatory for installation.
3. As an author, I want one root declaration identifying defaults and profiles, so that people and agents can inspect my offering in one place.
4. As an author, I want prose, scripts, and skills to remain ordinary referenced files, so that authoring does not require encoding every convention as structured data.
5. As an author, I want a complete profile to contain guidance, exact content, checks, fixes, and skills together, so that application mechanisms do not dictate separate packages.
6. As an author, I want shared defaults and independent profile variants, so that I can reuse common material without creating inheritance chains.
7. As an author, I want an absent override to inherit its default, so that common material need not be repeated unnecessarily.
8. As an author, I want a replacement to supply the complete declaration and whole file, so that resolution does not depend on agent-interpreted merging.
9. As an author, I want explicit exclusions to remove complete declarations and their associated governance, so that excluded targets are not still modified or checked by inherited operations.
10. As an author, I want a skill's directory and supporting resources replaced together, so that new instructions cannot accidentally retain incompatible old resources.
11. As an author, I want named repository-level declarations for concerns spanning files, so that layout and other broad conventions do not require fake managed output files.
12. As an author, I want to distinguish exact supplied content from guidance for repository-owned content, so that adoption knows when to install and when to adapt.
13. As an author, I want to provide my own ordinary-work skills and scripts, so that I can define a different development process without forking the tool implementation.
14. As an author, I want the system to supply adoption itself, so that I do not have to implement an adoption skill or lifecycle hooks.
15. As an adopter, I want one complete profile, so that the effective standards remain a coherent choice rather than a collection of adoption switches.
16. As an adopter, I want to use a lighter profile or fork for lasting deviations, so that constrained work repositories can use the system indefinitely.
17. As an author, I want to copy desired material into my own complete profile, so that initial selective reuse does not require a cross-publisher dependency system.
18. As an adopter, I want deterministic inspection without execution of author code, so that I can understand the profile and applicable operations before adoption.
19. As an adopter, I want one shared skill to apply exact files and contextual guidance, so that agent work and mechanical work are coordinated consistently across authors.
20. As an adopter, I want declared applicable fixes to run as part of adoption, so that scriptable changes do not become manual instructions.
21. As an author, I want ordinary scripts with declared invocation and dependencies, so that I can use appropriate existing runtimes rather than learn a new execution language.
22. As an adopter, I want missing prerequisites reported before their operations start, so that the tool does not silently install dependencies or fail through avoidable partial work.
23. As an author, I want scripts to receive the resolved selection, so that my implementation can respect active declarations and exclusions.
24. As an adopter, I want the system to be honest that authored scripts are trusted tooling, so that declaration validation is not misrepresented as sandboxing or proof of behavior.
25. As an adopter, I want required adoption work to be agent-completable, so that adoption does not end with a planned human-only checklist.
26. As an adopter, I want scripted verification distinguished from agent assessment, so that passing a headings check is not presented as proof that the README explains my product accurately.
27. As an adopter, I want success only after required changes are complete and applicable checks pass, so that incomplete runs are not reported as adopted.
28. As an adopter, I want successful changes left uncommitted, so that committing and delivery follow my selected repository workflow.
29. As an adopter, I want local edits to installed content preserved and detected, so that experimentation does not result in silent replacement during updates.
30. As an adopter, I want known installed-content conflicts to block the whole update before mutation, so that I can reconcile the intended profile before a coherent update begins.
31. As an adopter, I want updated guidance applied to current project-owned content, so that my evolving product description is not overwritten as though it were a supplied template.
32. As an adopter, I want interrupted work retained and resumable, so that an agent can diagnose and retry without blind repetition or fictional rollback guarantees.
33. As an adopter, I want exact tool and standards versions pinned independently, so that authors can release standards without releasing the CLI and routine work remains stable.
34. As an adopter, I want selected standards inputs and provenance committed in my project, so that a fresh checkout retains them even if the author's repository disappears.
35. As an adopter, I want the CLI installed at the project-pinned version, so that I do not have to carry its entire implementation in my repository.
36. As an adopter, I want a thin user bootstrap followed by local pinned system skills, so that first entry is simple and ongoing behavior is repository-specific and stable.
37. As an adopter, I want system skill names reserved, so that an author's ordinary-work skill cannot replace the adoption mechanism.
38. As a product maintainer, I want a real fresh-agent adoption journey across contrasting authors, so that the proof exercises the intended product rather than only a resolver fixture.
39. As a product maintainer, I want discovery findings reconciled before production ticketing, so that dependencies transfer knowledge instead of merely imposing execution order.

## Implementation Decisions

### Authoring and resolution

- Exactly two inheritance levels exist: shared defaults and one selected profile. There are no profile-to-profile chains, multiple simultaneously selected profiles, or consumer-selectable adoption groups.
- Each target's complete declaration is the inheritance unit: content or guidance and associated checks/fixes are inherited, completely replaced, or explicitly excluded together. Replacement can explicitly reference shared source material but does not inherit unmentioned metadata.
- File content uses whole-file replacement as a lasting rule. Skill content uses whole-directory replacement, including supporting scripts and resources. Resolution performs no Markdown merging or interpretation of merge instructions.
- Named repository-level declarations support concerns spanning files and follow the same complete-declaration rules.
- An exclusion removes the selected declaration's governance. It does not by itself authorize deleting an existing project-owned file. Previously installed content that becomes retired requires explicit update reconciliation; exact retirement semantics are a proof finding.
- Exact supplied content and requirements on project-owned content are explicitly distinguished. The system does not infer ownership or application mode from filenames or prose. Either can be accompanied by guidance, checks, and fixes.
- Profiles are complete choices. Lasting customization belongs in a different profile or fork. Initial reuse can copy material with its origins preserved; independently updateable per-part references across publishers are deferred.

### Shared adoption and execution

- The tool supplies one shared `adopt-standards` skill plus deterministic execution support. Authors supply conventions, content, ordinary-work skills, and optional checks/fixes; they do not implement adoption procedures or adoption hooks. Profiles and declarations can provide guidance or skills without scripted automation.
- Inspection resolves and explains selected material and operations without executing author-provided code or modifying the consumer repository.
- Adoption coordinates applicable declared fixes, exact installations, contextual agent work, and checks. The effective selection is settled before the adoption agent applies project-specific guidance.
- Scripts use ordinary runtimes with declared invocation and dependencies, literal argument boundaries, prerequisite checks, and a common result contract. Missing runtimes/dependencies are not silently installed. Precise input/output schemas and ordering must be exercised through the proof.
- Scripts receive the resolved selection and must respect it, including exclusions. They are trusted project tooling. The tool validates declarations and invocation results but does not claim to sandbox arbitrary code or prove its effects.
- All required adoption changes are intended to be completable by an agent. Reports distinguish automated verification from agent assessment. Success requires completed adoption changes and passing applicable checks; blocked execution is incomplete adoption, not success with a mandatory human checklist. Future-work conventions govern later activity and do not require adoption to execute every activity described by an ordinary-work skill.
- Successful adoption leaves verified work uncommitted. Committing and delivering it follows the selected repository workflow.

### Updates and distribution

- Tool version, standards revision, and selected profile are recorded explicitly. Tool and standards pins are independent. Version changes are deliberate operations, not background changes during routine use.
- Selected standards content, guidance, scripts, skills, and source/version records are retained in the consumer's committed material. A fresh checkout retains those inputs without relying on continued publisher availability.
- The CLI is an installed versioned dependency, not copied implementation in every consumer. Setup obtains the exact pinned version; the system verifies that version before operating. A general CLI installation update does not change the project pin.
- A thin user-installed bootstrap supports first adoption. Repository-local pinned system skills support ongoing use alongside selected author skills. System skill names are reserved against profile replacement.
- Known conflicts with edited installed content block the whole update before mutation. Compare against previously installed content, and reconcile the intended content or profile source before applying the new selection.
- Exact content updates and contextual guidance updates remain distinct: the former proposes a replacement; the latter applies changed requirements to current project-owned content.
- Failures after changes begin preserve uncommitted work. The agent diagnoses, repairs, and retries within the selected standards. Progress must support resumption without blindly repeating completed actions. If completion is impossible in that run, report actual changes and failure; do not discard work automatically or promise rollback of arbitrary scripts.

### Discovery-first delivery

- The first executable work is an isolated end-to-end prototype using two small independently authored sample standards repositories, contrasting complete profiles, and disposable consumers. It must not require reproducing the maintainer's existing standards.
- The prototype answers whether this authoring and adoption model works for outside authors. It can change provisional syntax and must expose any accepted decision that needs reconsideration rather than silently modifying it.
- Its output includes inspectable sample inputs/outputs, actual execution evidence, a public-format proposal, unresolved findings, and a verdict. Keep throwaway implementation outside the production path and preserve an immutable primary-source reference.
- Local immutable sources and an isolated installed CLI are sufficient for the first deterministic proof. An actual fresh agent must exercise contextual adoption through the shared skill; a mocked agent or prewritten output does not prove that behavior.
- Real public publication and topic discovery require a controlled rehearsal before release. Local fixtures are not evidence of public discoverability.
- Reconcile findings into this specification and relevant domain/architectural documentation before specifying the next executable production ticket. Do not create a ready downstream tree in advance.

## Testing Decisions

Test observable author and adopter behavior through the shared public adoption/inspection/update operations. An isolated CLI and disposable Git repositories exercise deterministic work; an actual fresh agent exercises the shared skill's interpretation and contextual adaptation. These are the primary evidence surfaces, not internal loaders or a decorative explanation view.

Use the existing content-reconciliation separation between comparison and application, repository-assessment reporting, literal-process execution, consumer journeys, and fresh-agent tests as prior art where useful. Their current mandatory profiles, fixed policy inventory, commit behavior, and old pack/workflow taxonomy are not requirements of the replacement.

The proof must include:

- Two authors with materially different guidance and ordinary-work skills, each with defaults and contrasting profiles, using the same shared adoption implementation without author-specific branches.
- Inherit, complete replacement, and exclusion for declarations; whole-file and complete-skill replacement; a repository-level concern; invalid references and conflicting declarations with understandable failures.
- Read-only inspection that executes no author code, plus declared dependencies and script invocation/results that can actually be used by the shared skill.
- Exact supplied content installation and real agent adaptation of an existing project's README, with machine evidence distinguished from contextual assessment.
- An excluded employer-owned contribution document unchanged by all remaining operations and not subjected to the excluded requirements.
- Completion without an automatic commit, and retained selected standards/provenance on a subsequent consumer checkout after publisher access is removed.
- Independent version pins and a deliberate update that changes a skill with supporting resources and guidance for evolving project-owned content.
- A known local installed-content conflict that blocks the entire update before any consumer mutation.
- A failure after application begins, truthful retained-progress evidence, and successful diagnosis/retry or an explicit incomplete verdict where blocked. Do not fake fresh-agent or recovery evidence.

Prefer a small reproducible scenario runner and focused assertions over a production-scale prototype test architecture. The aim is evidence for the design, not prematurely establishing permanent schemas or module layout. Preserve exact source references and an acceptance-to-evidence mapping so review can assess the complete proof.

## Out of Scope

- Implementing the full production redesign from this parent issue before the prototype and findings reconciliation.
- Preserving or migrating the maintainer's current opinionated standards as a prerequisite to the first proof.
- Multiple selected profiles, profile inheritance chains, adoption subsets, implicit local override layers, Markdown merging, or independent cross-publisher component updates.
- A custom discovery marketplace, hosted registry, ratings, or a publication-approval authority.
- Author-provided adoption implementations, hidden lifecycle hooks, replacing reserved system skills, or claiming to sandbox trusted author scripts.
- Automatic background standards/tool upgrades, silent dependency installation, automatic adoption commits, automatic discard of failed work, or universal rollback guarantees.
- A mandatory human-only adoption checklist.
- Application scaffolding and built-in remote GitHub lifecycle/reconciliation capabilities as requirements of the first proof. Repository guidance, development configuration, skills, templates, and CI files remain in scope; authors' ordinary-work skills are independently authored.
- Finalizing release packaging, source migration/cutover, exact command/result schemas, or the downstream production issue tree before the proof supplies evidence.
- Absorbing independent issue #67 or automatically changing the review/delivery workflow in this product-planning step.

## Further Notes

This specification replaces #68 and its undelivered implementation plan #70 through #77. Close those issues as not planned with an explicit supersession link; do not describe them as completed implementations. Retain #69 and merged PR #78 as historical work on the former model.

This direction supersedes the product constraints of ADR 0016 and the old resolver model where they require the former pack/workflow/ecosystem taxonomy, platform-only executable capabilities, compatibility-first migration, or a single mandatory standards workflow. Useful deterministic integrity, provenance, conflict reporting, and evidence practices may be retained, but the old artifacts must not silently expand the replacement's acceptance scope. Reconcile durable ADR/glossary documentation with these agreed decisions before production dispatch.

The original handoff also identified process defects: incomplete inherited requirement discovery, premature downstream readiness, backloaded evidence, and review not bound to the final exact change. The discovery-first frontier rule is adopted here. Broader workflow-skill revisions remain a focused follow-up; this specification does not assume new packaging alone fixes them.

No implementation tickets are created as part of this specification publication. A handoff will carry the next session into ticketing for the prototype alone. Readiness is separate from dispatch. Prototype completion must return findings to this specification before downstream production tickets are created or marked ready.

