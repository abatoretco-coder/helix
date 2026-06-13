"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { WatchlistEntity } from "@/types";

export default function WatchlistPage() {
  const [entities, setEntities] = useState<WatchlistEntity[]>([]);
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    try {
      setLoading(true);
      const [watchlist, recentMatches] = await Promise.all([
        api.getWatchlist(),
        api.getWatchlistMatches(40),
      ]);
      setEntities(watchlist.entities || []);
      setMatches(recentMatches.items || []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <h1>Watchlist</h1>
      <p className="sub">DB-backed entities and latest matched articles.</p>

      <button onClick={load} disabled={loading}>{loading ? "Loading..." : "Refresh"}</button>
      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Entities ({entities.length})</h2>
        <div className="chips">
          {entities.map((entity, idx) => (
            <span key={`${entity.name}-${idx}`} className="chip">
              {entity.name} · p{entity.priority ?? 2}
            </span>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Latest Matches ({matches.length})</h2>
        <div className="list">
          {matches.map((item) => (
            <article key={item.id} className="card">
              <h3><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></h3>
              <p className="meta">{item.source || "Unknown"} · score {Number(item.final_score || 0).toFixed(3)}</p>
              <p>{item.summary_short || "No summary"}</p>
              <p className="match">Matched: {(item.matched_entities || []).join(", ")}</p>
            </article>
          ))}
        </div>
      </section>

      <style jsx>{`
        .page { max-width: 1000px; margin: 0 auto; padding: 1.5rem 1rem 2rem; }
        .sub { color: var(--color-text-secondary); margin-bottom: 1rem; }
        .error { color: var(--color-error); margin: 0.8rem 0; }
        .panel { margin-top: 1rem; border: 1px solid var(--color-border); border-radius: 12px; padding: 1rem; background: rgba(255,255,255,0.9); }
        .chips { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.6rem; }
        .chip { border: 1px solid var(--color-border); border-radius: 999px; padding: 0.2rem 0.6rem; font-size: 0.86rem; }
        .list { display: grid; gap: 0.8rem; margin-top: 0.7rem; }
        .card { border: 1px solid var(--color-border); border-radius: 10px; padding: 0.8rem; background: var(--color-surface); }
        .meta { color: var(--color-text-secondary); font-size: 0.9rem; }
        .match { color: #1d4ed8; font-size: 0.88rem; margin-top: 0.4rem; }
      `}</style>
    </div>
  );
}
