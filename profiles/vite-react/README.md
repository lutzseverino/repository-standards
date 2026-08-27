# Vite React profile

This profile applies when `ecosystem=node` and `framework=vite-react`. Its managed
behavior is limited to composing Vite, build, coverage, and TypeScript cache
exclusions into `.gitignore`.

## Guidance

The following guidance is advisory and is not assessed for standards
conformance. A React and Vite repository can expose an aggregate check such as:

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

The example scripts and `examples/ci.yml` are guidance rather than managed
files. Package-manager choice, scripts, tool selection, framework layout,
working directory, deployment behavior, and test scope remain
repository-owned. Select any other applicable package-manager profile alongside
this one.
