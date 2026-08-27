# Spring Boot profile

This profile applies when `ecosystem=java`, `framework=spring-boot`, and
`project-kind=service`. Its managed behavior is limited to composing Maven and
JVM generated-path exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance: choose a supported Java and Spring Boot combination, pin build
tooling, and expose a repository-owned aggregate validation command such as:

```sh
./mvnw verify
```

Java versions, dependencies, Maven Wrapper policy, plugins, module layout,
scripts, workflows, and dependency-update roots remain repository-owned.
