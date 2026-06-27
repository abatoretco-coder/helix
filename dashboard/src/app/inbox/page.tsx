"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { InboxResponse } from "@/types";

const MODES = ["top", "recent", "long_reads", "watchlist"] as const;

export default function InboxPage() {
  const [mode, setMode] = useState<(typeof MODES)[number]>("top");
  const [hideRead, setHideRead] = useState(false);
  const [data, setData] = useState<InboxResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getInbox({ mode, limit: 60, hide_read: hideRead });
      setData(res);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load inbox");
    } finally {
      setLoading(false);
    }
  }, [hideRead, mode]);

  useEffect(() => {
    load();
  }, [load]);

  const updateState = async (
    articleId: number,
    payload: { is_read?: boolean; is_saved?: boolean; is_hidden?: boolean },
  ) => {
    try {
      setBusyId(articleId);
      await api.setArticleUserState(articleId, payload);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update state");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="page">
      <h1>Inbox</h1>
      <p className="sub">Focused feed with personal read/save/hide state.</p>

      <div className="controls">
        <label>
          Mode
          <select value={mode} onChange={(e) => setMode(e.target.value as (typeof MODES)[number])}>
            {MODES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={hideRead} onChange={(e) => setHideRead(e.target.checked)} />
          Hide read
        </label>
        <button onClick={load} disabled={loading}>{loading ? "Loading..." : "Refresh"}</button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="list">
        {data?.items.map((item) => (
          <article key={item.id} className="card">
            <h3>
              <a href={item.url || "#"} target="_blank" rel="noreferrer">{item.title || "Untitled"}</a>
            </h3>
            <p className="meta">
              {item.source || "Unknown"} · {item.category || "uncategorized"} · score {Number(item.final_score || 0).toFixed(3)}
            </p>
            {item.summary_short && <p>{item.summary_short}</p>}
            {!!item.matched_watchlist?.length && (
              <p className="chips">Matched: {item.matched_watchlist.join(", ")}</p>
            )}
            <div className="actions">
              <button
                onClick={() => updateState(item.id, { is_read: !item.is_read })}
                disabled={busyId === item.id}
              >
                {item.is_read ? "Mark unread" : "Mark read"}
              </button>
              <button
                onClick={() => updateState(item.id, { is_saved: !item.is_saved })}
                disabled={busyId === item.id}
              >
                {item.is_saved ? "Unsave" : "Save"}
              </button>
              <button
                onClick={() => updateState(item.id, { is_hidden: !item.is_hidden })}
                disabled={busyId === item.id}
              >
                {item.is_hidden ? "Unhide" : "Hide"}
              </button>
            </div>
          </article>
        ))}
      </div>

      {!loading && !data?.items.length && <p>No items for current filters.</p>}

      <style jsx>{`
        .page {
          max-width: 1000px;
          margin: 0 auto;
          padding: 1.5rem 1rem 2rem;
        }
        .sub { color: var(--color-text-secondary); margin-bottom: 1rem; }
        .controls {
          display: flex;
          flex-wrap: wrap;
          gap: 0.8rem;
          align-items: center;
          margin-bottom: 1rem;
        }
        label { display: grid; gap: 0.3rem; font-size: 0.9rem; }
        .check { display: flex; align-items: center; gap: 0.5rem; margin-top: 1rem; }
        select, button { padding: 0.45rem 0.65rem; border-radius: 8px; border: 1px solid var(--color-border); }
        .error { color: var(--color-error); margin-bottom: 1rem; }
        .list { display: grid; gap: 0.9rem; }
        .card {
          border: 1px solid var(--color-border);
          border-radius: 12px;
          padding: 0.9rem;
          background: rgba(255,255,255,0.9);
        }
        .card h3 { margin: 0 0 0.4rem; }
        .meta { color: var(--color-text-secondary); font-size: 0.9rem; margin: 0 0 0.5rem; }
        .chips { color: #1d4ed8; font-size: 0.85rem; margin: 0.35rem 0; }
        .actions { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.6rem; }
      `}</style>
    </div>
  );
}
