---
name: create-repository
description: Create a prepared local and GitHub repository baseline.
disable-model-invocation: true
---

# Create repository

Create one prepared creation baseline from settled repository facts.

1. Reuse facts already settled in the conversation or supplied specification.
   Collect only missing decisions before running anything. Repository name,
   one-line purpose, visibility, and license must be explicit. Establish enough
   applicability facts to prove every selectable ecosystem profile matches or
   cannot match. Infer the GitHub owner, local destination, and applicability
   facts only from unambiguous context; collect an unspecified ecosystem before
   invocation and ask only for unproven facts. This step is complete only when
   every selectable profile fully matches or conflicts with a settled fact.
   Express the license as an SPDX identifier or key from the selected standards
   release's pinned license catalog.
2. Run the repository goal interface with those facts. Pass an exact release when
   the user selected one; omit `--version` to select the latest stable release.
   Repeat `--fact NAME=VALUE` for applicability facts. When the user resolves an
   ambiguous match, repeat `--profile NAME` for every explicitly selected
   ecosystem profile.

   ```sh
   scripts/standards create \
     --name NAME \
     --purpose 'ONE LINE' \
     --visibility private \
     --license MIT \
     --owner OWNER \
     --destination /ABSOLUTE/PATH \
     [--fact NAME=VALUE ...] [--profile NAME ...] [--version VERSION]
   ```

3. Surface the goal's assessment, retained-state report, and recovery action.
   Completion means an uncommitted baseline on unborn `main`, an empty GitHub
   repository configured as `origin`, and first publication still required.
   Use the exact canonical phrase `first publication` in the final report and
   leave that separate operation for the user to invoke.

The operation creates standards and documentation content only. Product
scaffolding and package or build manifests remain outside this operation.
