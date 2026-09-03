# Policy resolver model

Durable findings from the throwaway resolver prototype required by
[issue #69](https://github.com/lutzseverino/repository-standards/issues/69).
These findings constrain the production resolution and explanation work; they
do not make the prototype implementation or its filenames part of the product.

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
[`test/policy-resolver-prototype-69`](https://github.com/lutzseverino/repository-standards/tree/3bbc655423fbd4057a58217d05bd38a94e9efe6e/scripts/prototypes)
branch. It is a single HTML file with a pure resolver module, free-play actions,
and guided walkthroughs. No production capability imports or invokes it.

## Evidence exercised

The prototype resolves this complete selection matrix through the same pure
interface:

| Policy pack | Workflow policy | Ecosystem profiles | Local choice |
| --- | --- | --- | --- |
| Compatibility | Planning-oriented | Zero | Canonical-validation arguments |
| Compatibility | Issue-directed | One (`node-npm`) | GitHub Projects enabled |
| Minimal | Planning-oriented | Several (`node-npm`, `vite-react`) | Canonical-validation arguments |
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
- a workflow requiring a capability absent from the pinned platform fails with
  `compatibility.capability.unsupported`;
- changing an acquired policy document without changing the lock fails with
  `lock.content.tampered` before an effective contract is returned;
- every resolved fact identifies its sole owner, selected/default/local origin,
  source declaration, and evidence digest;
- the exact `5.0.0` declaration is sufficient to start migration, but its
  immutable release tree is also required to interpret inherited profile
  behavior and produce complete content and retirement plans.

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
- an ordered-insensitive set of zero or more ecosystem-profile selectors;
- typed local choices keyed only by extension points declared by the selected
  policy pack;
- closed repository-owned sections for repository identity, boundaries,
  dependency updates, canonical validation, GitHub declarations, local content
  fragments, variables, and repository-owned paths where those facts are not
  supplied as selected defaults.

Selectors identify a package coordinate. Setup may temporarily accept an
omitted version while resolving an acquisition plan, but the ordinary stored
configuration and lock used by capabilities must identify an exact version.
Unknown fields and unknown choice keys fail explicitly.

Local choices are not last-wins overrides. A valid choice replaces exactly one
default at an extension point declared by the selected pack. Its effective
owner becomes repository configuration, its origin is `local-choice`, and its
explanation also names the pack declaration that permitted it.

### Package envelope and kind-specific payloads

Every package has one common closed envelope:

- kind, publisher, name, and semantic version;
- supported capability-platform range;
- required capability names;
- authoritative source attribution and license metadata;
- references to included content and policy documents.

The immutable locked identity is the complete coordinate, including kind,
publisher, name, and exact version. Source and publisher remain separately
visible trust roots so a change to either can require renewed confirmation.

Each kind then has a distinct closed payload:

- a policy pack declares typed repository-environment defaults, extension
  points, capability requirements, authoritative policy documents, and
  optional non-binding workflow or profile recommendations;
- a workflow policy declares capability roots, ordered process or transition
  facts, readiness criteria, and its authoritative workflow document;
- an ecosystem profile declares applicability plus explicit observable
  repository-environment contributions and its policy documents.

Policy packages contain declarative data and content only. They cannot contain
executable capability implementations or commands for the resolver to run.

### Lock and acquired packages

The lock contains:

- a lock format version;
- the exact capability-platform identity;
- a digest of the repository configuration it resolves;
- one entry for every selected package, with complete immutable identity,
  publisher, source and immutable source revision, license, compatibility
  declaration, package digest, and a sorted path-to-digest content inventory.

The locally acquired package set contains the closed package manifest and the
content bytes described by each lock entry. Resolution verifies selection,
identity, configuration freshness, complete path inventory, individual content
digests, and aggregate package digest before interpreting any contribution.
Extra, missing, or changed content is an integrity failure.

The lock is the authority for ordinary offline resolution; the acquired
manifest cannot silently replace its identity, provenance, compatibility, or
license claims.

### Ownership index

After closed-shape and integrity validation, the resolver translates typed
inputs into an internal ownership index keyed by canonical addresses in the
resolved contract. Representative address families include:

- exclusive managed path or managed absence;
- composed managed fragment, identified within its parent target;
- declared GitHub field or required resource;
- canonical-validation field;
- repository boundary, dependency-update declaration, or owned path;
- workflow process or readiness field;
- selected capability and policy-document reference.

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

Every other collision fails. Values that happen to be equal still conflict
when owners differ, because authority would remain ambiguous.

### Resolved repository contract

The normalized contract contains:

- exact selected platform, pack, workflow, and profile identities;
- typed effective repository facts, managed content and absences, declared
  GitHub state, canonical validation, repository ownership, and workflow facts;
- composed managed targets with their ordered, independently owned fragments
  and aggregate provenance;
- the validated transitive capability closure and the package that demanded
  each root;
- applicable authoritative policy documents;
- compatibility evidence for every selected package;
- provenance for every material effective fact.

Contract ordering is canonical and independent of input order. The contract
does not retain raw manifests as an alternate interpretation surface.

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
capability closure and demand reasons, compatibility evidence, and each
composed target's ordered fragment owners. Stable human output renders this
same structure; it does not reconstruct provenance from decorative prose.

## Resolver order

The production resolver should perform phases in this order:

1. validate every closed input shape and selection cardinality;
2. prove that the lock matches the pinned platform and configuration;
3. verify selected identities, acquired content, and package digests;
4. validate package/platform and required-capability compatibility;
5. validate workflow capability closure and cycles;
6. validate declared extension points and typed local choices;
7. normalize typed contributions into the ownership index;
8. apply only explicit local-choice replacement;
9. validate exclusive targets and composed fragment identities and order;
10. reject every remaining duplicate owner;
11. emit the canonical contract and explanation evidence.

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
root cause is reported once even when a capability appears as both a declared
requirement and a workflow root. The prototype established these initial code
families:

| Family | Representative codes |
| --- | --- |
| Selection | `selection.policy-pack.count`, `selection.workflow-policy.count` |
| Lock | `lock.platform.stale`, `lock.configuration.stale`, `lock.selection.missing` |
| Integrity | `lock.identity.mismatch`, `lock.content.missing`, `lock.content.tampered` |
| Compatibility | `compatibility.platform.unsupported`, `compatibility.capability.unsupported` |
| Capability closure | `capability.missing`, `capability.cycle` |
| Local choice | `choice.undeclared`, `choice.type.invalid` |
| Composition | `composition.mode.conflict`, `composition.fragment.duplicate`, `composition.order.ambiguous` |
| Ownership | `ownership.duplicate` |

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
  tree outside the executable capability-platform package;
- keep acquired consumer packages in one managed internal store that is read as
  data and never added to the Python import path;
- place the `5.0.0` migration reader with setup/adoption migration internals,
  outside the ordinary resolver interface;
- replace callers and tests at the resolved-contract seam rather than layering
  policy-aware paths beside `repository_contract.py` and profile inheritance.

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
