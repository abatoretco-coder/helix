"use client";

import { Article } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import Link from "next/link";

export function ArticleCard({ article }: { article: Article }) {
  const pubDate = article.published_at
    ? new Date(article.published_at)
    : null;

  return (
    <div className="article-card">
      <div className="article-header">
        <Link href={`/articles/${article.id}`}>
          <h3 className="article-title">{article.title || "Untitled"}</h3>
        </Link>
        {article.ai?.final_score && (
          <span className="score-badge">
            {(article.ai.final_score * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <p className="article-description">{article.description || article.ai?.summary_short}</p>

      <div className="article-meta">
        {article.language && <span className="badge">{article.language.toUpperCase()}</span>}
        {article.ai?.category && <span className="badge category">{article.ai.category}</span>}
        {pubDate && (
          <span className="date">
            {formatDistanceToNow(pubDate, { addSuffix: true, locale: fr })}
          </span>
        )}
      </div>

      <div className="article-content-preview">
        {article.word_count && <small>{article.word_count} words</small>}
      </div>
    </div>
  );
}

export function LoadingSpinner() {
  return <div className="spinner">Loading...</div>;
}

export function ErrorMessage({ error }: { error: string }) {
  return <div className="error-message">{error}</div>;
}

export function SearchBox({
  onSearch,
  loading = false,
}: {
  onSearch: (q: string) => void;
  loading?: boolean;
}) {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem("q") as HTMLInputElement;
    if (input?.value) {
      onSearch(input.value);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="search-box">
      <input
        type="text"
        name="q"
        placeholder="Search articles..."
        disabled={loading}
        autoComplete="off"
      />
      <button type="submit" disabled={loading}>
        {loading ? "Searching..." : "Search"}
      </button>
    </form>
  );
}
