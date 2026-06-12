"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Article } from "@/types";
import { ArticleCard, LoadingSpinner, ErrorMessage, SearchBox } from "@/components/ArticleCard";

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);

  const loadArticles = async () => {
    try {
      setLoading(true);
      const data = await api.getArticles(50, offset);
      if (offset === 0) {
        setArticles(data);
      } else {
        setArticles((prev) => [...prev, ...data]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load articles");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArticles();
  }, [offset]);

  return (
    <div className="articles-page">
      <h1>📚 All Articles</h1>

      <div className="controls">
        <p>{articles.length} articles loaded</p>
        <button onClick={() => setOffset((o) => o + 50)} disabled={loading}>
          Load More
        </button>
      </div>

      {error && <ErrorMessage error={error} />}

      <div className="articles-list">
        {articles.map((article) => (
          <ArticleCard key={article.id} article={article} />
        ))}
      </div>

      {loading && <LoadingSpinner />}

      <style jsx>{`
        .articles-page {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        h1 {
          margin-bottom: 2rem;
        }

        .controls {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 4px;
        }

        button {
          background: #0066cc;
          color: white;
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        button:hover:not(:disabled) {
          background: #0052a3;
        }

        button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        .articles-list {
          display: grid;
          gap: 1rem;
        }
      `}</style>
    </div>
  );
}
