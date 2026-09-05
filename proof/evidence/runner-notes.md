# Execution provenance and runner correction

The retained `run/` package is the final actual run, starting at
`/private/tmp/standards-proof80-final`. A preliminary pair of fresh-agent runs
helped check the journey before tightening the completion gate; that preliminary
run is not used for the acceptance claims here.

All retained zipapp implementation files were compared byte-for-byte with
`proof/tool/` at capture. `run/depot/catalogue.json` and `SHA256SUMS.json` record
actual artifact/evidence hashes. The immutable Git commit containing this
package is the reference for the final reproducible source and fixtures;
`implementation_base` in run.json is the main-branch base at preparation, not a
claim that the prototype existed in that base commit.

The first offline runner attempt incorrectly used a string-prefix containment
assertion: sibling `fresh-install` was mistaken for a child of `fresh`. Setup
had successfully obtained the pinned artifact. The runner was corrected to use
path-component containment and resumed with the already committed/cloned
consumer after checking its Git identity. It did not repeat adoption or the
consumer commit. Both setup invocations remain in commands.jsonl. Publisher
repositories had already been archived as Git bundles and removed; none were
restored for the resumed offline exercise.

Snapshot comparison covers all worktree files, executable flags, symlink
identity, HEAD, and index tree; Git administrative caches/reflogs are outside
that comparison. The consumer copies carry actual before/after bytes. Agent
records preserve raw tool commands, edits, outputs, final messages and exits.
The malformed-result and retirement consumers intentionally remain incomplete
mechanical probes; they are not counted as successful adoptions.
