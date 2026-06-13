import {
  Article,
  Briefing,
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
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (API_TOKEN) {
    headers["X-API-Token"] = API_TOKEN;
  }

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

  getDeadQueue: (queue: string, limit = 100) =>
    fetchAPI<DeadQueueDetail>(`/v1/queues/dead/${queue}?limit=${limit}`),

  retryDeadQueue: (queue: string, limit = 100) =>
    fetchAPI<{ queue: string; retried: number }>(`/v1/queues/dead/${queue}/retry?limit=${limit}`, { method: "POST" }),

  purgeDeadQueue: (queue: string) =>
    fetchAPI<{ queue: string; purged: number }>(`/v1/queues/dead/${queue}`, { method: "DELETE" }),

  getOpsSummary: () =>
    fetchAPI<OpsSummary>(`/v1/ops/summary`),

  // Health
  health: () =>
    fetchAPI<any>(`/health`),
};
