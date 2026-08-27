# Node npm profile

This profile applies when `ecosystem=node`, `package-manager=npm`, and
`project-kind=package`. Its managed behavior is limited to composing Node and
npm generated-path exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance: declare the npm version deliberately, commit the chosen lockfile,
use reproducible installs in CI, and expose one repository-owned aggregate
validation command. Package manifests, lockfile policy, scripts, dependency
versions, and release behavior remain repository-owned.
