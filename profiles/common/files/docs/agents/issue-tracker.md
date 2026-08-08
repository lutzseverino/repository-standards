# Issue tracker: GitHub

Incoming requests, specifications, and implementation tickets live in this
repository's GitHub Issues. Use the GitHub CLI for issue operations and infer
the repository from the current clone.

## Conventions

- Create an issue with `gh issue create`.
- Read an issue and its comments with `gh issue view <number> --comments`.
- List and filter issues with `gh issue list` and structured JSON output.
- Comment with `gh issue comment`.
- Apply or remove labels with `gh issue edit`.
- Close delivered work with `gh issue close`.

Incoming requests begin unlabelled and pass through `/triage`. Self-authored
specifications and implementation tickets use the planning workflow in
`CONTRIBUTING.md` and do not pass through triage.

Pull requests are not an incoming-request or triage surface.

## Relationships

Use GitHub sub-issues for parent specifications and implementation tickets. Use
native issue dependencies for blocking relationships where they are available;
otherwise record blockers in the issue body.

When a skill says to publish to the issue tracker, create a GitHub issue. When a
skill says to fetch a ticket, read the full issue body, labels, and comments.

This configuration follows the upstream setup contract at
[`84fdeffd`](https://github.com/mattpocock/skills/blob/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md).
