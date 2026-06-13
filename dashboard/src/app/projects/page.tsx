"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ProjectItem } from "@/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadProjects = async () => {
    try {
      setLoading(true);
      const data = await api.getProjects();
      setProjects(data.items || []);
      if (!selected && data.items?.length) {
        setSelected(data.items[0].slug);
      }
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const loadProjectArticles = async (slug: string) => {
    try {
      const data = await api.getProjectArticles(slug, 40);
      setArticles(data.items || []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project articles");
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selected) {
      loadProjectArticles(selected);
    }
  }, [selected]);

  return (
    <div className="page">
      <h1>Research Projects</h1>
      <p className="sub">DB-backed project definitions and linked article stream.</p>

      <div className="controls">
        <button onClick={loadProjects} disabled={loading}>{loading ? "Loading..." : "Refresh"}</button>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {projects.map((project) => (
            <option key={project.slug} value={project.slug}>{project.name}</option>
          ))}
        </select>
      </div>

      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h2>Projects ({projects.length})</h2>
        <div className="list">
          {projects.map((project) => (
            <article key={project.slug} className="card">
              <h3>{project.name}</h3>
              <p>{project.description || "No description"}</p>
              <p className="meta">slug: {project.slug}</p>
              <p className="meta">keywords: {(project.keywords || []).join(", ") || "none"}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Matched Articles ({articles.length})</h2>
        <div className="list">
          {articles.map((item) => (
            <article key={item.id} className="card">
              <h3><a href={item.url} target="_blank" rel="noreferrer">{item.title}</a></h3>
              <p className="meta">{item.source || "Unknown"} · {item.category || "uncategorized"}</p>
              <p>{item.summary_short || "No summary"}</p>
              <p className="meta">matched: {(item.matched_keywords || []).join(", ")}</p>
            </article>
          ))}
        </div>
      </section>

      <style jsx>{`
        .page { max-width: 1000px; margin: 0 auto; padding: 1.5rem 1rem 2rem; }
        .sub { color: var(--color-text-secondary); margin-bottom: 1rem; }
        .controls { display: flex; gap: 0.8rem; align-items: center; }
        button, select { padding: 0.45rem 0.65rem; border-radius: 8px; border: 1px solid var(--color-border); }
        .error { color: var(--color-error); margin: 0.8rem 0; }
        .panel { margin-top: 1rem; border: 1px solid var(--color-border); border-radius: 12px; padding: 1rem; background: rgba(255,255,255,0.9); }
        .list { display: grid; gap: 0.8rem; margin-top: 0.6rem; }
        .card { border: 1px solid var(--color-border); border-radius: 10px; padding: 0.8rem; background: var(--color-surface); }
        .meta { color: var(--color-text-secondary); font-size: 0.9rem; }
      `}</style>
    </div>
  );
}
