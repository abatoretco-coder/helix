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
  const [filter, setFilter] = useState<"all" | SourceHealthItem["status"]>("all");
  const [bandFilter, setBandFilter] = useState<"all" | SourceHealthItem["quality_band"]>("all");
  const [languageFilter, setLanguageFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [sortBy, setSortBy] = useState<"health" | "value" | "errors" | "volume" | "recent">("health");
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

  const applyRecommendation = async (source: SourceHealthItem) => {
    const action = source.recommendation.action;
    setActionBySource((prev) => ({ ...prev, [source.id]: action }));
    try {
      if (action === "disable") {
        await api.disableSource(source.id);
      } else if (action === "refresh_or_disable" || action === "watch_stale") {
        await api.refreshSource(source.id);
      } else if ((action === "lower_priority" || action === "boost_priority") && source.recommendation.target_priority) {
        await api.updateSource(source.id, { priority: source.recommendation.target_priority });
      } else if (action === "monitor_errors") {
        await api.resetSourceErrors(source.id);
      }
      await loadSources(true);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recommendation failed");
    } finally {
      setActionBySource((prev) => {
        const next = { ...prev };
        delete next[source.id];
        return next;
      });
    }
  };

  const languages = Array.from(new Set(items.map((item) => item.language).filter(Boolean))).sort();
  const categories = Array.from(new Set(items.map((item) => item.category).filter(Boolean))).sort();
  const sourceTypes = Array.from(new Set(items.map((item) => item.source_type).filter(Boolean))).sort();

  const rankedItems = [...items].sort((a, b) => {
    if (sortBy === "errors") {
      return (b.errors_7d || 0) - (a.errors_7d || 0);
    }

    if (sortBy === "volume") {
      return (b.items_7d || 0) - (a.items_7d || 0);
    }

    if (sortBy === "value") {
      const aValue = (a.items_7d || 0) * (a.article_conversion_rate_7d ?? 0) * ((a.quality_avg || 0) / 100);
      const bValue = (b.items_7d || 0) * (b.article_conversion_rate_7d ?? 0) * ((b.quality_avg || 0) / 100);
      return bValue - aValue;
    }

    if (sortBy === "recent") {
      const aStamp = new Date(a.last_checked_at || a.last_success_at || a.last_error_at || 0).getTime();
      const bStamp = new Date(b.last_checked_at || b.last_success_at || b.last_error_at || 0).getTime();
      return bStamp - aStamp;
    }

    const statusRank: Record<SourceHealthItem["status"], number> = {
      broken: 0,
      warning: 1,
      disabled: 2,
      ok: 3,
    };

    const statusDelta = statusRank[a.status] - statusRank[b.status];
    if (statusDelta !== 0) return statusDelta;

    return (a.health_score || 0) - (b.health_score || 0);
  });

  const filteredItems = rankedItems.filter((item) => {
    if (filter !== "all" && item.status !== filter) return false;
    if (bandFilter !== "all" && item.quality_band !== bandFilter) return false;
    if (languageFilter !== "all" && item.language !== languageFilter) return false;
    if (categoryFilter !== "all" && item.category !== categoryFilter) return false;
    if (typeFilter !== "all" && item.source_type !== typeFilter) return false;

    if (search.trim()) {
      const needle = search.toLowerCase();
      return (
        item.name.toLowerCase().includes(needle) ||
        item.source_type.toLowerCase().includes(needle) ||
        (item.category || "").toLowerCase().includes(needle) ||
        (item.language || "").toLowerCase().includes(needle) ||
        item.diagnostics.some((reason) => reason.toLowerCase().includes(needle))
      );
    }

    return true;
  });

  const stats = {
    total: items.length,
    ok: items.filter((s) => s.status === "ok").length,
    warning: items.filter((s) => s.status === "warning").length,
    broken: items.filter((s) => s.status === "broken").length,
    disabled: items.filter((s) => s.status === "disabled").length,
    highValue: items.filter((s) => s.quality_band === "high_value").length,
    errors7d: items.reduce((sum, s) => sum + (s.errors_7d || 0), 0),
    items7d: items.reduce((sum, s) => sum + (s.items_7d || 0), 0),
    avgHealth:
      items.length > 0
        ? Math.round(items.reduce((sum, s) => sum + (s.health_score || 0), 0) / items.length)
        : 0,
  };

  const actionableRecommendations = [...items]
    .filter((source) => !["keep", "keep_disabled"].includes(source.recommendation.action))
    .sort((a, b) => {
      const severityRank = { high: 0, medium: 1, low: 2 };
      const severityDelta = severityRank[a.recommendation.severity] - severityRank[b.recommendation.severity];
      if (severityDelta !== 0) return severityDelta;
      return a.health_score - b.health_score;
    })
    .slice(0, 8);

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
          <small>{stats.avgHealth}/100 mean health score</small>
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
        <div className="stat-card disabled">
          <strong>{stats.disabled}</strong>
          <span>Disabled</span>
        </div>
        <div className="stat-card value">
          <strong>{stats.highValue}</strong>
          <span>High value</span>
        </div>
        <div className="stat-card">
          <strong>{stats.errors7d}</strong>
          <span>Errors 7d</span>
        </div>
        <div className="stat-card">
          <strong>{stats.items7d}</strong>
          <span>Items 7d</span>
        </div>
      </div>

      {actionableRecommendations.length > 0 && (
        <section className="recommendations-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Recommended actions</p>
              <h2>Source maintenance queue</h2>
            </div>
            <span>{actionableRecommendations.length} shown</span>
          </div>
          <div className="recommendations-list">
            {actionableRecommendations.map((source) => (
              <article key={source.id} className={`recommendation ${source.recommendation.severity}`}>
                <div>
                  <div className="recommendation-title">
                    <span>{source.recommendation.title}</span>
                    <small>{source.recommendation.severity}</small>
                  </div>
                  <strong>{source.name}</strong>
                  <p>{source.recommendation.detail}</p>
                  {source.recommendation.target_priority != null && (
                    <p className="target-priority">Target priority: {source.recommendation.target_priority}</p>
                  )}
                </div>
                <button
                  className="action-button"
                  onClick={() => applyRecommendation(source)}
                  disabled={Boolean(actionBySource[source.id]) || source.recommendation.action === "review_language"}
                >
                  {actionBySource[source.id]
                    ? "Applying..."
                    : source.recommendation.action === "disable"
                      ? "Disable"
                      : source.recommendation.action === "refresh_or_disable" || source.recommendation.action === "watch_stale"
                        ? "Refresh"
                        : source.recommendation.action === "monitor_errors"
                          ? "Reset errors"
                          : source.recommendation.action === "review_language"
                            ? "Review manually"
                            : "Apply"}
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search source, type, category, language or diagnostic"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-buttons">
          {(["all", "ok", "warning", "broken", "disabled"] as const).map((f) => (
            <button
              key={f}
              className={filter === f ? "active" : ""}
              onClick={() => setFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <select value={bandFilter} onChange={(event) => setBandFilter(event.target.value as typeof bandFilter)}>
          <option value="all">All bands</option>
          <option value="high_value">High value</option>
          <option value="healthy">Healthy</option>
          <option value="watch">Watch</option>
          <option value="noisy">Noisy</option>
          <option value="stale">Stale</option>
          <option value="broken">Broken</option>
          <option value="disabled">Disabled</option>
        </select>
        <select value={languageFilter} onChange={(event) => setLanguageFilter(event.target.value)}>
          <option value="all">All languages</option>
          {languages.map((language) => (
            <option key={language} value={language}>{language}</option>
          ))}
        </select>
        <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
          <option value="all">All categories</option>
          {categories.map((category) => (
            <option key={category} value={category}>{category}</option>
          ))}
        </select>
        <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
          <option value="all">All types</option>
          {sourceTypes.map((sourceType) => (
            <option key={sourceType} value={sourceType}>{sourceType}</option>
          ))}
        </select>
        <div className="filter-buttons sort-buttons">
          {(["health", "value", "errors", "volume", "recent"] as const).map((mode) => (
            <button
              key={mode}
              className={sortBy === mode ? "active" : ""}
              onClick={() => setSortBy(mode)}
            >
              {mode === "health"
                ? "Health risk"
                : mode === "value"
                  ? "Best value"
                  : mode === "errors"
                    ? "Most errors"
                    : mode === "volume"
                      ? "Most volume"
                      : "Recently checked"}
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
                    {source.source_type} · {source.category} · {source.language || "n/a"} · priority {source.priority}
                  </p>
                </div>
                <div className="badges">
                  <span className={`status ${source.status}`}>{source.status}</span>
                  <span className={`band ${source.quality_band}`}>{source.quality_band.replace("_", " ")}</span>
                </div>
              </div>

              <div className="health-meter">
                <div className="health-meter-label">
                  <span>Health score</span>
                  <strong>{source.health_score}/100</strong>
                </div>
                <div className="health-bar">
                  <span style={{ width: `${Math.max(0, Math.min(100, source.health_score))}%` }} />
                </div>
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
                  <span className="label">Items 7d</span>
                  <span className="value">{source.items_7d}</span>
                </div>
                <div className="info-row">
                  <span className="label">Articles 24h</span>
                  <span className="value">{source.articles_24h}</span>
                </div>
                <div className="info-row">
                  <span className="label">Articles 7d</span>
                  <span className="value">{source.articles_7d}</span>
                </div>
                <div className="info-row">
                  <span className="label">Errors 24h</span>
                  <span className="value">{source.errors_24h}</span>
                </div>
                <div className="info-row">
                  <span className="label">Errors 7d</span>
                  <span className="value">{source.errors_7d}</span>
                </div>
                <div className="info-row">
                  <span className="label">Success 7d</span>
                  <span className="value">
                    {source.extraction_success_rate_7d != null
                      ? `${Math.round(source.extraction_success_rate_7d * 100)}%`
                      : "n/a"}
                  </span>
                </div>
                <div className="info-row">
                  <span className="label">Raw to article 7d</span>
                  <span className="value">
                    {source.article_conversion_rate_7d != null
                      ? `${Math.round(source.article_conversion_rate_7d * 100)}%`
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
                <div className="info-row">
                  <span className="label">Dominant language</span>
                  <span className="value">
                    {source.dominant_article_language_7d || "n/a"}
                    {source.language_mismatch_rate_7d != null
                      ? ` · ${Math.round(source.language_mismatch_rate_7d * 100)}% mismatch`
                      : ""}
                  </span>
                </div>
              </div>

              <div className={`recommendation-note ${source.recommendation.severity}`}>
                <strong>{source.recommendation.title}</strong>
                <span>{source.recommendation.detail}</span>
              </div>

              <div className="diagnostics">
                {source.diagnostics.slice(0, 3).map((reason) => (
                  <span key={reason}>{reason}</span>
                ))}
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

        .stat-card.disabled strong {
          color: var(--color-text-tertiary);
        }

        .stat-card.value strong {
          color: var(--color-primary);
        }

        .recommendations-panel {
          border: 1px solid var(--color-border);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.82);
          padding: 1rem;
          margin-bottom: 1.5rem;
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
        }

        .section-heading {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-end;
          margin-bottom: 1rem;
        }

        .section-heading h2 {
          margin: 0;
          color: var(--color-text);
          font-size: 1.25rem;
        }

        .section-heading > span {
          color: var(--color-text-tertiary);
          font-weight: 700;
        }

        .recommendations-list {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 0.75rem;
        }

        .recommendation {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
          border: 1px solid var(--color-border);
          border-radius: 8px;
          padding: 0.85rem;
          background: white;
        }

        .recommendation.high {
          border-left: 4px solid var(--color-error);
        }

        .recommendation.medium {
          border-left: 4px solid var(--color-warning);
        }

        .recommendation.low {
          border-left: 4px solid var(--color-primary);
        }

        .recommendation-title {
          display: flex;
          gap: 0.5rem;
          align-items: center;
          color: var(--color-text);
          font-weight: 800;
          margin-bottom: 0.25rem;
        }

        .recommendation-title small {
          color: var(--color-text-tertiary);
          text-transform: uppercase;
          font-size: 0.7rem;
        }

        .recommendation strong {
          display: block;
          color: var(--color-text);
          margin-bottom: 0.2rem;
        }

        .recommendation p {
          margin: 0;
          color: var(--color-text-secondary);
          font-size: 0.86rem;
        }

        .target-priority {
          margin-top: 0.35rem !important;
          font-weight: 700;
        }

        .toolbar {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          align-items: center;
          margin-bottom: 1.5rem;
        }

        .toolbar input,
        .toolbar select {
          flex: 1;
          min-width: 260px;
          border: 1px solid var(--color-border);
          border-radius: 12px;
          padding: 0.85rem 1rem;
          background: white;
        }

        .toolbar select {
          flex: 0 1 170px;
          min-width: 150px;
        }

        .toolbar > .sort-buttons {
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

        .source-card.disabled {
          border-left: 4px solid var(--color-text-tertiary);
          opacity: 0.86;
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

        .status.disabled {
          background: rgba(100, 116, 139, 0.14);
          color: var(--color-text-tertiary);
        }

        .badges {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 0.35rem;
        }

        .band {
          padding: 0.25rem 0.65rem;
          border-radius: 999px;
          font-size: 0.76rem;
          font-weight: 700;
          text-transform: uppercase;
          color: var(--color-text-secondary);
          background: rgba(100, 116, 139, 0.12);
        }

        .band.high_value {
          background: rgba(0, 102, 204, 0.13);
          color: var(--color-primary);
        }

        .band.healthy {
          background: rgba(45, 183, 69, 0.14);
          color: var(--color-success);
        }

        .band.watch,
        .band.noisy,
        .band.stale {
          background: rgba(245, 158, 11, 0.14);
          color: var(--color-warning);
        }

        .band.broken {
          background: rgba(220, 38, 38, 0.14);
          color: var(--color-error);
        }

        .health-meter {
          margin-bottom: 1rem;
        }

        .health-meter-label {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          margin-bottom: 0.4rem;
          color: var(--color-text-secondary);
          font-size: 0.88rem;
        }

        .health-meter-label strong {
          color: var(--color-text);
        }

        .health-bar {
          height: 8px;
          border-radius: 999px;
          background: rgba(100, 116, 139, 0.14);
          overflow: hidden;
        }

        .health-bar span {
          display: block;
          height: 100%;
          min-width: 4px;
          border-radius: inherit;
          background: linear-gradient(90deg, var(--color-error), var(--color-warning), var(--color-success));
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

        .diagnostics {
          display: grid;
          gap: 0.35rem;
          margin: 0 0 0.85rem;
        }

        .diagnostics span {
          border-radius: 8px;
          background: rgba(15, 23, 42, 0.04);
          color: var(--color-text-secondary);
          font-size: 0.84rem;
          padding: 0.45rem 0.6rem;
        }

        .recommendation-note {
          border-radius: 8px;
          padding: 0.65rem 0.75rem;
          margin-bottom: 0.75rem;
          display: grid;
          gap: 0.2rem;
          background: rgba(15, 23, 42, 0.04);
          border: 1px solid rgba(15, 23, 42, 0.06);
        }

        .recommendation-note.high {
          background: rgba(220, 38, 38, 0.08);
          border-color: rgba(220, 38, 38, 0.18);
        }

        .recommendation-note.medium {
          background: rgba(245, 158, 11, 0.09);
          border-color: rgba(245, 158, 11, 0.2);
        }

        .recommendation-note strong {
          color: var(--color-text);
          font-size: 0.9rem;
        }

        .recommendation-note span {
          color: var(--color-text-secondary);
          font-size: 0.84rem;
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
