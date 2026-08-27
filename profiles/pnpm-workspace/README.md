# pnpm workspace profile

This profile applies when `ecosystem=node`, `package-manager=pnpm`, and
`project-kind=workspace`. Its managed behavior is limited to composing Node and
pnpm generated-path exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance. A pnpm workspace can declare its package manager explicitly, for
example:

```json
{
  "packageManager": "pnpm@9.12.0"
}
```

Lockfile policy, install commands, workspace definitions, filters, scripts,
catalogs, package boundaries, dependency-update declarations, and package
manager upgrades remain repository-owned.
