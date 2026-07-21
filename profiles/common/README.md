# Common profile

Select this profile in every participating repository. It owns exact editor,
Git attribute, agent, contribution, issue, pull-request, and GitHub Actions
workflow-validation files, and supplies the first `.gitignore` fragment. It
also owns the small pull-request policy check that makes branch, title,
issue-link, and body conventions executable. Dependabot configuration is
rendered from the manifest's structured dependency-update declarations.

It intentionally does not own the product README, license, security policy,
build manifests, main CI workflow, release workflow, or documentation indexes.
Those artifacts either require repository-specific facts or differ by
ecosystem. The standards audit still validates the presentation and navigation
of README and documentation boundaries declared by the repository manifest.
