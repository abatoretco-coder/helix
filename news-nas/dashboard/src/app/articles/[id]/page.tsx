"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Article } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";

export default function ArticleDetailPage() {
  const params = useParams();
  const articleId = parseInt(params.id as string);

  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getArticle(articleId);
        setArticle(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load article");
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [articleId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!article) return <div className="not-found">Article not found</div>;

  const pubDate = article.published_at ? new Date(article.published_at) : null;

  return (
    <div className="article-detail">
      <div className="article-header">
        <h1>{article.title || "Untitled"}</h1>

        <div className="article-meta">
          {article.author && <span className="author">By {article.author}</span>}
          {pubDate && (
            <span className="date">
              {formatDistanceToNow(pubDate, { addSuffix: true, locale: fr })}
            </span>
          )}
          {article.language && <span className="badge">{article.language.toUpperCase()}</span>}
          {article.ai?.category && <span className="badge">{article.ai.category}</span>}
        </div>

        {article.ai?.final_score && (
          <div className="score-bar">
            <div className="score-label">Relevance Score</div>
            <div className="score-fill" style={{ width: `${article.ai.final_score * 100}%` }}>
              {(article.ai.final_score * 100).toFixed(0)}%
            </div>
          </div>
        )}
      </div>

      <div className="article-content">
        {article.description && (
          <div className="description">
            <p>{article.description}</p>
          </div>
        )}

        {article.ai?.summary_short && (
          <div className="summary">
            <h2>Quick Summary</h2>
            <div className="summary-text">{article.ai.summary_short}</div>
          </div>
        )}

        {article.ai?.summary_long && (
          <div className="detailed-summary">
            <h2>Detailed Summary</h2>
            <div className="summary-text">{article.ai.summary_long}</div>
          </div>
        )}

        {article.ai?.topics && article.ai.topics.length > 0 && (
          <div className="topics">
            <h2>Topics</h2>
            <div className="topics-list">
              {article.ai.topics.map((topic, i) => (
                <span key={i} className="topic-badge">
                  {topic}
                </span>
              ))}
            </div>
          </div>
        )}

        {article.word_count && (
          <div className="article-stats">
            <h2>Stats</h2>
            <p>{article.word_count} words</p>
            <p>Quality Score: {article.quality_score?.toFixed(2) || "N/A"}</p>
          </div>
        )}
      </div>

      <div className="article-actions">
        <a href={article.url} target="_blank" rel="noopener noreferrer" className="btn-primary">
          Read Full Article →
        </a>
      </div>

      <style jsx>{`
        .article-detail {
          max-width: 800px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .article-header {
          margin-bottom: 2rem;
          padding-bottom: 2rem;
          border-bottom: 2px solid #eee;
        }

        h1 {
          margin: 0 0 1rem;
          font-size: 2rem;
          color: #333;
          line-height: 1.2;
        }

        .article-meta {
          display: flex;
          gap: 1rem;
          flex-wrap: wrap;
          font-size: 0.9rem;
          color: #666;
          margin-bottom: 1rem;
        }

        .author {
          font-weight: 600;
        }

        .date {
          color: #999;
        }

        .badge {
          background: #f0f0f0;
          color: #333;
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          font-weight: 600;
          font-size: 0.85rem;
        }

        .score-bar {
          margin-top: 1rem;
          padding: 1rem;
          background: #f5f5f5;
          border-radius: 8px;
        }

        .score-label {
          font-size: 0.9rem;
          color: #666;
          margin-bottom: 0.5rem;
        }

        .score-fill {
          background: linear-gradient(90deg, #ff6b6b 0%, #ffd93d 50%, #6bcf7f 100%);
          color: white;
          padding: 0.5rem;
          border-radius: 4px;
          font-weight: 600;
          text-align: right;
          min-height: 30px;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          padding-right: 0.75rem;
        }

        .article-content {
          margin-bottom: 2rem;
          line-height: 1.8;
        }

        .description {
          background: #f9f9f9;
          padding: 1.5rem;
          border-left: 4px solid #0066cc;
          border-radius: 4px;
          margin-bottom: 2rem;
          font-size: 1.05rem;
        }

        .description p {
          margin: 0;
        }

        .summary,
        .detailed-summary {
          margin-bottom: 2rem;
        }

        .summary h2,
        .detailed-summary h2 {
          font-size: 1.3rem;
          margin: 0 0 0.75rem;
          color: #333;
        }

        .summary-text {
          background: #f0f0f0;
          padding: 1rem;
          border-radius: 4px;
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .topics {
          margin-bottom: 2rem;
        }

        .topics h2 {
          font-size: 1.1rem;
          margin: 0 0 0.75rem;
          color: #333;
        }

        .topics-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .topic-badge {
          background: #e6f2ff;
          color: #0066cc;
          padding: 0.35rem 0.75rem;
          border-radius: 20px;
          font-size: 0.9rem;
          font-weight: 500;
        }

        .article-stats {
          background: #f9f9f9;
          padding: 1rem;
          border-radius: 4px;
          margin-bottom: 2rem;
        }

        .article-stats h2 {
          font-size: 1rem;
          margin: 0 0 0.5rem;
        }

        .article-stats p {
          margin: 0.25rem 0;
          color: #666;
        }

        .article-actions {
          display: flex;
          gap: 1rem;
          margin-top: 2rem;
        }

        .btn-primary {
          background: #0066cc;
          color: white;
          padding: 0.75rem 1.5rem;
          border-radius: 4px;
          text-decoration: none;
          font-weight: 600;
          display: inline-block;
          transition: background 0.2s;
        }

        .btn-primary:hover {
          background: #0052a3;
        }

        .not-found {
          text-align: center;
          padding: 2rem;
          color: #999;
          font-size: 1.1rem;
        }
      `}</style>
    </div>
  );
}
