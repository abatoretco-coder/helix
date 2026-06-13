"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { SourceHealthItem, SourceHealthResponse } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function SourcesPage() {
  const [items, setItems] = useState<SourceHealthItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "ok" | "warning" | "broken">("all");
  const [sortBy, setSortBy] = useState<"risk" | "errors" | "recent">("risk");
  const [search, setSearch] = useState("");
  const [actionBySource, setActionBySource] = useState<Record<number, string>>({});

  const loadSources = async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const data: SourceHealthResponse = await api.getSourceHealth();
      setItems(data.items);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadSources();
  }, []);

  const runSourceAction = async (sourceId: number, action: "enable" | "disable" | "refresh" | "reset-errors") => {
    setActionBySource((prev) => ({ ...prev, [sourceId]: action }));
    try {
      if (action === "enable") await api.enableSource(sourceId);
      if (action === "disable") await api.disableSource(sourceId);
      if (action === "refresh") await api.refreshSource(sourceId);
      if (action === "reset-errors") await api.resetSourceErrors(sourceId);
      await loadSources(true);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionBySource((prev) => {
        const next = { ...prev };
        delete next[sourceId];
        return next;
      });
    }
  };

  const rankedItems = [...items].sort((a, b) => {
    if (sortBy === "errors") {
      return (b.errors_24h || 0) - (a.errors_24h || 0);
    }

    if (sortBy === "recent") {
      const aStamp = new Date(a.last_checked_at || a.last_success_at || a.last_error_at || 0).getTime();
      const bStamp = new Date(b.last_checked_at || b.last_success_at || b.last_error_at || 0).getTime();
      return bStamp - aStamp;
    }

    const statusRank: Record<SourceHealthItem["status"], number> = {
      broken: 0,
      warning: 1,
      ok: 2,
    };

    const statusDelta = statusRank[a.status] - statusRank[b.status];
    if (statusDelta !== 0) return statusDelta;

    return (b.errors_24h || 0) - (a.errors_24h || 0);
  });

  const filteredItems = rankedItems.filter((item) => {
    if (filter !== "all" && item.status !== filter) return false;

    if (search.trim()) {
      const needle = search.toLowerCase();
      return (
        item.name.toLowerCase().includes(needle) ||
        item.source_type.toLowerCase().includes(needle) ||
        (item.category || "").toLowerCase().includes(needle)
      );
    }

    return true;
  });

  const stats = {
    total: items.length,
    ok: items.filter((s) => s.status === "ok").length,
    warning: items.filter((s) => s.status === "warning").length,
    broken: items.filter((s) => s.status === "broken").length,
    errors24h: items.reduce((sum, s) => sum + (s.errors_24h || 0), 0),
    items24h: items.reduce((sum, s) => sum + (s.items_24h || 0), 0),
    avgSuccessRate:
      items.length > 0
        ? items.reduce((sum, s) => sum + (s.extraction_success_rate_24h ?? 0), 0) / items.length
        : 0,
  };

  const refreshLabel = refreshing ? "Refreshing..." : "Refresh";

  if (loading) return <LoadingSpinner />;

  return (
    <div className="sources-page">
      <header className="hero">
        <div>
          <p className="eyebrow">Source health</p>
          <h1>Every source, ranked by reliability.</h1>
          <p className="hero-copy">
            Freshness, extraction success, error volume, and current status for the NAS source registry.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-panel-label">Coverage</span>
          <strong>{stats.total} sources</strong>
          <small>{Math.round((stats.avgSuccessRate || 0) * 100)}% mean extraction success</small>
          <button className="refresh-button" onClick={() => loadSources(true)} disabled={refreshing}>
            {refreshLabel}
          </button>
        </div>
      </header>

      {error && <ErrorMessage error={error} />}

      <div className="stats-grid">
        <div className="stat-card ok">
          <strong>{stats.ok}</strong>
          <span>OK</span>
        </div>
        <div className="stat-card warning">
          <strong>{stats.warning}</strong>
          <span>Warning</span>
        </div>
        <div className="stat-card broken">
          <strong>{stats.broken}</strong>
          <span>Broken</span>
        </div>
        <div className="stat-card">
          <strong>{stats.errors24h}</strong>
          <span>Errors 24h</span>
        </div>
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search source, type or category"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-buttons">
          {(["all", "ok", "warning", "broken"] as const).map((f) => (
            <button
              key={f}
              className={filter === f ? "active" : ""}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div className="filter-buttons">
          {(["risk", "errors", "recent"] as const).map((mode) => (
            <button
              key={mode}
              className={sortBy === mode ? "active" : ""}
              onClick={() => setSortBy(mode)}
            >
              {mode === "risk" ? "Risk first" : mode === "errors" ? "Most errors" : "Recently checked"}
            </button>
          ))}
        </div>
      </div>

      <div className="sources-grid">
        {filteredItems.length === 0 ? (
          <p className="no-sources">No sources match the current filters.</p>
        ) : (
          filteredItems.map((source) => (
            <article key={source.id} className={`source-card ${source.status}`}>
              <div className="source-header">
                <div>
                  <h3>{source.name}</h3>
                  <p className="meta">
                    {source.source_type} · {source.category} · priority {source.priority}
                  </p>
                </div>
                <span className={`status ${source.status}`}>{source.status}</span>
              </div>

              <div className="source-info">
                <div className="info-row">
                  <span className="label">Enabled</span>
                  <span className="value">{source.enabled ? "yes" : "no"}</span>
                </div>
                <div className="info-row">
                  <span className="label">Items 24h</span>
                  <span className="value">{source.items_24h}</span>
                </div>
                <div className="info-row">
                  <span className="label">Articles 24h</span>
                  <span className="value">{source.articles_24h}</span>
                </div>
                <div className="info-row">
                  <span className="label">Errors 24h</span>
                  <span className="value">{source.errors_24h}</span>
                </div>
                <div className="info-row">
                  <span className="label">Success rate</span>
                  <span className="value">
                    {source.extraction_success_rate_24h != null
                      ? `${Math.round(source.extraction_success_rate_24h * 100)}%`
                      : "n/a"}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Avg quality</span>
                  <span className="value">
                    {source.quality_avg != null ? source.quality_avg.toFixed(2) : "n/a"}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Last success</span>
                  <span className="value">
                    {source.last_success_at ? new Date(source.last_success_at).toLocaleString() : "—"}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Last error</span>
                  <span className="value">
                    {source.last_error_at ? new Date(source.last_error_at).toLocaleString() : "—"}
                  </span>
                </div>
              </div>

              {source.url && (
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-url">
                  Open source
                </a>
              )}

              <div className="source-actions">
                {source.enabled ? (
                  <button
                    className="action-button"
                    onClick={() => runSourceAction(source.id, "disable")}
                    disabled={Boolean(actionBySource[source.id])}
                  >
                    {actionBySource[source.id] === "disable" ? "Disabling..." : "Disable"}
                  </button>
                ) : (
                  <button
                    className="action-button"
                    onClick={() => runSourceAction(source.id, "enable")}
                    disabled={Boolean(actionBySource[source.id])}
                  >
                    {actionBySource[source.id] === "enable" ? "Enabling..." : "Enable"}
                  </button>
                )}

                <button
                  className="action-button"
                  onClick={() => runSourceAction(source.id, "refresh")}
                  disabled={Boolean(actionBySource[source.id])}
                >
                  {actionBySource[source.id] === "refresh" ? "Queueing..." : "Refresh soon"}
                </button>

                <button
                  className="action-button"
                  onClick={() => runSourceAction(source.id, "reset-errors")}
                  disabled={Boolean(actionBySource[source.id])}
                >
                  {actionBySource[source.id] === "reset-errors" ? "Resetting..." : "Reset errors"}
                </button>
              </div>
            </article>
          ))
        )}
      </div>

      <style jsx>{`
        .sources-page {
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
          font-size: clamp(2rem, 4vw, 3.25rem);
          line-height: 1.05;
          max-width: 14ch;
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

        .refresh-button {
          margin-top: 0.5rem;
          border-radius: 12px;
          border: 1px solid var(--color-border);
          background: rgba(255, 255, 255, 0.75);
          align-self: flex-start;
        }

        .refresh-button:disabled {
          opacity: 0.7;
          cursor: wait;
        }

        .hero-panel-label {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: var(--color-text-tertiary);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .stat-card {
          background: rgba(255, 255, 255, 0.75);
          border-radius: 16px;
          padding: 1rem;
          border: 1px solid var(--color-border);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }

        .stat-card strong {
          display: block;
          font-size: 2rem;
          color: var(--color-text);
        }

        .stat-card span {
          color: var(--color-text-secondary);
        }

        .stat-card.ok strong {
          color: var(--color-success);
        }

        .stat-card.warning strong {
          color: var(--color-warning);
        }

        .stat-card.broken strong {
          color: var(--color-error);
        }

        .toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          align-items: center;
          margin-bottom: 1.5rem;
        }

        .toolbar input {
          flex: 1;
          min-width: 260px;
          border: 1px solid var(--color-border);
          border-radius: 12px;
          padding: 0.85rem 1rem;
          background: white;
        }

        .toolbar > .filter-buttons:last-child {
          margin-left: auto;
        }

        .filter-buttons {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        button {
          background: white;
          border: 1px solid var(--color-border);
          padding: 0.55rem 1rem;
          border-radius: 999px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s;
        }

        button:hover {
          border-color: var(--color-primary);
          color: var(--color-primary);
        }

        button.active {
          background: var(--color-primary);
          color: white;
          border-color: var(--color-primary);
        }

        .sources-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1rem;
        }

        .source-card {
          border: 1px solid var(--color-border);
          border-radius: 18px;
          padding: 1.25rem;
          background: rgba(255, 255, 255, 0.85);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
        }

        .source-card.ok {
          border-left: 4px solid var(--color-success);
        }

        .source-card.warning {
          border-left: 4px solid var(--color-warning);
        }

        .source-card.broken {
          border-left: 4px solid var(--color-error);
        }

        .source-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .source-header h3 {
          margin: 0;
          font-size: 1.1rem;
          color: var(--color-text);
        }

        .meta {
          margin-top: 0.25rem;
          color: var(--color-text-tertiary);
          font-size: 0.88rem;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 999px;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .status.ok {
          background: rgba(45, 183, 69, 0.14);
          color: var(--color-success);
        }

        .status.warning {
          background: rgba(245, 158, 11, 0.14);
          color: var(--color-warning);
        }

        .status.broken {
          background: rgba(220, 38, 38, 0.14);
          color: var(--color-error);
        }

        .source-info {
          display: grid;
          gap: 0.35rem;
          margin-bottom: 1rem;
        }

        .info-row {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          font-size: 0.92rem;
        }

        .label {
          color: var(--color-text-tertiary);
        }

        .value {
          color: var(--color-text);
          font-weight: 600;
        }

        .source-url {
          color: var(--color-primary);
          font-weight: 600;
          text-decoration: none;
          display: inline-block;
          margin-bottom: 0.75rem;
        }

        .source-url:hover {
          text-decoration: underline;
        }

        .no-sources {
          color: var(--color-text-tertiary);
        }

        .source-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .action-button {
          border-radius: 8px;
          padding: 0.45rem 0.75rem;
          font-size: 0.85rem;
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
