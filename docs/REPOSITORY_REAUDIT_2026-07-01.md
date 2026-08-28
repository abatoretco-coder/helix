# Reaudit repository - 2026-07-01

## Scope

Reaudit focused on repository health, dead-code signals, documentation drift, Docker/service readiness, Jarvis-facing API behavior, and security assumptions.

## Checks run

- `.\scripts\dev_check.ps1 -StaticOnly`
- `npm --prefix dashboard run build`
- `python -m ruff check services scripts clients/python/helix_agent_client docker`
- `python scripts\validate_sources.py --path config\sources.yaml --strict`

All checks passed before corrective edits.

## Findings

- The repository is structurally coherent and current static checks are green.
- Source registry validation passes with 275 configured sources.
- No actionable dead-code TODO/FIXME cluster was found during text scan.
- `/v1/news/items` and `/v1/news/summary` are now important product endpoints for Jarvis-style clients.
- `/v1/news/summary` defaulted to OpenAI while the README still promised that nothing leaves the NAS. This was the main product/security drift.
- The broader AI implementation is OpenAI-compatible when enabled. The deployment policy is OpenAI on demand only, with background AI disabled by default.
- `.env.example` duplicated `OPENAI_API_KEY`, which made deployment intent less clear.

## Corrections applied

- `/v1/news/summary` now defaults to local extractive bullets.
- OpenAI-compatible summarization is explicit opt-in with `NEWS_SUMMARY_PROVIDER=openai`.
- News summary responses now expose `summaryProvider`.
- `/v1/agent/capabilities` now reports news item and news summary support plus the configured summary provider.
- Docker Compose and `.env.example` now expose dedicated news-summary settings:
  - `NEWS_SUMMARY_PROVIDER`
  - `NEWS_SUMMARY_MODEL`
  - `NEWS_SUMMARY_TIMEOUT_SECONDS`
- README now documents `/v1/news/items`, `/v1/news/summary`, and the local-first/external-provider boundary.
- README now describes the current OpenAI-compatible AI provider behavior and stops implying that Ollama already powers every AI path.
- `scripts/deploy.sh` now skips Ollama by default; set `INSTALL_OLLAMA=true` only on machines that can run it.
- `scripts/smoke_test.sh` only requires Ollama when `INSTALL_OLLAMA=true`.
- Jarvis API contract now includes the news product endpoints.
- Roadmap now tracks live NAS validation, cited news summaries, OpenAI cost controls, and parked local-runtime work.

## Next priorities

1. Boot the full Docker stack when the NAS is available and run the runtime smoke test.
2. Validate `/v1/news/items` freshness and `/v1/news/summary` output against live articles.
3. Add citations to news summaries so Jarvis can return answer text with stable source references.
4. Add per-endpoint OpenAI usage counters and budget limits before enabling any background AI.
5. Resolve the documented Next.js security upgrade path after testing the Next 16 migration.
6. Keep Ollama work parked unless local hardware becomes available.
