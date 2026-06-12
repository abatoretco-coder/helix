"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Source } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "enabled" | "disabled">("all");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getSources();
        setSources(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load sources");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const filteredSources = sources.filter((s) => {
    if (filter === "enabled") return s.enabled;
    if (filter === "disabled") return !s.enabled;
    return true;
  });

  const stats = {
    total: sources.length,
    enabled: sources.filter((s) => s.enabled).length,
    disabled: sources.filter((s) => !s.enabled).length,
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="sources-page">
      <h1>📡 News Sources</h1>

      {error && <ErrorMessage error={error} />}

      <div className="stats-bar">
        <div className="stat">
          <strong>{stats.total}</strong> total
        </div>
        <div className="stat enabled">
          <strong>{stats.enabled}</strong> enabled
        </div>
        <div className="stat disabled">
          <strong>{stats.disabled}</strong> disabled
        </div>
      </div>

      <div className="filter-buttons">
        {(["all", "enabled", "disabled"] as const).map((f) => (
          <button
            key={f}
            className={filter === f ? "active" : ""}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="sources-grid">
        {filteredSources.length === 0 ? (
          <p className="no-sources">No sources found</p>
        ) : (
          filteredSources.map((source) => (
            <div
              key={source.id}
              className={`source-card ${source.enabled ? "enabled" : "disabled"}`}
            >
              <div className="source-header">
                <h3>{source.name}</h3>
                <span className={`status ${source.enabled ? "active" : "inactive"}`}>
                  {source.enabled ? "Active" : "Inactive"}
                </span>
              </div>

              <div className="source-info">
                <div className="info-row">
                  <span className="label">Type:</span>
                  <span className="value">{source.source_type}</span>
                </div>

                {source.category && (
                  <div className="info-row">
                    <span className="label">Category:</span>
                    <span className="value">{source.category}</span>
                  </div>
                )}

                {source.language && (
                  <div className="info-row">
                    <span className="label">Language:</span>
                    <span className="value">{source.language.toUpperCase()}</span>
                  </div>
                )}

                <div className="info-row">
                  <span className="label">Priority:</span>
                  <span className={`priority priority-${source.priority}`}>
                    {source.priority}
                  </span>
                </div>

                {source.error_count > 0 && (
                  <div className="info-row error">
                    <span className="label">Errors:</span>
                    <span className="value">{source.error_count}</span>
                  </div>
                )}
              </div>

              {source.url && (
                <a href={source.url} target="_blank" rel="noopener noreferrer" className="source-url">
                  Visit Source →
                </a>
              )}
            </div>
          ))
        )}
      </div>

      <style jsx>{`
        .sources-page {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        h1 {
          margin: 0 0 2rem;
          font-size: 2rem;
          color: #333;
        }

        .stats-bar {
          display: flex;
          gap: 2rem;
          margin-bottom: 2rem;
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 8px;
          flex-wrap: wrap;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }

        .stat strong {
          font-size: 1.5rem;
          color: #333;
        }

        .stat.enabled strong {
          color: #2db745;
        }

        .stat.disabled strong {
          color: #dc2626;
        }

        .filter-buttons {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 2rem;
        }

        button {
          background: white;
          border: 1px solid #ddd;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.2s;
        }

        button:hover {
          border-color: #0066cc;
          color: #0066cc;
        }

        button.active {
          background: #0066cc;
          color: white;
          border-color: #0066cc;
        }

        .sources-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .source-card {
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
          transition: all 0.2s;
        }

        .source-card:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          border-color: #0066cc;
        }

        .source-card.disabled {
          opacity: 0.7;
          background: #fafafa;
        }

        .source-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 1rem;
          margin-bottom: 1rem;
          padding-bottom: 1rem;
          border-bottom: 1px solid #eee;
        }

        .source-header h3 {
          margin: 0;
          font-size: 1.1rem;
          color: #333;
          flex: 1;
        }

        .status {
          padding: 0.25rem 0.75rem;
          border-radius: 20px;
          font-size: 0.8rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .status.active {
          background: #d1fae5;
          color: #065f46;
        }

        .status.inactive {
          background: #fee2e2;
          color: #7f1d1d;
        }

        .source-info {
          margin-bottom: 1rem;
        }

        .info-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 0;
          font-size: 0.9rem;
        }

        .label {
          color: #666;
          font-weight: 500;
        }

        .value {
          color: #333;
          font-weight: 600;
        }

        .priority {
          background: #f0f0f0;
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          font-weight: 600;
        }

        .priority-1 {
          background: #fecaca;
          color: #7f1d1d;
        }

        .priority-2 {
          background: #fde047;
          color: #713f12;
        }

        .priority-3 {
          background: #a7f3d0;
          color: #065f46;
        }

        .priority-4 {
          background: #dbeafe;
          color: #0c2d6b;
        }

        .info-row.error {
          color: #dc2626;
        }

        .source-url {
          display: inline-block;
          color: #0066cc;
          text-decoration: none;
          font-weight: 600;
          margin-top: 0.5rem;
          padding-top: 0.5rem;
          border-top: 1px solid #eee;
          width: 100%;
          text-align: center;
        }

        .source-url:hover {
          text-decoration: underline;
        }

        .no-sources {
          text-align: center;
          padding: 2rem;
          color: #999;
          grid-column: 1 / -1;
        }
      `}</style>
    </div>
  );
}
