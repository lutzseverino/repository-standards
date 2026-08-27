# Standard agent skills profile

The common profile inherits this profile so every participating repository
receives the standard repository-local agent skills. This profile contains the
pinned upstream bundle only; family-owned repository lifecycle skills use their
own profile, inventory, and license.

The bundle is curated from the official `mattpocock-skills` plugin at
`84fdeffd12f2ee307994d1eb6feb48173b6e0502`. Its inventory records the canonical
workflow roots and their dependency graph; the selected skills are exactly that
transitive closure. Additions, removals, closure changes, and upgrades are
deliberate standards changes that repositories receive through standards
adoption.

Skills retired from the managed bundle are declared absent file by file. This
removes only previously managed artifacts while preserving unrelated
repository-owned skills under `.agents/skills/`.
