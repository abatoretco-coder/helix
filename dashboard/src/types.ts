export interface Source {
  id: number;
  name: string;
  source_type: string;
  url?: string;
  query?: string;
  category: string;
  language: string;
  priority: number;
  enabled: boolean;
  error_count: number;
}

export interface ArticleAI {
  summary_short?: string;
  summary_long?: string;
  category?: string;
  topics?: string[];
  final_score?: number;
  importance_score?: number;
  processed_at?: string;
}

export interface Article {
  id: number;
  url: string;
  title?: string;
  description?: string;
  author?: string;
  language?: string;
  published_at?: string;
  word_count?: number;
  quality_score?: number;
  source_id?: number;
  ai?: ArticleAI;
}

export interface Cluster {
  id: number;
  main_title?: string;
  main_summary?: string;
  topic?: string;
  article_count: number;
  importance_score?: number;
  last_seen_at?: string;
}

export interface Briefing {
  id: number;
  period: string;
  period_date: string;
  category: string;
  content?: string;
  generated_at: string;
}

export interface PipelineStatus {
  generated_at: string;
  sources: {
    total: number;
    enabled: number;
    active: number;
    with_errors: number;
  };
  pipeline: {
    raw_items_total: number;
    raw_items_today: number;
    articles_total: number;
    articles_today: number;
    ai_processed_total: number;
    ai_processed_today: number;
    briefings_total: number;
    briefings_today: number;
    processing_errors_last_24h: number;
    queue_depths: Record<string, number>;
    average_durations_last_24h_ms: Record<string, number>;
    cluster_count: number;
    cluster_links: number;
  };
}

export interface SourceHealthItem extends Source {
  last_checked_at?: string | null;
  last_success_at?: string | null;
  last_error_at?: string | null;
  errors_24h: number;
  items_24h: number;
  articles_24h: number;
  extraction_success_rate_24h?: number | null;
  quality_avg?: number | null;
  status: "ok" | "warning" | "broken";
}

export interface SourceHealthResponse {
  count: number;
  items: SourceHealthItem[];
}

export interface PipelineQueuesResponse {
  generated_at: string;
  queues: Record<string, number>;
}

export interface PipelineErrorsResponse {
  generated_at: string;
  count: number;
  by_step: Record<string, number>;
  items: any[];
}

export interface DeadQueueOverview {
  generated_at: string;
  queues: Record<string, number>;
}

export interface DeadQueueDetail {
  queue: string;
  count: number;
  items: Record<string, any>[];
}

export interface OpsSummary {
  generated_at: string;
  status: PipelineStatus;
  queues: PipelineQueuesResponse;
  dead_letter: {
    queues: Record<string, number>;
    total: number;
  };
  recent_errors_count: number;
  recent_errors: PipelineErrorsResponse;
  source_health_summary: {
    total: number;
    enabled: number;
    disabled: number;
    with_errors: number;
    high_error: number;
  };
  configured_models: {
    llm_model: string;
    embedding_model: string;
  };
  low_power_mode: boolean;
  backup: {
    path: string;
    exists: boolean;
  };
  obsidian_export: {
    enabled: boolean;
    path: string;
    exists: boolean;
  };
}

export interface Capabilities {
  generated_at: string;
  inbox: boolean;
  watchlist_config: boolean;
  research_projects_config: boolean;
  dead_queues: boolean;
  obsidian_export: boolean;
  home_assistant_skeleton: boolean;
  read_state_supported: boolean;
  db_watchlist_supported: boolean;
  db_projects_supported: boolean;
}

export interface InboxItem {
  id: number;
  title?: string;
  url?: string;
  source?: string;
  published_at?: string | null;
  summary_short?: string;
  category?: string;
  final_score?: number;
  word_count?: number;
  is_read?: boolean;
  is_saved?: boolean;
  is_hidden?: boolean;
  matched_watchlist?: string[];
}

export interface InboxResponse {
  mode: string;
  profile_id: string;
  hide_read: boolean;
  hide_hidden: boolean;
  read_state_supported: boolean;
  count: number;
  items: InboxItem[];
}

export interface UserStateUpdate {
  profile_id?: string;
  is_read?: boolean;
  is_saved?: boolean;
  is_hidden?: boolean;
}

export interface WatchlistEntity {
  id?: number;
  name: string;
  type?: string;
  priority?: number;
  enabled?: boolean;
}

export interface ProjectItem {
  id?: number;
  slug: string;
  name: string;
  keywords: string[];
  priority?: number;
  description?: string;
}
