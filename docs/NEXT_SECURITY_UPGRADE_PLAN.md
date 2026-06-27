# Next.js Security Upgrade Plan

## Current state

`npm --prefix dashboard run audit:prod` reports advisories against the current Next 14 line and PostCSS dependency tree. The automatic npm fix proposes Next 16, which is a breaking framework upgrade for this dashboard.

## Decision

Do not run `npm audit fix --force` directly on the NAS deployment branch. Treat the upgrade as a compatibility project.

## Upgrade path

1. Create a dedicated branch for the dashboard framework upgrade.
2. Upgrade `next`, `eslint-config-next`, and related React tooling together.
3. Run:

```bash
npm --prefix dashboard install
npm --prefix dashboard run lint
npm --prefix dashboard run build
npm --prefix dashboard run audit:prod
```

4. Verify the dashboard routes manually:

- `/`
- `/articles`
- `/articles/[id]`
- `/briefings`
- `/clusters`
- `/inbox`
- `/jarvis`
- `/operations`
- `/projects`
- `/search`
- `/sources`
- `/watchlist`

5. Rebuild the Docker image and run the full stack smoke test.

## Deployment guardrails

- Keep the dashboard LAN-only until the upgrade is validated.
- Enable dashboard Basic Auth when exposing the UI beyond a trusted local network.
- Keep `REQUIRE_API_TOKEN=true` for `/v1` endpoints when integrating with Jarvis or other clients.
- Do not expose `NEXT_PUBLIC_HELIX_API_TOKEN` on a public dashboard.
