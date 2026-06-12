"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Briefing } from "@/types";
import { LoadingSpinner, ErrorMessage } from "@/components/ArticleCard";

export default function BriefingsPage() {
  const [briefings, setBriefings] = useState<Briefing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getDailyBriefing();
        if (data) setBriefings([data]);
      } catch {
        // Might not exist yet
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await api.generateBriefing("daily");
      alert("Briefing queued for generation");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="briefings-page">
      <h1>📋 Daily Briefings</h1>

      <button onClick={handleGenerate} disabled={generating} className="generate-btn">
        {generating ? "Generating..." : "Generate Today's Briefing"}
      </button>

      {error && <ErrorMessage error={error} />}

      {briefings.length > 0 ? (
        <div className="briefings-list">
          {briefings.map((briefing) => (
            <div key={briefing.id} className="briefing-card">
              <h2>{new Date(briefing.period_date).toLocaleDateString()}</h2>
              {briefing.content ? (
                <div className="briefing-body">{briefing.content}</div>
              ) : (
                <p className="placeholder">Briefing generating or not available</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="no-briefings">
          {loading ? (
            <LoadingSpinner />
          ) : (
            <p>No briefings yet. Click "Generate" to create one.</p>
          )}
        </div>
      )}

      <style jsx>{`
        .briefings-page {
          max-width: 900px;
          margin: 0 auto;
          padding: 2rem;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        h1 {
          margin-bottom: 1.5rem;
        }

        .generate-btn {
          background: #0066cc;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          margin-bottom: 2rem;
        }

        .generate-btn:hover:not(:disabled) {
          background: #0052a3;
        }

        .generate-btn:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        .briefings-list {
          display: grid;
          gap: 1rem;
        }

        .briefing-card {
          border: 1px solid #eee;
          border-left: 4px solid #0066cc;
          border-radius: 8px;
          padding: 1.5rem;
          background: white;
        }

        .briefing-card h2 {
          margin: 0 0 1rem;
          color: #333;
        }

        .briefing-body {
          line-height: 1.6;
          color: #555;
          white-space: pre-wrap;
          word-break: break-word;
        }

        .placeholder {
          color: #999;
          font-style: italic;
        }

        .no-briefings {
          text-align: center;
          padding: 2rem;
          color: #666;
        }
      `}</style>
    </div>
  );
}
