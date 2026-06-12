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
