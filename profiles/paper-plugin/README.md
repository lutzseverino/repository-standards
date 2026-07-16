# Paper plugin profile

Target Java 17 for Paper compatibility while running the build on JDK 21, which
is required by Google Java Format 1.35. Use the Maven Wrapper, Maven Enforcer,
compiler, Surefire, JAR, Shade, JUnit, ArchUnit, and Spotless. Run the canonical
gate through `./mvnw verify`.

The common release preamble uses explicit permissions, pinned Actions, a fixed
runner, concurrency, version validation, and a verified Maven build. Publishing
destinations remain repository-specific: GitHub, Modrinth, Hangar, or any later
target should not be hidden behind a pretend universal release workflow.
