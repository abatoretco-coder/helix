import {
  Article,
  Briefing,
  Capabilities,
  Cluster,
  DeadQueueDetail,
  DeadQueueOverview,
  OpsSummary,
  PipelineErrorsResponse,
  PipelineQueuesResponse,
  PipelineStatus,
  Source,
  SourceHealthResponse,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_HELIX_API_TOKEN;

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(API_TOKEN ? { "X-API-Token": API_TOKEN } : {}),
    ...((options?.headers as Record<string, string>) || {}),
  };

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
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

  getClusterTimeline: (id: number) =>
    fetchAPI<{ cluster_id: number; count: number; items: any[] }>(`/v1/clusters/${id}/timeline`),

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

  getSourceHealth: () =>
    fetchAPI<SourceHealthResponse>(`/v1/sources/health`),

  enableSource: (id: number) =>
    fetchAPI<Source>(`/v1/sources/${id}/enable`, { method: "POST" }),

  disableSource: (id: number) =>
    fetchAPI<Source>(`/v1/sources/${id}/disable`, { method: "POST" }),

  refreshSource: (id: number) =>
    fetchAPI<Source>(`/v1/sources/${id}/refresh`, { method: "POST" }),

  resetSourceErrors: (id: number) =>
    fetchAPI<Source>(`/v1/sources/${id}/reset-errors`, { method: "POST" }),

  // Pipeline
  getPipelineStatus: () =>
    fetchAPI<PipelineStatus>(`/v1/pipeline/status`),

  getPipelineQueues: () =>
    fetchAPI<PipelineQueuesResponse>(`/v1/pipeline/queues`),

  getPipelineErrors: () =>
    fetchAPI<PipelineErrorsResponse>(`/v1/pipeline/errors`),

  getDeadQueues: () =>
    fetchAPI<DeadQueueOverview>(`/v1/queues/dead`),

  getDeadQueueItems: (queue: string, limit = 100) =>
    fetchAPI<DeadQueueDetail>(`/v1/queues/dead/${queue}?limit=${limit}`),

  retryDeadQueue: (queue: string, limit = 100) =>
    fetchAPI<{ queue: string; retried: number }>(`/v1/queues/dead/${queue}/retry?limit=${limit}`, { method: "POST" }),

  purgeDeadQueue: (queue: string) =>
    fetchAPI<{ queue: string; purged: number }>(`/v1/queues/dead/${queue}/purge`, { method: "POST" }),

  getOpsSummary: () =>
    fetchAPI<OpsSummary>(`/v1/ops/summary`),

  getCapabilities: () =>
    fetchAPI<Capabilities>(`/v1/capabilities`),

  getInbox: (params?: { limit?: number; category?: string; min_score?: number; hide_read?: boolean; mode?: string }) => {
    const q = new URLSearchParams();
    if (params?.limit != null) q.set("limit", String(params.limit));
    if (params?.category) q.set("category", params.category);
    if (params?.min_score != null) q.set("min_score", String(params.min_score));
    if (params?.hide_read != null) q.set("hide_read", String(params.hide_read));
    if (params?.mode) q.set("mode", params.mode);
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return fetchAPI<{ mode: string; count: number; items: any[] }>(`/v1/inbox${suffix}`);
  },

  getWatchlist: () =>
    fetchAPI<{ count: number; entities: any[] }>(`/v1/watchlist`),

  getWatchlistMatches: (limit = 50) =>
    fetchAPI<{ count: number; items: any[] }>(`/v1/watchlist/matches?limit=${limit}`),

  getProjects: () =>
    fetchAPI<{ count: number; items: any[] }>(`/v1/projects`),

  getProjectArticles: (slug: string, limit = 50) =>
    fetchAPI<{ project: any; count: number; items: any[] }>(`/v1/projects/${encodeURIComponent(slug)}/articles?limit=${limit}`),

  // Health
  health: () =>
    fetchAPI<any>(`/health`),
};
