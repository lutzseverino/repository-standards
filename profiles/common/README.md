# Common profile

Select this profile in every participating repository. It owns exact editor,
Git attribute, agent, contribution, GitHub issue-tracker, triage-label, blank
issue-intake, and workflow-validation files, inherits the upstream standard and
family-owned lifecycle skill bundles, and supplies the first `.gitignore`
fragment. It declares the required GitHub labels for live audit and
synchronization and declares retired issue-form and pull-request-policy files
absent. Dependabot configuration is rendered from the manifest's structured
dependency-update declarations.

It intentionally does not own the product README, license, security policy,
build manifests, main CI workflow, release workflow, domain documentation, or
documentation indexes.
Those artifacts either require repository-specific facts or differ by
ecosystem. The standards audit still validates the presentation and navigation
of README and documentation boundaries declared by the repository manifest.
