# Node protocol profile

Declare an exact npm package-manager version, commit `package-lock.json`, and
use `npm ci` in CI. Use Node.js 24 LTS unless a verified consumer constraint
requires Node.js 22.

Provide one aggregate `npm run check` script covering formatting, linting,
type-checking where applicable, tests, schema validation, and build output.
Protocol compatibility and fixture tests are part of the gate. Do not add
React-specific tooling to a protocol package.

Specifications, schemas, fixtures, package metadata, and release behavior stay
repository-owned.
