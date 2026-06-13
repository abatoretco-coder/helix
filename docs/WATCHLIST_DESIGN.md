# Watchlist Design

## Goal

Track entities, topics, or keywords that require higher priority monitoring.

## Config file

- Path: `config/watchlist.yaml`
- Fields:
  - `entities`: explicit names (companies, people, products)
  - `keywords`: broad topic terms
  - `priority_boost`: optional numeric bonus in [0..1]

## Runtime behavior

- During AI scoring, if an article matches watchlist entities/keywords, increase personal relevance score.
- Keep matching deterministic and lightweight for NAS workloads.
