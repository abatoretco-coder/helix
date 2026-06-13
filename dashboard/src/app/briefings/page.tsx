"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Briefing } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function BriefingsPage() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  const loadBriefing = async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const data = await api.getDailyBriefing();
      setBriefing(data);
      setError("");
    } catch {
      setBriefing(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadBriefing();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.generateBriefing("daily");
      await loadBriefing(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const sections = briefing?.content
    ? briefing.content.split(/\n\s*\n/).filter(Boolean)
    : [];

  return (
    <div className="briefings-page">
      <header className="hero">
        <div>
          <p className="eyebrow">Daily briefing</p>
          <h1>Briefings ready to read, refresh, or regenerate.</h1>
          <p className="hero-copy">
            The daily briefing aggregates the most relevant items from the latest pipeline run and keeps a single
            readable summary for the day.
          </p>
        </div>
        <div className="hero-panel">
          <span className="hero-panel-label">Current state</span>
          <strong>{briefing ? new Date(briefing.generated_at).toLocaleString() : "No briefing yet"}</strong>
          <small>
            {briefing
              ? `${sections.length || 1} section${sections.length === 1 ? "" : "s"} · ${briefing.category}`
              : "Generate the first daily briefing from the queue."}
          </small>
          <div className="actions">
            <button onClick={handleGenerate} disabled={generating} className="generate-btn">
              {generating ? "Generating..." : "Generate now"}
            </button>
            <button onClick={() => loadBriefing(true)} disabled={refreshing} className="refresh-btn">
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
      </header>

      {error && <ErrorMessage error={error} />}

      {loading ? (
        <LoadingSpinner />
      ) : briefing ? (
        <div className="briefing-grid">
          <section className="briefing-card">
            <div className="briefing-card-header">
              <div>
                <p className="card-label">Period</p>
                <h2>{new Date(briefing.period_date).toLocaleDateString()}</h2>
              </div>
              <span className="pill">{briefing.period}</span>
            </div>

            <div className="briefing-meta">
              <div>
                <span className="meta-label">Category</span>
                <strong>{briefing.category}</strong>
              </div>
              <div>
                <span className="meta-label">Generated</span>
                <strong>{new Date(briefing.generated_at).toLocaleString()}</strong>
              </div>
            </div>

            {briefing.content ? (
              <div className="briefing-body">
                {sections.map((section, index) => (
                  <p key={index}>{section}</p>
                ))}
              </div>
            ) : (
              <div className="placeholder-box">
                <p className="placeholder-title">Briefing queued</p>
                <p className="placeholder">The briefing job has been created, but content is not available yet.</p>
              </div>
            )}
          </section>

          <aside className="side-panel">
            <div className="side-card">
              <span className="meta-label">What this page does</span>
              <p>
                The briefing page gives you one place to regenerate the day summary and inspect the latest output
                without jumping back to the API.
              </p>
            </div>
            <div className="side-card accent">
              <span className="meta-label">Suggested next step</span>
              <p>Hook this page to a historical briefing list once the backend exposes a list endpoint.</p>
            </div>
          </aside>
        </div>
      ) : (
        <div className="no-briefings">
          <p>No briefing is available yet.</p>
          <button onClick={handleGenerate} disabled={generating} className="generate-btn">
            {generating ? "Generating..." : "Generate the first briefing"}
          </button>
        </div>
      )}

      <style jsx>{`
        .briefings-page {
          max-width: 1200px;
          margin: 0 auto;
          padding: 2rem 1.25rem 3rem;
        }

        .hero {
          display: grid;
          grid-template-columns: 1.5fr 0.5fr;
          gap: 1rem;
          align-items: end;
          margin-bottom: 1.5rem;
        }

        .eyebrow {
          text-transform: uppercase;
          letter-spacing: 0.18em;
          font-size: 0.75rem;
          color: var(--color-text-tertiary);
          margin-bottom: 0.5rem;
        }

        h1 {
          margin: 0;
          color: var(--color-text);
          font-size: clamp(2rem, 4vw, 3.25rem);
          line-height: 1.05;
          max-width: 14ch;
        }

        .hero-copy {
          margin-top: 1rem;
          color: var(--color-text-secondary);
          max-width: 64ch;
        }

        .hero-panel {
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.12), rgba(45, 183, 69, 0.12));
          border: 1px solid rgba(0, 102, 204, 0.12);
          border-radius: 18px;
          padding: 1rem 1.25rem;
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
        }

        .hero-panel-label,
        .card-label,
        .meta-label {
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: var(--color-text-tertiary);
        }

        .actions {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-top: 0.5rem;
        }

        .generate-btn,
        .refresh-btn {
          border: none;
          color: white;
          font-weight: 600;
          padding: 0.75rem 1.1rem;
          border-radius: 12px;
        }

        .generate-btn {
          background: var(--color-primary);
        }

        .refresh-btn {
          background: rgba(255, 255, 255, 0.22);
          border: 1px solid rgba(255, 255, 255, 0.24);
        }

        .generate-btn:hover:not(:disabled) {
          background: var(--color-primary-dark);
        }

        .refresh-btn:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.34);
        }

        .generate-btn:disabled,
        .refresh-btn:disabled {
          opacity: 0.72;
          cursor: not-allowed;
        }

        .briefing-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.8fr);
          gap: 1rem;
          align-items: start;
        }

        .briefing-card {
          border: 1px solid var(--color-border);
          border-radius: 20px;
          padding: 1.5rem;
          background: rgba(255, 255, 255, 0.82);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
        }

        .briefing-card-header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .briefing-card h2 {
          margin: 0;
          color: var(--color-text);
          font-size: 1.4rem;
        }

        .pill {
          border-radius: 999px;
          background: rgba(0, 102, 204, 0.1);
          color: var(--color-primary);
          padding: 0.3rem 0.75rem;
          font-size: 0.8rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .briefing-meta {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 0.75rem;
          margin-bottom: 1rem;
        }

        .briefing-meta strong {
          display: block;
          color: var(--color-text);
          margin-top: 0.2rem;
        }

        .briefing-body {
          display: grid;
          gap: 0.85rem;
          line-height: 1.7;
          color: var(--color-text-secondary);
        }

        .briefing-body p {
          margin: 0;
        }

        .placeholder-box,
        .side-card {
          border: 1px solid var(--color-border);
          border-radius: 16px;
          padding: 1rem;
          background: rgba(249, 250, 251, 0.9);
        }

        .placeholder-title {
          margin-bottom: 0.25rem;
          font-weight: 700;
          color: var(--color-text);
        }

        .placeholder {
          color: var(--color-text-secondary);
          font-style: normal;
        }

        .side-panel {
          display: grid;
          gap: 1rem;
        }

        .side-card p {
          margin-top: 0.4rem;
          color: var(--color-text-secondary);
        }

        .side-card.accent {
          background: linear-gradient(135deg, rgba(0, 102, 204, 0.08), rgba(45, 183, 69, 0.08));
        }

        .no-briefings {
          text-align: center;
          padding: 2rem;
          color: var(--color-text-secondary);
          display: grid;
          gap: 1rem;
          justify-items: center;
        }

        @media (max-width: 900px) {
          .hero,
          .briefing-grid {
            grid-template-columns: 1fr;
          }

          .hero-panel,
          .briefing-card,
          .side-card {
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
}
