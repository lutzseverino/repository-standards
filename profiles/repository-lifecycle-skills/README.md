# Repository lifecycle skills profile

The common profile inherits this family-owned bundle so participating
repositories can create and publish repositories, adopt standards releases,
and deliver validated changes without depending on the separately pinned
upstream workflow bundle. Its inventory and license metadata identify the
repository family as the source. Each skill either carries its execution
adapter or performs the agent-owned transition directly, so participating
repositories do not depend on this standards source checkout.

The bundle contains:

- `adopt-standards` for deliberate stable-release adoption and its validated
  commit;
- `create-repository` for prepared creation baselines that still await first
  publication;
- `deliver-change` for explicitly confirmed GitHub delivery;
- `publish-repository` for the separately confirmed transition from a prepared
  creation baseline to a standards-complete repository.
