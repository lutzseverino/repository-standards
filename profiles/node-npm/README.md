# Node npm profile

Declare the exact npm version in `package.json`, commit `package-lock.json`, and
use `npm ci` in CI. Do not track pnpm or Yarn lockfiles in the same install unit.
Use Node.js 24 LTS unless a verified runtime constraint requires Node.js 22.

Provide one aggregate `npm run check` command. The package manifest, scripts,
dependency versions, and release behavior remain repository-owned.
