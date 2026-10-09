import { AI_TIMEOUT_MESSAGE, AI_PROVIDER_BUSY_MESSAGE } from '@/services/ai-feedback'

export interface AICapabilities { enabled: boolean; ready: boolean; max_question_chars: number; consent_version: string; notice: string }
export interface AIQuestion { request_uuid: string; question: string; mode: 'general' | 'resource'; resource_id: number | null; consent_version: string }
export interface AIRecord {
  request_uuid: string; mode: string; resource_id: number | null; resource_version: number | null
  question: string; answer: string | null; status: 'pending' | 'succeeded' | 'failed' | 'unknown'
  model: string; created_at: string; finished_at: string | null; error_code: string | null; source: string
}
export interface AIHistory { items: AIRecord[]; total: number; page: number; page_size: number }
export function validateAIQuestion(question: string, consent: boolean, mode: string, resourceId: number | undefined): string {
  if (!question.trim() || question.length > 2000) return '问题需为1–2000字符'
  if (!consent) return '请先确认外部模型处理说明'
  if (mode === 'resource' && (!Number.isSafeInteger(resourceId) || (resourceId ?? 0) < 1)) return '请输入有效资源编号'
  return ''
}
export function aiStatus(record: AIRecord): string {
  if (record.error_code === 'provider_timeout') return AI_TIMEOUT_MESSAGE
  if (record.error_code === 'provider_rate_limit') return AI_PROVIDER_BUSY_MESSAGE
  if (record.error_code === 'resource_unavailable') return '资源不可用，内容已隐藏'
  return { pending: '处理中，请刷新状态；不要重复发送', succeeded: '回答完成', failed: '模型调用失败，可查看错误状态', unknown: '完成情况未知，重新提问可能再次产生消耗' }[record.status]
}
