"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Cluster } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function ClustersPage() {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getClusters(50);
        setClusters(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load clusters");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const handleSelectCluster = async (id: number) => {
    try {
      const data = await api.getCluster(id);
      setSelectedCluster(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cluster");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="clusters-page">
      <h1>🎯 Event Clusters</h1>
      <p className="subtitle">Same stories from different sources</p>

      {error && <ErrorMessage error={error} />}

      <div className="clusters-layout">
        <div className="clusters-list">
          {clusters.length === 0 ? (
            <p>No clusters yet. Articles need to be processed first.</p>
          ) : (
            clusters.map((cluster) => (
              <div
                key={cluster.id}
                className={`cluster-item ${selectedCluster?.id === cluster.id ? "active" : ""}`}
                onClick={() => handleSelectCluster(cluster.id)}
              >
                <h3>{cluster.main_title || `Event #${cluster.id}`}</h3>
                <p className="cluster-count">{cluster.article_count} articles</p>
                {cluster.importance_score && (
                  <div className="cluster-score">
                    Importance: {(cluster.importance_score * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {selectedCluster && (
          <div className="cluster-detail">
            <h2>{selectedCluster.main_title || "Cluster"}</h2>
            {selectedCluster.main_summary && (
              <div className="cluster-summary">
                <h3>Summary</h3>
                <p>{selectedCluster.main_summary}</p>
              </div>
            )}

            {selectedCluster.articles && selectedCluster.articles.length > 0 && (
              <div className="cluster-articles">
                <h3>Articles in this cluster</h3>
                <div className="articles-in-cluster">
                  {selectedCluster.articles.map((article: any) => (
                    <div key={article.id} className="cluster-article-item">
                      <a href={article.url} target="_blank" rel="noopener noreferrer">
                        {article.title}
                      </a>
                      {article.source && <span className="source">{article.source}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .clusters-page {
          max-width: 1400px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        h1 {
          margin: 0 0 0.5rem;
          font-size: 2rem;
          color: #333;
        }

        .subtitle {
          color: #666;
          margin-bottom: 2rem;
        }

        .clusters-layout {
          display: grid;
          grid-template-columns: 350px 1fr;
          gap: 2rem;
        }

        .clusters-list {
          border: 1px solid #eee;
          border-radius: 8px;
          overflow-y: auto;
          max-height: 800px;
          background: white;
        }

        .cluster-item {
          padding: 1rem;
          border-bottom: 1px solid #eee;
          cursor: pointer;
          transition: all 0.2s;
        }

        .cluster-item:hover {
          background: #f9f9f9;
        }

        .cluster-item.active {
          background: #e6f2ff;
          border-left: 3px solid #0066cc;
          padding-left: calc(1rem - 3px);
        }

        .cluster-item h3 {
          margin: 0 0 0.5rem;
          font-size: 1rem;
          color: #333;
          line-height: 1.3;
        }

        .cluster-count {
          margin: 0 0 0.5rem;
          color: #666;
          font-size: 0.9rem;
        }

        .cluster-score {
          font-size: 0.85rem;
          color: #0066cc;
          font-weight: 600;
        }

        .cluster-detail {
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
        }

        .cluster-detail h2 {
          margin: 0 0 1rem;
          font-size: 1.5rem;
          color: #333;
        }

        .cluster-summary {
          background: #f9f9f9;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 1.5rem;
        }

        .cluster-summary h3 {
          margin: 0 0 0.5rem;
          font-size: 1rem;
          color: #333;
        }

        .cluster-summary p {
          margin: 0;
          line-height: 1.6;
          color: #555;
        }

        .cluster-articles h3 {
          margin: 0 0 1rem;
          font-size: 1.1rem;
          color: #333;
        }

        .articles-in-cluster {
          display: grid;
          gap: 0.75rem;
        }

        .cluster-article-item {
          padding: 0.75rem;
          border: 1px solid #eee;
          border-radius: 4px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          background: white;
        }

        .cluster-article-item a {
          color: #0066cc;
          text-decoration: none;
          flex: 1;
          font-weight: 500;
        }

        .cluster-article-item a:hover {
          text-decoration: underline;
        }

        .source {
          background: #f0f0f0;
          color: #666;
          padding: 0.25rem 0.5rem;
          border-radius: 3px;
          font-size: 0.8rem;
          white-space: nowrap;
          margin-left: 0.5rem;
        }

        @media (max-width: 1024px) {
          .clusters-layout {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
