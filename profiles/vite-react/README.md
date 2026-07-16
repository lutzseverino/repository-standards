# Vite React profile

Use React, Vite, strict TypeScript, and one canonical `check` script. Biome owns
formatting, import organization, and fast general lint rules. ESLint owns
type-aware TypeScript and React-specific rules not covered by Biome. Vitest is
included where behavior merits tests.

Recommended scripts:

```json
{
  "scripts": {
    "format": "biome format --write .",
    "lint:biome": "biome check .",
    "lint:eslint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "build": "vite build",
    "check": "npm run lint:biome && npm run lint:eslint && npm run typecheck && npm run test && npm run build"
  }
}
```

Replace `npm run` with `pnpm` inside a pnpm install unit. Add architecture
checks only when the repository has actual boundaries to enforce. The CI
example assumes npm; pnpm repositories should start from the pnpm-workspace
example and invoke their aggregate `check` script.

`examples/ci.yml` is guidance, not a managed file, because the gate, working
directory, deployment behavior, and test needs are repository-specific.
Select either `node-npm` or `pnpm-workspace` for the install unit.
