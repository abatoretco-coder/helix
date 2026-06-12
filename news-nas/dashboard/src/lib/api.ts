import { Article, Cluster, Briefing, Source } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error: ${res.status} ${text}`);
  }

  return res.json();
}

export const api = {
  // Articles
  getArticles: (limit = 50, offset = 0) =>
    fetchAPI<Article[]>(`/articles?limit=${limit}&offset=${offset}`),

  getArticle: (id: number) =>
    fetchAPI<Article>(`/articles/${id}`),

  // Search
  search: (q: string, limit = 20) =>
    fetchAPI<any>(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  // Clusters
  getClusters: (limit = 30, offset = 0) =>
    fetchAPI<Cluster[]>(`/clusters?limit=${limit}&offset=${offset}`),

  getCluster: (id: number) =>
    fetchAPI<any>(`/clusters/${id}`),

  // Briefings
  getDailyBriefing: () =>
    fetchAPI<Briefing>(`/briefings/daily`),

  generateBriefing: (period = "daily") =>
    fetchAPI<any>(`/briefings/generate`, { method: "POST", body: JSON.stringify({ period }) }),

  // Jarvis
  jarvisQuery: (query: string) =>
    fetchAPI<any>(`/jarvis/query`, {
      method: "POST",
      body: JSON.stringify({ query, limit: 10 }),
    }),

  // Sources
  getSources: () =>
    fetchAPI<Source[]>(`/sources`),

  // Health
  health: () =>
    fetchAPI<any>(`/health`),
};
