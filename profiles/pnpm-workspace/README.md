# pnpm workspace profile

Declare exactly one package manager per install unit. During the v1 cohesion
rollout, pnpm workspaces use the established exact declaration:

```json
{
  "packageManager": "pnpm@9.12.0"
}
```

Track `pnpm-lock.yaml` and do not track `package-lock.json` or `yarn.lock` in
the same install unit. CI uses `pnpm install --frozen-lockfile` and a root
aggregate `pnpm check` command. Upgrade pnpm separately from standards adoption.

The workspace definition, filters, scripts, catalogs, and package boundaries
remain repository-owned.
