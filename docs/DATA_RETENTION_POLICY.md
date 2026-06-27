# Helix Data Retention Policy

- Raw HTML: 90 days
- Raw JSON: 365 days
- Failed/duplicate raw items: 14 days
- Text articles: permanent
- Embeddings: permanent
- Processing logs: 30 days
- Briefings: permanent
- Config: permanent

The cleanup worker records each run in `retention_jobs`, including DB row deletes and MinIO raw object deletes.
