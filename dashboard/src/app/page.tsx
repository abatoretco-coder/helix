"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Article, Source, Briefing } from "@/types";
import { ArticleCard, LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function Dashboard() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [articlesData, sourcesData] = await Promise.all([
          api.getArticles(10),
          api.getSources(),
        ]);
        setArticles(articlesData);
        setSources(sourcesData);

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

  if (loading) return <LoadingSpinner />;

  const enabledSources = sources.filter((s) => s.enabled).length;
  const topArticles = articles.slice(0, 5);

  return (
    <div className="dashboard-container">
      <h1>📰 News NAS Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>{sources.length}</h3>
          <p>Active Sources</p>
          <small>{enabledSources} enabled</small>
        </div>
        <div className="stat-card">
          <h3>{articles.length}</h3>
          <p>Recent Articles</p>
        </div>
        {briefing && (
          <div className="stat-card">
            <h3>📋</h3>
            <p>Daily Briefing</p>
            <small>Updated today</small>
          </div>
        )}
      </div>

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
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        h1 {
          margin-bottom: 2rem;
          color: #333;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .stat-card {
          background: #f5f5f5;
          border-radius: 8px;
          padding: 1.5rem;
          text-align: center;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .stat-card h3 {
          font-size: 2rem;
          margin: 0;
          color: #0066cc;
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
          background: #fafafa;
          border-left: 4px solid #0066cc;
          padding: 1.5rem;
          margin-bottom: 2rem;
          border-radius: 4px;
        }

        .briefing-content {
          background: white;
          padding: 1rem;
          border-radius: 4px;
          line-height: 1.6;
          max-height: 300px;
          overflow-y: auto;
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
