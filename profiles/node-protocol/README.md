# Node protocol profile

This profile applies when `ecosystem=node`, `package-manager=npm`, and
`project-kind=protocol`. It inherits the Node npm exclusions and composes
protocol build and coverage exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance: include protocol compatibility, schema, and fixture checks in the
repository-owned aggregate validation command. Package-manager policy,
specifications, schemas, fixtures, package metadata, scripts, framework layout,
and release behavior remain repository-owned.
