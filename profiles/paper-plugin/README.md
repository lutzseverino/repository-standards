# Paper plugin profile

This profile applies when `ecosystem=java`, `framework=paper`, and
`project-kind=plugin`. Its managed behavior is limited to composing Maven,
JVM, and Paper runtime exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance: align Java and Paper compatibility deliberately, pin build tools,
and include meaningful verification in the repository-owned aggregate command.
Dependencies, Maven plugins, source layout, scripts, workflows, artifacts, and
publishing destinations remain repository-owned.
