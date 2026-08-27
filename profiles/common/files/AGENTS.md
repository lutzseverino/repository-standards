# Agent guidance

Follow the repository's existing architecture, build tooling, and local
instructions. Keep changes scoped to the requested outcome and preserve
repository-specific behavior unless the task explicitly changes it.

Read `CONTRIBUTING.md` before preparing a change. Use the repository's declared
package or build manager and execute the manifest's structured canonical
validation with preserved argument boundaries and no shell interpretation.

Prefer durable rules in tests, tooling, and documentation over instructions
that exist only in agent context.

Respond in English regardless of the language used to address you. Use another
language when explicitly requested or when the content itself requires it,
such as quotations, translations, localized content, or language-specific
documentation.

## Standards release discovery

At the start of each agent session, run this check at most once:

```sh
sh .agents/scripts/discover-standards-release.sh
```

Cache that the check was attempted and cache its output for the session. Empty
output means that discovery is unavailable or no newer stable release exists;
it is not evidence that the repository is current. Do not run the check again
during the session.

Only the first substantive final response is eligible for an update notice. If
the cached output is a stable semantic version, immediately before that response
run the following command, replacing `AVAILABLE` with the cached version:

```sh
sh .agents/scripts/discover-standards-release.sh --notice AVAILABLE
```

The notice check rereads only the local manifest and makes no network request.
Append its non-empty output verbatim to the final response. Whether its output is
empty or non-empty, consider the notice handled and do not repeat it in later
responses.

## Agent skills

The repository skill setup is complete. Use the configuration below. Run
`setup-matt-pocock-skills` only when deliberately switching issue trackers or
rebuilding the configuration from scratch.

### Issue tracker

Issues and specifications are tracked in this repository's GitHub Issues. See
`docs/agents/issue-tracker.md`.

### Triage labels

Use the canonical category and state labels. See
`docs/agents/triage-labels.md`.

### Domain docs

Read the repository-owned domain-document configuration before exploring or
naming domain concepts. See `docs/agents/domain.md`.
