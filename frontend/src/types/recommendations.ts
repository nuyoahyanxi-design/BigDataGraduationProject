import type { ResourceSummary } from './resources'
export type RecommendationAlgorithm = 'content_v1' | 'popular_v1'
export interface ProfileSummary {
  batch_id: string; generated_at: string; as_of_utc: string
  interest_weights: Record<string, number>
  evidence: 'observed' | 'explicit_only' | 'no_evidence'
  event_counts: Record<'resource_view' | 'learning_start' | 'learning_complete' | 'favorite_add' | 'favorite_remove', number>
  active_days: number; started_resources: number; completed_resources: number; completion_rate: number | null
}
export interface RecommendationItem {
  resource_id: number; resource: ResourceSummary; algorithm: RecommendationAlgorithm; score: string; rank: number; reason: string
}
export interface RecommendationsResponse {
  batch_id: string | null; generated_at: string | null; as_of_utc: string | null
  algorithm: RecommendationAlgorithm; items: RecommendationItem[]; profile: ProfileSummary | null
  explicit_interest_tags: string[]; message: string | null
}
export const algorithmNames = { content_v1: '内容推荐', popular_v1: '热门推荐（Baseline）' }
export function formatScore(value: string) {
  return value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value
}
