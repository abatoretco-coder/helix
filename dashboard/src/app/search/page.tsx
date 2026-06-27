"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { SearchBox, LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQ);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"keyword" | "semantic">("keyword");

  const handleSearch = useCallback(async (q: string, searchMode = mode) => {
    if (!q.trim()) return;

    setQuery(q);
    setLoading(true);
    setError("");

    try {
      const data = searchMode === "semantic"
        ? await api.semanticSearch(q, 50)
        : await api.search(q, 50);
      setResults(data.hits || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    if (initialQ) {
      handleSearch(initialQ);
    }
  }, [handleSearch, initialQ]);

  return (
    <div className="search-page">
      <h1>🔍 Search</h1>

      <div className="search-controls">
        <SearchBox onSearch={handleSearch} loading={loading} />
        <div className="mode-toggle" aria-label="Search mode">
          {(["keyword", "semantic"] as const).map((item) => (
            <button
              key={item}
              type="button"
              className={mode === item ? "active" : ""}
              onClick={() => {
                setMode(item);
                if (query) {
                  handleSearch(query, item);
                }
              }}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorMessage error={error} />}

      {results.length > 0 && (
        <div className="results">
          <p className="result-count">
            Found {results.length} results for &quot;<strong>{query}</strong>&quot;
          </p>

          <div className="results-list">
            {results.map((result) => (
              <div key={result.id} className="result-item">
                <h3>
                  <a href={result.url} target="_blank" rel="noopener noreferrer">
                    {result.title}
                  </a>
                </h3>
                <p className="result-summary">{result.summary_short || result.description}</p>
                <div className="result-meta">
                  {result.source && <span className="badge">{result.source}</span>}
                  {result.category && <span className="badge">{result.category}</span>}
                  {result.final_score && (
                    <span className="score">{(result.final_score * 100).toFixed(0)}%</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && <LoadingSpinner />}

      {!loading && query && results.length === 0 && !error && (
        <div className="no-results">No articles found for &quot;{query}&quot;</div>
      )}

      <style jsx>{`
        .search-page {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        h1 {
          margin-bottom: 2rem;
        }

        .search-controls {
          display: grid;
          gap: 0.75rem;
          margin-bottom: 2rem;
        }

        .search-box {
          display: flex;
          gap: 0.5rem;
        }

        .mode-toggle {
          display: inline-flex;
          width: fit-content;
          border: 1px solid #ddd;
          border-radius: 8px;
          overflow: hidden;
        }

        .mode-toggle button {
          border: 0;
          border-radius: 0;
          background: #fff;
          color: #333;
          padding: 0.45rem 0.75rem;
          text-transform: capitalize;
        }

        .mode-toggle button.active {
          background: #0066cc;
          color: #fff;
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

        button:hover {
          background: #0052a3;
        }

        .results {
          margin-top: 2rem;
        }

        .result-count {
          color: #666;
          margin-bottom: 1rem;
        }

        .results-list {
          display: grid;
          gap: 1rem;
        }

        .result-item {
          border: 1px solid #eee;
          border-radius: 8px;
          padding: 1rem;
          transition: all 0.2s;
        }

        .result-item:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          border-color: #0066cc;
        }

        .result-item h3 {
          margin: 0;
          font-size: 1.1rem;
        }

        .result-item a {
          color: #0066cc;
          text-decoration: none;
        }

        .result-item a:hover {
          text-decoration: underline;
        }

        .result-summary {
          margin: 0.5rem 0;
          color: #666;
          font-size: 0.95rem;
          line-height: 1.5;
        }

        .result-meta {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
          margin-top: 0.5rem;
          font-size: 0.85rem;
        }

        .badge {
          background: #f0f0f0;
          color: #333;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-weight: 600;
        }

        .score {
          background: #0066cc;
          color: white;
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

export default function SearchPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <SearchContent />
    </Suspense>
  );
}
