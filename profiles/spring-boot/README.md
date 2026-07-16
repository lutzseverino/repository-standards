# Spring Boot profile

The v1 shared baseline is Java 21, Spring Boot 4.0.6, Maven Wrapper, and
Spotless using Google Java Format. Lombok, MapStruct, OpenAPI generation,
Surefire, and generated-source integration should align where used; domain
dependencies and earned checks remain repository-specific.

Run Maven through `./mvnw`, including in documentation and CI. Pin the Maven
distribution and its checksum. The canonical local gate is normally:

```sh
./mvnw verify
```

Multi-module repositories may add explicit frontend or integration jobs while
retaining one workflow named `CI`.
