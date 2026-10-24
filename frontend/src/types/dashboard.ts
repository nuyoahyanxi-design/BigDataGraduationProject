export interface DailyMetric { day: string; resource_view: number; learning_start: number; learning_complete: number; favorite_add: number; favorite_remove: number }
export interface DashboardMetrics {
  chapter?: { chapter_views: number; video_plays: number; viewed_pairs: number; played_pairs: number; play_users: number; completed_pairs: number; daily: { day: string; chapter_view: number; video_play: number; chapter_complete: number }[]; rule: string } | null
  users: { total: number; active_learners: number; admins: number }
  resources: { total: number; published: number; scope_label?: string | null }
  resource_categories: { category: string; count: number }[]
  behavior: { total_effective_events: number; window_events: number; daily: DailyMetric[]; timezone: 'Asia/Shanghai'; window_days: 30 }
  learning: { scope_label?: string | null; started_pairs: number; in_progress: number; completed: number; completion_rate: number | null }
}
export interface DashboardResponse {
  available: boolean
  data: null | {
    status: 'completed'; batch_id: string; source_batch_id: string; generated_at: string; as_of_utc: string
    source: string; dataset_origin: string; spark_version: string; metrics: DashboardMetrics
    quality: { input_count: number; filtered_count: number; output_count: number }
    recommendation_publication: null | { batch_id: string; profile_batch_id: string; generated_at: string; as_of_utc: string }
  }
  profiles: null | { source: string; batch_id: string | null; users: number; evidence: Record<string, number> }
  recommendations: null | { source: string; batch_id: string | null; generated_at: string | null; rows: number; algorithms: { algorithm: string; rows: number; users: number; resources: number }[] }
  message: string | null
}
