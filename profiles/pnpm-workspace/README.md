# pnpm workspace profile

Declare exactly one package manager per install unit. pnpm workspaces use the
established exact declaration:

```json
{
  "packageManager": "pnpm@9.12.0"
}
```

Track `pnpm-lock.yaml` and do not track `package-lock.json` or `yarn.lock` in
the same install unit. CI uses `pnpm install --frozen-lockfile` and a root
aggregate `pnpm check` command. `pnpm check` is the sole canonical gate; CI may
split it into jobs only when those jobs collectively execute every constituent
check. Upgrade pnpm separately from standards adoption.

Declare an `npm` dependency-update entry for the workspace root; Dependabot's
`npm` ecosystem supports pnpm lockfiles.

The workspace definition, filters, scripts, catalogs, and package boundaries
remain repository-owned.
