# Paper plugin profile

Use Java 17 for Paper compatibility, the Maven Wrapper, Maven Enforcer,
compiler, Surefire, JAR, Shade, JUnit, ArchUnit, and Spotless with Google Java
Format. Run the canonical gate through `./mvnw verify`.

The common release preamble uses explicit permissions, pinned Actions, a fixed
runner, concurrency, version validation, and a verified Maven build. Publishing
destinations remain repository-specific: GitHub, Modrinth, Hangar, or any later
target should not be hidden behind a pretend universal release workflow.
