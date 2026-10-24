export type ProgressStatus = 'not_started' | 'in_progress' | 'completed'
export type LearningAction = 'view' | 'start' | 'complete' | 'favorite' | 'unfavorite'
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface ResourceSummary {
  display_type?: 'document' | 'course' | 'exercise' | null
  id: number; title: string; summary: string; tags: string[]; difficulty: number
  resource_type: 'document' | 'course' | 'exercise'; category_code: string
  source_name: string | null; license_note: string | null
  status: 'draft' | 'published' | 'offline' | 'deleted'
  version_no: number; created_by: number; published_at: string | null
  created_at: string; updated_at: string
}
export interface ResourceDetail extends ResourceSummary { content: string | null; content_url: string | null }
export interface ListQuery { page: number; page_size: number; q?: string; category_code?: string }
export interface Progress { resource_id: number; status: ProgressStatus; first_started_at: string | null; completed_at: string | null; updated_at: string | null }
export interface Favorite { resource_id: number; created_at: string }
export interface EventPayload { event_uuid: string; session_id: string; client_occurred_at?: string }
export interface EventReceipt {
  id: number; event_uuid: string; user_id: number; resource_id: number
  event_type: 'RESOURCE_VIEW' | 'LEARNING_START' | 'LEARNING_COMPLETE' | 'FAVORITE_ADD' | 'FAVORITE_REMOVE'
  event_source: 'client' | 'server'; schema_version: number; resource_version: number
  session_id: string | null; occurred_at: string; received_at: string; client_occurred_at: string | null
  is_effective: 0 | 1; state_before: string | null; state_after: string | null
}
export const categories = [
  ['python-basics', 'Python 基础'], ['java-basics', 'Java 基础'], ['databases', '数据库'],
  ['data-engineering', '数据工程'], ['machine-learning', '机器学习'],
  ['web-development', 'Web 开发'], ['algorithms', '算法'],
] as const
export const typeNames = { document: '文档', course: '课程', exercise: '练习' }
export const difficultyNames: Record<number, string> = { 1: '入门', 2: '进阶', 3: '高级' }
export const progressNames = { not_started: '未开始', in_progress: '学习中', completed: '已完成' }
export function safeContentUrl(value: string | null) {
  if (!value) return undefined
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : undefined }
  catch { return undefined }
}
