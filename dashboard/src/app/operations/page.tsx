"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Capabilities, DeadQueueDetail, DeadQueueOverview, OpsSummary } from "@/types";
import { ErrorMessage, LoadingSpinner } from "@/components/ArticleCard";

const PIPELINE_QUEUES = ["extract", "ai", "cluster", "briefing"] as const;
type PipelineQueueName = (typeof PIPELINE_QUEUES)[number];

const EXPECTED_SERVICES = [
  "postgres",
  "redis",
  "minio",
  "morss",
  "meilisearch",
  "ollama",
  "api",
  "freshrss",
  "worker_collect",
  "worker_extract",
  "worker_ai",
  "worker_cluster",
  "worker_briefing",
  "worker_cleanup",
  "dashboard",
  "prometheus",
];

export default function OperationsPage() {
  const [summary, setSummary] = useState<OpsSummary | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [deadOverview, setDeadOverview] = useState<DeadQueueOverview | null>(null);
  const [deadDetails, setDeadDetails] = useState<Record<string, DeadQueueDetail>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [queueAction, setQueueAction] = useState<Record<string, string>>({});

  const load = async (silent = false) => {
    if (silent) setRefreshing(true);
    else setLoading(true);
    try {
      const [ops, dead, caps] = await Promise.all([api.getOpsSummary(), api.getDeadQueues(), api.getCapabilities()]);
      setSummary(ops);
      setDeadOverview(dead);
      setCapabilities(caps);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load operations data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const loadDeadQueue = async (queue: PipelineQueueName) => {
    setQueueAction((prev) => ({ ...prev, [queue]: "load" }));
    try {
      const detail = await api.getDeadQueueItems(queue, 100);
      setDeadDetails((prev) => ({ ...prev, [queue]: detail }));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dead queue details");
    } finally {
      setQueueAction((prev) => {
        const next = { ...prev };
        delete next[queue];
        return next;
      });
    }
  };

  const retryDeadQueue = async (queue: PipelineQueueName) => {
    setQueueAction((prev) => ({ ...prev, [queue]: "retry" }));
    try {
      await api.retryDeadQueue(queue, 100);
      await Promise.all([load(true), loadDeadQueue(queue)]);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to retry dead queue");
    } finally {
      setQueueAction((prev) => {
        const next = { ...prev };
        delete next[queue];
        return next;
      });
    }
  };

  const purgeDeadQueue = async (queue: PipelineQueueName) => {
    if (!window.confirm(`Purge dead-letter queue '${queue}'? This cannot be undone.`)) {
      return;
    }
    setQueueAction((prev) => ({ ...prev, [queue]: "purge" }));
    try {
      await api.purgeDeadQueue(queue);
      await Promise.all([load(true), loadDeadQueue(queue)]);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to purge dead queue");
    } finally {
      setQueueAction((prev) => {
        const next = { ...prev };
        delete next[queue];
        return next;
      });
    }
  };

  const queueDepths = summary?.status.pipeline.queue_depths ?? {};
  const deadCounts = deadOverview?.queues ?? {};

  const totalDead = useMemo(
    () => Object.values(deadCounts).reduce((sum, count) => sum + (count || 0), 0),
    [deadCounts],
  );

  if (loading) return <LoadingSpinner />;

  return (
    <div className="ops-page">
      <header className="hero">
        <div>
          <p className="eyebrow">Operations</p>
          <h1>Queues, dead letters, and pipeline integrity.</h1>
          <p className="hero-copy">
            Operational cockpit for queue pressure, processing errors, and dead-letter maintenance.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-panel-label">Dead queue items</span>
          <strong>{totalDead}</strong>
          <small>{summary?.generated_at ? new Date(summary.generated_at).toLocaleString() : "—"}</small>
          <small>LLM: {summary?.configured_models.llm_model || "n/a"}</small>
          <small>Embedding: {summary?.configured_models.embedding_model || "n/a"}</small>
          <button onClick={() => load(true)} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {error && <ErrorMessage error={error} />}

      <section className="stat-grid">
        {PIPELINE_QUEUES.map((queue) => (
          <article key={queue} className="stat-card">
            <h3>{queue}</h3>
            <p>queue depth: {queueDepths[queue] ?? 0}</p>
            <p>dead letters: {deadCounts[queue] ?? 0}</p>
            <div className="actions">
              <button onClick={() => loadDeadQueue(queue)} disabled={Boolean(queueAction[queue])}>
                {queueAction[queue] === "load" ? "Loading..." : "Inspect"}
              </button>
              <button onClick={() => retryDeadQueue(queue)} disabled={Boolean(queueAction[queue])}>
                {queueAction[queue] === "retry" ? "Retrying..." : "Retry dead"}
              </button>
              <button className="danger" onClick={() => purgeDeadQueue(queue)} disabled={Boolean(queueAction[queue])}>
                {queueAction[queue] === "purge" ? "Purging..." : "Purge dead"}
              </button>
            </div>
            {deadDetails[queue] && (
              <details className="dead-items">
                <summary>Show latest dead payloads ({deadDetails[queue].count})</summary>
                <pre>{JSON.stringify(deadDetails[queue].items.slice(0, 5), null, 2)}</pre>
              </details>
            )}
          </article>
        ))}
      </section>

      <section className="ops-metrics-grid">
        <article className="metric-card">
          <h3>Pipeline Metrics</h3>
          <p>Raw items today: {summary?.status.pipeline.raw_items_today ?? 0}</p>
          <p>Articles today: {summary?.status.pipeline.articles_today ?? 0}</p>
          <p>AI processed today: {summary?.status.pipeline.ai_processed_today ?? 0}</p>
          <p>Briefings today: {summary?.status.pipeline.briefings_today ?? 0}</p>
        </article>
        <article className="metric-card">
          <h3>Source Health Summary</h3>
          <p>Total: {summary?.source_health_summary.total ?? 0}</p>
          <p>Enabled: {summary?.source_health_summary.enabled ?? 0}</p>
          <p>With errors: {summary?.source_health_summary.with_errors ?? 0}</p>
          <p>High error: {summary?.source_health_summary.high_error ?? 0}</p>
        </article>
        <article className="metric-card">
          <h3>System Flags</h3>
          <p>Low power mode: {summary?.low_power_mode ? "enabled" : "disabled"}</p>
          <p>Backup path: {summary?.backup.path || "n/a"}</p>
          <p>Backup exists: {summary?.backup.exists ? "yes" : "no"}</p>
          <p>Obsidian export: {summary?.obsidian_export.enabled ? "enabled" : "disabled"}</p>
        </article>
        <article className="metric-card">
          <h3>Capabilities</h3>
          <p>Inbox: {capabilities?.inbox ? "enabled" : "disabled"}</p>
          <p>Watchlist config: {capabilities?.watchlist_config ? "enabled" : "disabled"}</p>
          <p>Projects config: {capabilities?.research_projects_config ? "enabled" : "disabled"}</p>
          <p>Dead queues: {capabilities?.dead_queues ? "enabled" : "disabled"}</p>
          <p>Read state DB: {capabilities?.read_state_supported ? "enabled" : "not supported"}</p>
        </article>
      </section>

      <section className="services-panel">
        <h2>Expected services</h2>
        <div className="services-grid">
          {EXPECTED_SERVICES.map((name) => (
            <span key={name} className="service-chip">{name}</span>
          ))}
        </div>
      </section>

      <section className="errors-panel">
        <h2>Recent processing errors</h2>
        {summary?.recent_errors.items?.length ? (
          <ul>
            {summary.recent_errors.items.map((item: any) => (
              <li key={item.id}>
                <strong>{item.step}</strong> · {item.message || "No message"}
              </li>
            ))}
          </ul>
        ) : (
          <p>No recent errors.</p>
        )}
      </section>

      <style jsx>{`
        .ops-page {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem 1.25rem 3rem;
        }

        .hero {
          display: grid;
          grid-template-columns: 1.5fr 0.5fr;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.75rem;
          color: var(--color-text-tertiary);
          margin-bottom: 0.5rem;
        }

        h1 {
          margin: 0;
          font-size: clamp(2rem, 4vw, 3.25rem);
          line-height: 1.05;
        }

        .hero-copy {
          margin-top: 1rem;
          color: var(--color-text-secondary);
        }

        .hero-panel {
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.12), rgba(220, 38, 38, 0.12));
          border: 1px solid rgba(0, 102, 204, 0.16);
          border-radius: 16px;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .hero-panel button {
          margin-top: 0.5rem;
          align-self: flex-start;
        }

        .hero-panel-label {
          text-transform: uppercase;
          letter-spacing: 0.12em;
          font-size: 0.75rem;
          color: var(--color-text-tertiary);
        }

        .stat-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .ops-metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .metric-card {
          border: 1px solid var(--color-border);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.8);
          padding: 1rem;
        }

        .metric-card h3 {
          margin: 0 0 0.6rem;
        }

        .metric-card p {
          margin: 0.3rem 0;
        }

        .services-panel {
          border: 1px solid var(--color-border);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.8);
          padding: 1rem;
          margin-bottom: 1.5rem;
        }

        .services-panel h2 {
          margin: 0 0 0.8rem;
        }

        .services-grid {
          display: flex;
          flex-wrap: wrap;
          gap: 0.45rem;
        }

        .service-chip {
          border: 1px solid var(--color-border);
          border-radius: 999px;
          padding: 0.25rem 0.6rem;
          font-size: 0.82rem;
          background: var(--color-surface);
        }

        .stat-card {
          border: 1px solid var(--color-border);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.8);
          padding: 1rem;
        }

        .stat-card h3 {
          margin: 0 0 0.5rem;
          text-transform: capitalize;
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 0.75rem;
        }

        .actions button {
          border-radius: 8px;
          padding: 0.45rem 0.75rem;
        }

        .actions button.danger {
          border-color: #dc2626;
          color: #dc2626;
        }

        .dead-items {
          margin-top: 0.8rem;
        }

        pre {
          margin-top: 0.5rem;
          font-size: 0.75rem;
          max-height: 220px;
          overflow: auto;
          background: #0f172a;
          color: #e2e8f0;
          padding: 0.75rem;
          border-radius: 8px;
        }

        .errors-panel {
          border: 1px solid var(--color-border);
          border-radius: 14px;
          padding: 1rem;
          background: rgba(255, 255, 255, 0.8);
        }

        .errors-panel ul {
          margin: 0.75rem 0 0;
          padding-left: 1rem;
          display: grid;
          gap: 0.4rem;
        }

        @media (max-width: 900px) {
          .hero {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
