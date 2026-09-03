# Policy resolver model

Durable findings from the throwaway resolver prototype required by
[issue #69](https://github.com/lutzseverino/repository-standards/issues/69).
These findings constrain the production resolution and explanation work; they
do not make the prototype implementation or its filenames part of the product.
They refine the accepted separation of capability platform and policy system
recorded in
[ADR 0016](adr/0016-separate-capability-platform-from-policy-packs.md).

## Question and verdict

The prototype asked whether one deterministic resolver can combine one policy
pack, one independently selected workflow policy, zero or more ecosystem
profiles, and declared repository-local choices from verified local packages,
while rejecting ambiguity and explaining every effective fact with its owner
and provenance.

The model works with two important refinements. First, arbitrary key-value
contribution or repository-fact bags must not become production input. They
were convenient inside the prototype, but would defeat closed schemas and
typed extension points. Production inputs need kind-specific, closed payloads.
The resolver may normalize those payloads internally into canonical contract
addresses for ownership and provenance checks.

Second, a managed target can be either exclusive or explicitly composed.
Exclusive declarations retain one target owner. A composed target contains
several independently owned fragments whose order is explicit and independent
of package selection order. This preserves the current supported `.gitignore`
composition without weakening duplicate-ownership rejection.

The click-through primary source remains on the deliberately unmerged
[`test/policy-resolver-prototype-69`](https://github.com/lutzseverino/repository-standards/tree/d8c6223407b55fd0c867f146b42aea201f157341/scripts/prototypes)
branch. It is a single HTML file with a pure resolver module, free-play actions,
and guided walkthroughs. No production capability imports or invokes it.

## Governing invariants

The model is settled from six invariants rather than from a growing list of
special cases:

1. **One authority per subject.** Every machine fact, managed target,
   composition fragment, capability, and judgment-based policy subject has
   exactly one effective owner. The only replacement rule is an explicit,
   typed local choice at one pack-declared extension point.
2. **Trust before meaning.** Closed input shape, exact selection/lock
   correspondence, immutable identity, content integrity, metadata parity,
   and referenced-content presence are proven before any package declaration
   is interpreted.
3. **Orthogonal selection with explicit compatibility.** Pack, workflow, and
   profile selectors do not imply one another. Applicability, platform ranges,
   package constraints, and capability closure are the only compatibility
   gates; selection order is never one.
4. **Policy cannot become execution.** Packages own declarative policy and
   content. The capability platform owns executable behavior and safety
   boundaries. Repository-owned canonical validation crosses the resolver as
   literal data and is executable only by its platform capability.
5. **One deterministic result.** Resolution is pure and offline. Logical sets
   are normalized before hashing, output is canonically ordered, diagnostics
   are ordered by phase and subject, and any failed phase returns no partial
   contract or later-phase guesses.
6. **Migration transfers authority once.** Migration reads only the exact
   preceding stable declaration and release tree, assigns every retained fact
   one new owner, and retires the old owner. Ordinary resolution never accepts
   both architectures.

Every production field and resolver rule must discharge one of these
invariants. A proposed field with no unique authority, verification evidence,
compatibility semantics, canonical form, or migration disposition is not yet
part of the model.

| Invariant | Shape obligation | Resolver gate | Required evidence |
| --- | --- | --- | --- |
| One authority | Canonical subject addresses and typed extension points | Replacement, composition, policy-subject, and duplicate checks | Owner and declaration pointer for every effective subject |
| Trust before meaning | Complete coordinates, self-contained package references, exact lock entries | Lock bijection, digest, metadata, and reference validation | Configuration, package, and content digests plus immutable source revision |
| Orthogonal selection | One pack, one workflow, a set of profiles, typed constraints and applicability | Platform, package, profile, and capability checks | Selected coordinates and each compatibility or demand reason |
| Policy is not execution | Closed declarative package payloads and platform capability inventory | Reserved-authority and capability-closure checks | Platform owner for executable capabilities; repository owner for canonical validation |
| Deterministic result | Set semantics and canonical address forms | Phase barriers and canonical sorting | Stable contract, explanation, and diagnostics for equivalent input |
| Single migration | Exact source reader and complete transfer/retirement records | Migration before ordinary resolution | Old-to-new owner mapping and deletion audit |

## Evidence exercised

The prototype resolves this complete selection matrix through the same pure
interface:

| Policy pack | Workflow policy | Ecosystem profiles | Repository-local inputs |
| --- | --- | --- | --- |
| Compatibility | Planning-oriented | Zero | GitHub Projects enabled; validation argument `--strict` |
| Compatibility | Issue-directed | One (`node-npm`) | GitHub Projects enabled; validation with no arguments |
| Minimal | Planning-oriented | Several (`node-npm`, `vite-react`) | GitHub Projects enabled; validation argument `--all` |
| Minimal | Issue-directed | Zero | GitHub Projects explicitly disabled |

The two packs own materially different managed content, required labels, and
ruleset policy. The workflow choice changes process facts and capability roots
without changing pack or ecosystem facts. Profile selection changes only its
explicit repository-environment contributions.

The guided failure and migration cases demonstrate:

- ordinary resolution succeeds with the network disabled because the resolver
  accepts only local configuration, lock, acquired packages, and the pinned
  capability-platform inventory;
- the several-profile repository composes pack, `node-npm`, and `vite-react`
  `.gitignore` fragments with sole fragment owners and explicit orders;
- two ecosystem profiles claiming the same exclusive managed path fail with
  `ownership.duplicate`, independent of selection order;
- an ecosystem profile is rejected with
  `compatibility.capability.unsupported` when it requires a capability absent
  from the pinned platform;
- a selected npm profile is rejected with `profile.applicability.mismatch`
  when repository facts declare pnpm;
- otherwise non-colliding packages fail with
  `compatibility.package.required` when a typed package constraint is unmet;
- different document paths claiming the same policy subject fail with
  `policy.subject.duplicate`;
- changing an acquired policy document without changing the lock fails with
  `lock.content.tampered` before an effective contract is returned;
- changing duplicated lock metadata without changing the content-hashed
  manifest fails with `lock.metadata.mismatch` before either claim is used;
- adding a duplicate or unselected lock entry fails before package
  interpretation, because selected coordinates and lock entries form an exact
  bijection;
- a content-hashed manifest that references an omitted policy or managed file
  fails with `package.reference.missing`, even when its remaining bytes and
  regenerated digest are internally consistent;
- reversing the order-insensitive profile selectors, multi-value applicability
  facts, and lock entries produces the same configuration digest and
  byte-equivalent resolved contract;
- a package-managed target overlapping a repository-owned path fails with
  `ownership.repository-conflict`;
- every resolved fact identifies its sole owner, selected/default/local origin,
  source declaration, and evidence digest;
- the exact `5.0.0` declaration and its immutable commit and tree identities
  are both required to interpret inherited profile behavior and produce
  complete content, authority-transfer, and retirement plans.

## Deep module interface

Resolution and explanation belong behind the capability platform's one deep
module interface. The focused interface needed by the next production ticket
is logically:

```text
resolve(resolution request) -> resolution result
explain(resolved repository contract) -> structured and human explanation
```

A resolution request contains four inputs:

1. the closed repository configuration;
2. the closed lock;
3. the locally acquired package set named by that lock;
4. the pinned capability-platform release and capability inventory.

It has no network, package-discovery, GitHub, or mutation dependency. Setup and
update may acquire packages through an internal adapter before calling this
interface. Ordinary capabilities cross only this resolved-contract seam.

The result is a discriminated success or failure:

- success contains one normalized resolved repository contract and structured
  explanation evidence;
- failure contains ordered diagnostics and no partial contract.

Planning and application will later deepen the same capability-platform module
rather than introduce a second policy interpretation seam.

## Settled logical shapes

The names below describe logical records. Exact filenames and programming
language types remain production decisions.

### Repository configuration

The configuration contains:

- one policy-pack selector;
- one workflow-policy selector;
- an order-insensitive set of zero or more ecosystem-profile selectors;
- closed profile-applicability facts sufficient to prove every selected
  profile's predicate;
- typed local choices keyed only by extension points declared by the selected
  policy pack;
- closed repository-owned sections for repository identity, boundaries,
  dependency updates, canonical validation, GitHub declarations, local content
  fragments, variables, and repository-owned paths where those facts are not
  supplied as selected defaults.

Selectors identify a package coordinate. Setup may temporarily accept an
omitted version while resolving an acquisition plan, but the ordinary stored
configuration and lock used by capabilities must identify an exact version.
Duplicate selectors and duplicate local-choice keys fail explicitly. Logical
sets are normalized before the configuration digest is computed, so textual
reordering cannot stale a lock or change a contract. Unknown fields and
unknown choice keys fail explicitly.

Profile-applicability facts use a platform-defined closed vocabulary with
typed values and evidence pointers; they are not an open key-value bag. A
profile predicate can reference only that vocabulary and declares one required
value per field. A repository fact may carry one value or a canonical nonempty
set when the repository spans ecosystems; the predicate matches when its value
is present. Every referenced fact remains attributable to repository
configuration in explanation output.

Local choices are not last-wins overrides. A valid choice replaces exactly one
default at an extension point declared by the selected pack. Its effective
owner becomes repository configuration, its origin is `local-choice`, and its
explanation also names the pack declaration that permitted it.

Canonical validation is always a repository-configuration-owned declaration.
Package contributions and extension points cannot supply or replace its
executable, literal arguments, or working directory. The resolver carries that
declaration as data; only the lifecycle capability that needs it may execute
the validated literal process vector.

### Package envelope and kind-specific payloads

Every package has one common, content-hashed closed envelope:

- kind, publisher, name, and semantic version;
- supported capability-platform range;
- capability root names;
- closed inter-package `requires` and `conflicts` constraints over package
  kind, publisher, name, and semantic-version range;
- authoritative source attribution and license metadata;
- references to included content and policy documents.

The immutable locked identity is the complete coordinate, including kind,
publisher, name, and exact version. The manifest is authoritative for declared
publisher, source, license, compatibility, and capability roots. Source and
publisher remain separately visible trust roots so a change to either can
require renewed confirmation.

Each kind then has a distinct closed payload:

- a policy pack declares typed repository-environment defaults, extension
  points, authoritative policy documents, and optional non-binding workflow or
  profile recommendations;
- a workflow policy declares ordered process or transition facts, readiness
  criteria, authorization boundaries, and its authoritative workflow document;
- an ecosystem profile declares applicability plus explicit observable
  repository-environment contributions and its policy documents.

A selectable ecosystem profile must contribute observable repository-
environment behavior. Guidance without such behavior remains documentation,
not a selectable profile.

Policy packages contain declarative data and content only. They cannot contain
executable capability implementations or commands for the resolver to run.

Every requirement must match at least one selected complete package coordinate,
and every conflict must match none. A constraint declared by either side is
sufficient to reject a combination; packages do not repeat reciprocal rules.
Constraints have no arbitrary expressions, evaluation hooks, or selection-order
semantics.

Every policy-document declaration contains one platform-defined policy subject,
one content path, and its purpose. The subject—not its path—is the canonical
ownership address. No two selected policy-document declarations can claim the
same subject, whether they come from different packages or from the same
package and whether their paths or prose differ.

When an authoritative document is also emitted as managed repository content,
the same selected package owns both the policy subject and managed target. In
particular, the selected workflow policy owns the ordinary-change-workflow
subject and the managed `CONTRIBUTING.md`; a policy pack cannot supply a
competing copy.

Every managed-content and policy-document path must resolve to verified bytes
inside the declaring package. A valid package digest cannot make a dangling or
escaping reference meaningful.

### Lock and acquired packages

The lock contains:

- a lock format version;
- the complete capability-platform identity, immutable revision, and
  capability-inventory digest;
- a digest of the repository configuration it resolves;
- exactly one entry for every selected package and no unselected entries, with
  complete immutable coordinate, source and immutable source revision,
  license, compatibility declaration, package digest, and a sorted
  path-to-digest content inventory.

The locally acquired package set contains the closed package manifest and the
content bytes described by each lock entry. Resolution verifies selection,
identity, configuration freshness, duplicate, missing, or extra lock entries,
complete path inventory, individual content digests, aggregate package digest,
declared content references, and exact parity between every duplicated lock
field and its content-hashed manifest declaration before interpreting any
contribution. Extra, missing, changed, dangling, or contradictory content is an
integrity failure.

The lock is the acquisition authority for ordinary offline resolution: it
selects the complete immutable coordinate and exact source revision and pins
the manifest and content digests. Publisher, source, license, and compatibility
are copied into it for inspectability, not as a second policy authority. A copy
that differs from the verified manifest fails with `lock.metadata.mismatch`;
the resolver never chooses one claim over the other.

### Ownership index

After closed-shape and integrity validation, the resolver translates typed
inputs into an internal ownership index keyed by canonical addresses in the
resolved contract. Representative address families include:

- exclusive managed path or managed absence;
- composed managed fragment, identified within its parent target;
- declared GitHub field or required resource;
- repository-configuration-owned canonical-validation field;
- repository boundary, dependency-update declaration, or owned path;
- workflow process or readiness field;
- selected capability and platform-defined policy subject.

Each material address must have exactly one effective owner. Local choices use
the explicit extension replacement rule before duplicate detection. An exact,
template, tree-expanded, or absent managed declaration owns its target
exclusively and conflicts with every other declaration for that target.

Compose declarations may share a target only when every declaration for that
target is compose. Each fragment has a canonical address containing the target,
package identity, and package-local fragment identity, and that address has one
owner. Fragment order is explicit; duplicate fragment identities or ambiguous
orders fail rather than falling back to package or profile selection order.
Repository-local fragments are repository-configuration-owned and follow the
explicit order in their typed configuration section after package fragments.
The capability platform owns the composition operation, not the fragment
policy.

Selected capabilities are owned by the capability platform. Package root
demands are provenance edges rather than competing ownership claims. The index
retains every demanding package and declaration pointer for a root, plus every
capability-to-capability dependency edge in its transitive closure.

Every other collision fails. Values that happen to be equal still conflict
when owners differ, because authority would remain ambiguous.

Repository-owned path declarations are ownership guards, not ordinary facts
that can coexist with managed targets. Normalization matches every managed
path against those exact paths and closed path patterns before emission; an
overlap fails even when package ownership would otherwise be unique.

### Resolved repository contract

The normalized contract contains:

- exact selected platform, pack, workflow, and profile identities, including
  the platform revision and capability-inventory digest;
- typed effective repository facts, managed content and absences, declared
  GitHub state, canonical validation, repository ownership, and workflow facts;
- composed managed targets with their ordered, independently owned fragments
  and aggregate provenance;
- the platform-owned validated transitive capability closure, every package
  that demanded each root, and every transitive dependency reason;
- applicable authoritative policy documents;
- compatibility evidence for every selected package;
- provenance for every material effective fact.

Contract ordering is canonical and independent of input order. The contract
sorts every set-like selection, package, document, capability, ownership, and
diagnostic collection by its canonical identity or address. The contract does
not retain raw manifests as an alternate interpretation surface.

### Explanation

Structured explanation is a projection of the resolved contract, not a second
resolution pass. For every material fact it includes:

- normalized address and value;
- sole owner;
- origin such as `selected-default`, `workflow-policy`,
  `ecosystem-profile`, `local-declaration`, or `local-choice`;
- package identity and digest or configuration digest;
- declaration pointer;
- the extension-point declarer when a local choice replaced a default.

It also includes selected identities and provenance, policy documents,
capability closure and all package-root and transitive dependency reasons,
compatibility evidence, and each composed target's ordered fragment owners.
Stable human output renders this same structure; it does not reconstruct
provenance from decorative prose.

## Resolver order

The production resolver should perform phases in this order:

1. validate every closed input shape, selection cardinality, and set
   uniqueness;
2. prove that the lock matches the pinned platform and normalized
   configuration and is an exact bijection with selected coordinates;
3. verify selected identities, acquired content, package digests, exact
   lock/manifest metadata parity, and every in-package content reference;
4. validate package/platform compatibility;
5. validate every selected package's typed inter-package requirements and
   conflicts against the complete selected coordinates;
6. prove each selected ecosystem profile's applicability predicate against the
   closed repository facts, rejecting missing or nonmatching evidence;
7. validate transitive capability closure and cycles for roots from every
   selected package;
8. validate declared extension points, their one replaceable default, typed
   local choices, and reserved repository/platform authorities;
9. normalize typed contributions into the ownership index;
10. apply only explicit local-choice replacement;
11. validate exclusive targets, composed fragments, policy subjects, and
    repository-ownership guards;
12. reject every remaining duplicate owner;
13. emit the canonical contract and explanation evidence.

Later phases do not guess after an earlier authority or integrity failure. For
example, a tampered pack produces the tamper diagnostic rather than cascading
into misleading unknown-extension errors.

## Diagnostics

Diagnostics are structured records with:

- a stable code;
- the canonical subject or address;
- a plain-language message;
- all implicated source identities or declaration pointers;
- an actionable remediation.

They are ordered first by resolver phase and then by canonical subject. One
root cause is reported once even when several packages declare the same root or
that root also appears as a transitive dependency; the diagnostic retains every
implicated source. The prototype established these initial code families:

| Family | Representative codes |
| --- | --- |
| Selection | `selection.policy-pack.count`, `selection.workflow-policy.count` |
| Lock | `lock.platform.stale`, `lock.configuration.stale`, `lock.selection.missing`, `lock.selection.extra`, `lock.selection.duplicate` |
| Integrity | `lock.identity.mismatch`, `lock.metadata.mismatch`, `lock.content.missing`, `lock.content.tampered`, `package.reference.missing`, `package.reference.unsafe` |
| Compatibility | `compatibility.platform.unsupported`, `compatibility.package.required`, `compatibility.package.conflict` |
| Profile applicability | `profile.applicability.incomplete`, `profile.applicability.mismatch`, `profile.behavior.missing` |
| Capability closure | `compatibility.capability.unsupported`, `capability.cycle` |
| Local choice | `choice.undeclared`, `choice.type.invalid`, `choice.duplicate`, `choice.declaration.invalid`, `choice.reserved` |
| Policy authority | `policy.subject.duplicate` |
| Composition | `composition.mode.conflict`, `composition.fragment.duplicate`, `composition.order.ambiguous` |
| Ownership | `ownership.duplicate`, `ownership.repository-conflict`, `ownership.reserved` |

Production may add more specific codes, but should retain the phase and subject
structure rather than collapse failures into free-form exceptions.

## Migration from `5.0.0`

Migration is a separate setup operation, not an alternate input mode of the
ordinary resolver. Its reader accepts only the exact preceding stable contract
and immutable `v5.0.0` release tree, then produces the new resolver inputs and
a complete future mutation plan.

The migration result needs:

- source protocol, release, manifest digest, and release-tree identity;
- target compatibility pack and planning-oriented workflow selections;
- explicit mapping of selectable v5 ecosystem profiles to new package
  identities, while recording behavior absorbed from `common` and
  `documentation`;
- repository facts and evidence sufficient to prove every migrated ecosystem
  profile still applies;
- preservation of the ordered `common`, `node-npm`, and `vite-react`
  `.gitignore` fragments when those profiles are selected, with each fragment
  assigned to its new sole owner;
- preserved repository-specific boundaries, dependency updates, GitHub state,
  variables, local fragments, canonical validation when present, and
  repository ownership;
- exact packages to acquire and the lock information to produce;
- one fact-transfer record from each old field or inherited profile behavior to
  its new sole owner;
- obsolete generated artifacts and old authorities to retire;
- policy-equivalence evidence, blockers, and required maintainer work.

The source manifest alone cannot reconstruct inherited managed content, skill
registries, or profile provenance. The immutable `v5.0.0` tree is therefore a
required migration input. After successful migration, neither the old
declaration nor the old profile resolver is accepted by ordinary resolution.

## Production layout assumptions

The production layout should preserve these seams while allowing exact names
to change during implementation:

- start one capability-platform package under the existing `scripts/lib`
  implementation area; its package root owns the small external interface and
  hides validation, integrity, ownership, compatibility, normalization, and
  explanation internals;
- group the new closed JSON schemas by policy-environment concern under
  `schema`, including configuration, lock, common package envelope,
  kind-specific payloads, resolved contract, and explanation;
- keep first-party pack, workflow, and profile sources in a declarative source
  tree outside the executable capability-platform package, and keep platform
  capability content separately inventoried so package acquisition cannot add
  executable capabilities;
- keep acquired consumer packages in one managed internal store that is read as
  data and never added to the Python import path;
- resolve every package content reference within its immutable package root;
  reject absolute paths, parent traversal, and symlink escapes;
- treat generated contracts, explanations, plans, and harness adapters as
  projections or execution artifacts, never additional policy authorities;
- place the `5.0.0` migration reader with setup/adoption migration internals,
  outside the ordinary resolver interface;
- replace callers and tests at the resolved-contract seam rather than layering
  policy-aware paths beside `repository_contract.py` and profile inheritance;
- keep every production import and runtime path independent of
  `scripts/prototypes/`.

The deletion test for the new module is decisive: removing it should force
configuration, lock, integrity, ownership, compatibility, and explanation
logic back into every capability caller. Deleting an old resolver after the
cutover must not leave another ordinary path that can still interpret the same
facts.

## Constraints for the next ticket

Production resolution and explanation should retain the complete prototype
matrix and failure cases as interface-level tests, then add closed-schema and
runtime parity for malformed and unknown fields. Tests should assert observable
contracts and diagnostic records, not internal loader order or the provisional
prototype representation.

The prototype deliberately did not settle storage filenames, serialization
syntax, decorative human formatting, acquisition transport, or migration
mutation mechanics. Those choices may vary without changing the logical model
above.
