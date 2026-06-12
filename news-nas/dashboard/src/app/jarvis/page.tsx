"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { SearchBox, LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function JarvisPage() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (q: string) => {
    if (!q.trim()) return;

    setQuery(q);
    setResponse(null);
    setError("");
    setLoading(true);

    try {
      const data = await api.jarvisQuery(q);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="jarvis-page">
      <h1>🤖 Jarvis - Ask Anything</h1>
      <p className="subtitle">Semantic search with LLM-powered responses</p>

      <SearchBox onSearch={handleSearch} loading={loading} />

      {error && <ErrorMessage error={error} />}

      {response && (
        <div className="response-container">
          <div className="response-answer">
            <h2>Answer</h2>
            <div className="answer-text">{response.answer || response.response || "No answer generated"}</div>
          </div>

          {response.sources && response.sources.length > 0 && (
            <div className="response-sources">
              <h2>Sources</h2>
              <div className="sources-list">
                {response.sources.map((source: any, i: number) => (
                  <div key={i} className="source-item">
                    <h3>
                      <a href={source.url} target="_blank" rel="noopener noreferrer">
                        {source.title}
                      </a>
                    </h3>
                    <p className="source-excerpt">{source.excerpt || source.description}</p>
                    <div className="source-meta">
                      {source.similarity && (
                        <span className="similarity">
                          Match: {(source.similarity * 100).toFixed(0)}%
                        </span>
                      )}
                      {source.source && <span className="badge">{source.source}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && query && !response && !error && (
        <div className="no-results">Processing your question...</div>
      )}

      {loading && <LoadingSpinner />}

      <style jsx>{`
        .jarvis-page {
          max-width: 900px;
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

        .search-box {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 2rem;
        }

        input {
          flex: 1;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
        }

        button {
          background: #0066cc;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
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

        .response-container {
          margin-top: 2rem;
          display: grid;
          gap: 2rem;
        }

        .response-answer {
          background: linear-gradient(135deg, #e6f2ff 0%, #f0f8ff 100%);
          border: 1px solid #0066cc;
          border-radius: 8px;
          padding: 1.5rem;
        }

        .response-answer h2 {
          margin: 0 0 1rem;
          font-size: 1.2rem;
          color: #0066cc;
        }

        .answer-text {
          font-size: 1rem;
          line-height: 1.6;
          color: #333;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .response-sources {
          margin-top: 2rem;
        }

        .response-sources h2 {
          margin: 0 0 1rem;
          font-size: 1.1rem;
          color: #333;
        }

        .sources-list {
          display: grid;
          gap: 1rem;
        }

        .source-item {
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1rem;
          background: white;
        }

        .source-item h3 {
          margin: 0 0 0.5rem;
          font-size: 1rem;
        }

        .source-item a {
          color: #0066cc;
          text-decoration: none;
        }

        .source-item a:hover {
          text-decoration: underline;
        }

        .source-excerpt {
          margin: 0.5rem 0;
          color: #666;
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .source-meta {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
          margin-top: 0.5rem;
          font-size: 0.85rem;
        }

        .similarity {
          background: #0066cc;
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-weight: 600;
        }

        .badge {
          background: #f0f0f0;
          color: #333;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-weight: 600;
        }

        .no-results {
          text-align: center;
          padding: 2rem;
          color: #999;
          font-size: 1.1rem;
        }
      `}</style>
    </div>
  );
}
