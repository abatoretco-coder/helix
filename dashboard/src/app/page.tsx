"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Article, Briefing, PipelineStatus, SourceHealthResponse, Source } from "@/types";
import { ArticleCard, LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function Dashboard() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [sourceHealth, setSourceHealth] = useState<SourceHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionBySource, setActionBySource] = useState<Record<number, string>>({});
  const [actionFeedback, setActionFeedback] = useState<string>("");

  useEffect(() => {
    const load = async () => {
      try {
        const [articlesData, sourcesData, pipelineData, sourceHealthData] = await Promise.all([
          api.getArticles(10),
          api.getSources(),
          api.getPipelineStatus(),
          api.getSourceHealth(),
        ]);
        setArticles(articlesData);
        setSources(sourcesData);
        setPipelineStatus(pipelineData);
        setSourceHealth(sourceHealthData);

        try {
          const dailyBriefing = await api.getDailyBriefing();
          setBriefing(dailyBriefing);
        } catch {
          // Briefing not available yet
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const refreshSourcePanels = async () => {
    const [sourcesData, sourceHealthData] = await Promise.all([
      api.getSources(),
      api.getSourceHealth(),
    ]);
    setSources(sourcesData);
    setSourceHealth(sourceHealthData);
  };

  const runSourceAction = async (sourceId: number, action: "enable" | "disable" | "refresh" | "reset-errors") => {
    setActionBySource((prev) => ({ ...prev, [sourceId]: action }));
    try {
      if (action === "enable") await api.enableSource(sourceId);
      if (action === "disable") await api.disableSource(sourceId);
      if (action === "refresh") await api.refreshSource(sourceId);
      if (action === "reset-errors") await api.resetSourceErrors(sourceId);
      await refreshSourcePanels();
      setActionFeedback(`Source action '${action}' completed.`);
    } catch (err) {
      setActionFeedback(err instanceof Error ? err.message : "Source action failed");
    } finally {
      setActionBySource((prev) => {
        const next = { ...prev };
        delete next[sourceId];
        return next;
      });
    }
  };

  if (loading) return <LoadingSpinner />;

  const enabledSources = sources.filter((s) => s.enabled).length;
  const topArticles = articles.slice(0, 5);
  const queueDepths = pipelineStatus?.pipeline.queue_depths ?? {};
  const avgDurations = pipelineStatus?.pipeline.average_durations_last_24h_ms ?? {};
  const healthItems = sourceHealth?.items.slice(0, 5) ?? [];

  return (
    <div className="dashboard-container">
      <header className="hero">
        <div>
          <p className="eyebrow">Helix NAS cockpit</p>
          <h1>News intelligence, source health, and pipeline status in one place.</h1>
          <p className="hero-copy">
            A compact operator view for the NAS: ingestion, extraction, AI, clustering, briefings, and source reliability.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-panel-label">Updated</span>
          <strong>{pipelineStatus?.generated_at ? new Date(pipelineStatus.generated_at).toLocaleString() : "—"}</strong>
          <Link href="/operations" className="ops-link">Open operations</Link>
        </div>
      </header>

      {actionFeedback && <p className="action-feedback">{actionFeedback}</p>}

      <div className="stats-grid">
        <div className="stat-card">
          <h3>{pipelineStatus?.sources.total ?? sources.length}</h3>
          <p>Sources</p>
          <small>{pipelineStatus?.sources.enabled ?? enabledSources} enabled</small>
        </div>
        <div className="stat-card">
          <h3>{pipelineStatus?.pipeline.raw_items_today ?? 0}</h3>
          <p>Raw items today</p>
          <small>{pipelineStatus?.pipeline.raw_items_total ?? 0} total</small>
        </div>
        <div className="stat-card">
          <h3>{pipelineStatus?.pipeline.ai_processed_today ?? 0}</h3>
          <p>AI processed today</p>
          <small>{pipelineStatus?.pipeline.ai_processed_total ?? 0} total</small>
        </div>
        <div className="stat-card">
          <h3>{pipelineStatus?.pipeline.processing_errors_last_24h ?? 0}</h3>
          <p>Errors 24h</p>
          <small>{pipelineStatus?.sources.with_errors ?? 0} sources impacted</small>
        </div>
      </div>

      <section className="panel-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Pipeline Health</h2>
            <span className="panel-subtitle">Queues, throughput and latency</span>
          </div>
          <div className="health-grid">
            <div className="health-card">
              <span className="health-label">Queues</span>
              {Object.keys(queueDepths).length === 0 ? (
                <p className="health-value muted">No queue data</p>
              ) : (
                Object.entries(queueDepths).map(([name, value]) => (
                  <div key={name} className="health-row">
                    <span>{name}</span>
                    <strong>{value}</strong>
                  </div>
                ))
              )}
            </div>
            <div className="health-card">
              <span className="health-label">Durations</span>
              {Object.keys(avgDurations).length === 0 ? (
                <p className="health-value muted">No recent duration data</p>
              ) : (
                Object.entries(avgDurations).map(([step, value]) => (
                  <div key={step} className="health-row">
                    <span>{step}</span>
                    <strong>{value.toFixed(0)} ms</strong>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Source Health</h2>
            <span className="panel-subtitle">Most fragile sources first</span>
          </div>
          <div className="source-health-list">
            {healthItems.length === 0 ? (
              <p className="muted">No source health data yet.</p>
            ) : (
              healthItems.map((item) => (
                <div key={item.id} className={`source-health-item ${item.status}`}>
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.source_type} · {item.category} · priority {item.priority}</p>
                    <div className="source-actions">
                      {item.enabled ? (
                        <button disabled={Boolean(actionBySource[item.id])} onClick={() => runSourceAction(item.id, "disable")}>Disable</button>
                      ) : (
                        <button disabled={Boolean(actionBySource[item.id])} onClick={() => runSourceAction(item.id, "enable")}>Enable</button>
                      )}
                      <button disabled={Boolean(actionBySource[item.id])} onClick={() => runSourceAction(item.id, "refresh")}>Refresh</button>
                      <button disabled={Boolean(actionBySource[item.id])} onClick={() => runSourceAction(item.id, "reset-errors")}>Reset errors</button>
                    </div>
                  </div>
                  <div className="source-health-metrics">
                    <span>{item.status}</span>
                    <span>{item.items_24h} items / 24h</span>
                    <span>{item.errors_24h} errors</span>
                    <span>{item.extraction_success_rate_24h != null ? `${(item.extraction_success_rate_24h * 100).toFixed(0)}% success` : "n/a"}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </section>

      {briefing && (
        <section className="briefing-section">
          <h2>Daily Briefing</h2>
          <div className="briefing-content">
            {briefing.content ? (
              <div className="briefing-text">{briefing.content}</div>
            ) : (
              <p>Briefing generating...</p>
            )}
          </div>
        </section>
      )}

      <section className="articles-section">
        <h2>Top Articles</h2>
        {error && <ErrorMessage error={error} />}
        <div className="articles-grid">
          {topArticles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      </section>

      <style jsx>{`
        .dashboard-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem 1.25rem 3rem;
        }

        .hero {
          display: grid;
          grid-template-columns: 1.5fr 0.5fr;
          gap: 1rem;
          align-items: end;
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
          color: var(--color-text);
          font-size: clamp(2rem, 4vw, 3.5rem);
          line-height: 1.05;
          max-width: 12ch;
        }

        .hero-copy {
          margin-top: 1rem;
          color: var(--color-text-secondary);
          max-width: 60ch;
        }

        .hero-panel {
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.12), rgba(45, 183, 69, 0.12));
          border: 1px solid rgba(0, 102, 204, 0.12);
          border-radius: 18px;
          padding: 1rem 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .ops-link {
          margin-top: 0.4rem;
          font-weight: 700;
          color: var(--color-primary);
          text-decoration: none;
        }

        .ops-link:hover {
          text-decoration: underline;
        }

        .action-feedback {
          margin: 0 0 1rem;
          color: var(--color-primary);
          font-weight: 600;
        }

        .hero-panel-label {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: var(--color-text-tertiary);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .stat-card {
          background: rgba(255, 255, 255, 0.75);
          border-radius: 16px;
          padding: 1.5rem;
          border: 1px solid var(--color-border);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }

        .stat-card h3 {
          font-size: 2rem;
          margin: 0;
          color: var(--color-primary);
        }

        .stat-card p {
          margin: 0.5rem 0 0;
          color: #666;
        }

        .stat-card small {
          color: #999;
          font-size: 0.85rem;
        }

        .briefing-section {
          background: rgba(255, 255, 255, 0.8);
          border-left: 4px solid var(--color-primary);
          padding: 1.5rem;
          margin-bottom: 2rem;
          border-radius: 16px;
          border: 1px solid var(--color-border);
        }

        .briefing-content {
          background: white;
          padding: 1rem;
          border-radius: 12px;
          line-height: 1.6;
          max-height: 300px;
          overflow-y: auto;
        }

        .panel-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .panel {
          background: rgba(255, 255, 255, 0.8);
          border: 1px solid var(--color-border);
          border-radius: 18px;
          padding: 1.25rem;
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: baseline;
          margin-bottom: 1rem;
        }

        .panel-subtitle {
          color: var(--color-text-tertiary);
          font-size: 0.9rem;
        }

        .health-grid {
          display: grid;
          gap: 1rem;
        }

        .health-card {
          background: var(--color-surface);
          border-radius: 14px;
          padding: 1rem;
        }

        .health-label {
          display: block;
          margin-bottom: 0.75rem;
          font-size: 0.8rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--color-text-tertiary);
        }

        .health-row {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          padding: 0.4rem 0;
          border-bottom: 1px solid rgba(229, 231, 235, 0.8);
        }

        .health-row:last-child {
          border-bottom: 0;
        }

        .source-health-list {
          display: grid;
          gap: 0.75rem;
        }

        .source-health-item {
          padding: 1rem;
          border-radius: 14px;
          background: var(--color-surface);
          border: 1px solid rgba(229, 231, 235, 0.9);
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
        }

        .source-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-top: 0.5rem;
        }

        .source-actions button {
          border: 1px solid var(--color-border);
          border-radius: 8px;
          background: white;
          padding: 0.3rem 0.55rem;
          font-size: 0.8rem;
          font-weight: 600;
        }

        .source-health-item.ok {
          border-left: 4px solid var(--color-success);
        }

        .source-health-item.warning {
          border-left: 4px solid var(--color-warning);
        }

        .source-health-item.broken {
          border-left: 4px solid var(--color-error);
        }

        .source-health-item p,
        .source-health-metrics {
          color: var(--color-text-secondary);
          font-size: 0.92rem;
        }

        .source-health-metrics {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.2rem;
          white-space: nowrap;
        }

        .muted {
          color: var(--color-text-tertiary);
        }

        .articles-section {
          margin-top: 2rem;
        }

        .articles-grid {
          display: grid;
          gap: 1rem;
        }

        .article-card {
          background: white;
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1rem;
          transition: all 0.2s;
        }

        .article-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          border-color: #0066cc;
        }

        .article-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }

        .article-title {
          margin: 0;
          font-size: 1.1rem;
          color: #0066cc;
          cursor: pointer;
          text-decoration: none;
          flex: 1;
        }

        .article-title:hover {
          text-decoration: underline;
        }

        .score-badge {
          background: #0066cc;
          color: white;
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.85rem;
          white-space: nowrap;
        }

        .article-description {
          margin: 0.5rem 0;
          color: #666;
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .article-meta {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
          margin: 0.5rem 0;
          font-size: 0.85rem;
        }

        .badge {
          background: #f0f0f0;
          color: #333;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .badge.category {
          background: #e6f2ff;
          color: #0066cc;
        }

        .date {
          color: #999;
        }

        .spinner {
          text-align: center;
          padding: 2rem;
          color: #666;
        }

        .error-message {
          background: #fee;
          color: #c33;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 1rem;
        }
      `}</style>
    </div>
  );
}
