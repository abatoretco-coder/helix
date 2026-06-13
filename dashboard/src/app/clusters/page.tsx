"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Cluster } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

type ClusterArticle = {
  id: number;
  url: string;
  title?: string;
  source?: string;
  source_name?: string;
  published_at?: string;
};

type ClusterDetail = Cluster & {
  articles?: ClusterArticle[];
  main_summary?: string;
  topic?: string;
  last_seen_at?: string;
};

export default function ClustersPage() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<ClusterDetail | null>(null);
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<"priority" | "size" | "recent">("priority");

  const loadClusters = async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const data = await api.getClusters(50);
      setClusters(data);
      setError("");
      if (data.length > 0 && !selectedClusterId) {
        await loadCluster(data[0].id, true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clusters");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadCluster = async (id: number, silent = false) => {
    setSelectedClusterId(id);
    if (!silent) {
      setDetailLoading(true);
    }

    try {
      const data = await api.getCluster(id);
      setSelectedCluster(data as ClusterDetail);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cluster");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const rankedClusters = useMemo(() => {
    const status = [...clusters];

    return status.sort((a, b) => {
      if (sortBy === "size") {
        return b.article_count - a.article_count;
      }

      if (sortBy === "recent") {
        const aStamp = new Date(a.last_seen_at || 0).getTime();
        const bStamp = new Date(b.last_seen_at || 0).getTime();
        return bStamp - aStamp;
      }

      return (b.importance_score || 0) - (a.importance_score || 0) || b.article_count - a.article_count;
    });
  }, [clusters, sortBy]);

  const filteredClusters = rankedClusters.filter((cluster) => {
    if (!search.trim()) return true;
    const needle = search.toLowerCase();
    return (
      (cluster.main_title || "").toLowerCase().includes(needle) ||
      (cluster.topic || "").toLowerCase().includes(needle)
    );
  });

  const stats = {
    total: clusters.length,
    articles: clusters.reduce((sum, cluster) => sum + cluster.article_count, 0),
    avgImportance:
      clusters.length > 0
        ? clusters.reduce((sum, cluster) => sum + (cluster.importance_score || 0), 0) / clusters.length
        : 0,
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="clusters-page">
      <header className="hero">
        <div>
          <p className="eyebrow">Cluster explorer</p>
          <h1>Track the event clusters that matter most.</h1>
          <p className="hero-copy">
            Group similar articles by event, inspect the strongest clusters first, and drill into the underlying
            sources without leaving the cockpit.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-panel-label">Coverage</span>
          <strong>{stats.total} clusters</strong>
          <small>{stats.articles} articles grouped</small>
          <button className="refresh-button" onClick={() => loadClusters(true)} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <strong>{stats.total}</strong>
          <span>Total clusters</span>
        </div>
        <div className="stat-card">
          <strong>{stats.articles}</strong>
          <span>Clustered articles</span>
        </div>
        <div className="stat-card">
          <strong>{Math.round(stats.avgImportance * 100)}%</strong>
          <span>Avg importance</span>
        </div>
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search cluster title or topic"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-buttons">
          {(["priority", "size", "recent"] as const).map((mode) => (
            <button
              key={mode}
              className={sortBy === mode ? "active" : ""}
              onClick={() => setSortBy(mode)}
            >
              {mode === "priority" ? "Priority" : mode === "size" ? "Largest" : "Recent"}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorMessage error={error} />}

      <div className="clusters-layout">
        <aside className="clusters-list">
          {filteredClusters.length === 0 ? (
            <p className="empty-state">No clusters match the current filters.</p>
          ) : (
            filteredClusters.map((cluster) => (
              <button
                key={cluster.id}
                className={`cluster-item ${selectedClusterId === cluster.id ? "active" : ""}`}
                onClick={() => loadCluster(cluster.id)}
              >
                <div className="cluster-head">
                  <h3>{cluster.main_title || cluster.topic || `Event #${cluster.id}`}</h3>
                  <span className="count">{cluster.article_count}</span>
                </div>
                <p className="cluster-topic">{cluster.topic || "Unspecified topic"}</p>
                <div className="cluster-footer">
                  <span>
                    {cluster.importance_score != null ? `${Math.round(cluster.importance_score * 100)}% importance` : "n/a"}
                  </span>
                  <span>{cluster.last_seen_at ? new Date(cluster.last_seen_at).toLocaleDateString() : "—"}</span>
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="cluster-detail">
          {detailLoading ? (
            <LoadingSpinner />
          ) : selectedCluster ? (
            <>
              <div className="detail-head">
                <div>
                  <p className="detail-label">Selected cluster</p>
                  <h2>{selectedCluster.main_title || selectedCluster.topic || `Cluster #${selectedCluster.id}`}</h2>
                </div>
                <span className="detail-pill">{selectedCluster.article_count} articles</span>
              </div>

              <div className="detail-grid">
                <div className="detail-card">
                  <span className="meta-label">Topic</span>
                  <strong>{selectedCluster.topic || "Unspecified"}</strong>
                </div>
                <div className="detail-card">
                  <span className="meta-label">Importance</span>
                  <strong>
                    {selectedCluster.importance_score != null
                      ? `${Math.round(selectedCluster.importance_score * 100)}%`
                      : "n/a"}
                  </strong>
                </div>
                <div className="detail-card">
                  <span className="meta-label">Last seen</span>
                  <strong>
                    {selectedCluster.last_seen_at ? new Date(selectedCluster.last_seen_at).toLocaleString() : "—"}
                  </strong>
                </div>
              </div>

              {selectedCluster.main_summary && (
                <div className="summary-box">
                  <span className="meta-label">Summary</span>
                  <p>{selectedCluster.main_summary}</p>
                </div>
              )}

              <div className="articles-section">
                <div className="section-head">
                  <h3>Articles in this cluster</h3>
                </div>

                {selectedCluster.articles && selectedCluster.articles.length > 0 ? (
                  <div className="article-list">
                    {selectedCluster.articles.map((article) => (
                      <article key={article.id} className="article-item">
                        <div>
                          <a href={article.url} target="_blank" rel="noopener noreferrer">
                            {article.title || `Article #${article.id}`}
                          </a>
                          <p className="article-meta">
                            {article.source || article.source_name || "Unknown source"}
                            {article.published_at ? ` · ${new Date(article.published_at).toLocaleString()}` : ""}
                          </p>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">No article list was returned for this cluster yet.</p>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state detail-empty">
              Select a cluster to inspect the detail view.
            </div>
          )}
        </section>
      </div>

      <style jsx>{`
        .clusters-page {
          max-width: 1400px;
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

        .eyebrow,
        .hero-panel-label,
        .meta-label,
        .detail-label {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.75rem;
          color: var(--color-text-tertiary);
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
          max-width: 64ch;
        }

        .hero-panel {
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.12), rgba(45, 183, 69, 0.12));
          border: 1px solid rgba(0, 102, 204, 0.12);
          border-radius: 18px;
          padding: 1rem 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }

        .refresh-button {
          margin-top: 0.4rem;
          border: 1px solid var(--color-border);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.8);
          align-self: flex-start;
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

        .clusters-layout {
          display: grid;
          grid-template-columns: 380px 1fr;
          gap: 1rem;
          align-items: start;
        }

        .clusters-list,
        .cluster-detail {
          border: 1px solid var(--color-border);
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.85);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
        }

        .clusters-list {
          overflow: hidden;
        }

        .cluster-item {
          width: 100%;
          text-align: left;
          border: 0;
          border-bottom: 1px solid var(--color-border);
          border-radius: 0;
          background: transparent;
          padding: 1rem;
          display: grid;
          gap: 0.35rem;
        }

        .cluster-item:hover {
          background: rgba(0, 102, 204, 0.04);
        }

        .cluster-item.active {
          background: rgba(0, 102, 204, 0.08);
          box-shadow: inset 3px 0 0 var(--color-primary);
        }

        .cluster-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 1rem;
        }

        .cluster-head h3 {
          margin: 0;
          color: var(--color-text);
          font-size: 1rem;
          line-height: 1.35;
        }

        .count {
          flex: none;
          border-radius: 999px;
          background: rgba(0, 102, 204, 0.1);
          color: var(--color-primary);
          padding: 0.18rem 0.6rem;
          font-weight: 700;
          font-size: 0.8rem;
        }

        .cluster-topic,
        .cluster-footer,
        .article-meta,
        .empty-state {
          color: var(--color-text-secondary);
          font-size: 0.92rem;
        }

        .cluster-footer {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .cluster-detail {
          padding: 1.25rem;
          display: grid;
          gap: 1rem;
        }

        .detail-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
        }

        .detail-head h2 {
          margin: 0.25rem 0 0;
          color: var(--color-text);
          font-size: 1.5rem;
        }

        .detail-pill {
          border-radius: 999px;
          background: rgba(45, 183, 69, 0.12);
          color: var(--color-success);
          padding: 0.3rem 0.75rem;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.75rem;
        }

        .detail-card,
        .summary-box,
        .article-item {
          border: 1px solid var(--color-border);
          border-radius: 16px;
          background: rgba(249, 250, 251, 0.92);
        }

        .detail-card {
          padding: 1rem;
        }

        .detail-card strong {
          display: block;
          margin-top: 0.25rem;
          color: var(--color-text);
        }

        .summary-box {
          padding: 1rem;
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.08), rgba(45, 183, 69, 0.08));
        }

        .summary-box p {
          margin-top: 0.35rem;
          color: var(--color-text-secondary);
          line-height: 1.65;
        }

        .section-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
          margin-bottom: 0.75rem;
        }

        .section-head h3 {
          margin: 0;
          color: var(--color-text);
        }

        .article-list {
          display: grid;
          gap: 0.75rem;
        }

        .article-item {
          padding: 1rem;
        }

        .article-item a {
          color: var(--color-primary);
          font-weight: 600;
        }

        .empty-state {
          padding: 1.2rem;
          text-align: center;
        }

        .detail-empty {
          min-height: 260px;
          display: grid;
          place-items: center;
          border: 1px dashed var(--color-border);
          background: rgba(255, 255, 255, 0.7);
          border-radius: 16px;
        }

        @media (max-width: 1024px) {
          .hero,
          .clusters-layout {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
