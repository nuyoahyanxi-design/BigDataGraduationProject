import { ApiError } from '@/api/http'

export const AI_TIMEOUT_MESSAGE = 'AI助手暂时未能完成回答，请稍后再试。可先查看历史记录；重新提问可能再次产生消耗。'
export const AI_PROVIDER_BUSY_MESSAGE = 'AI模型服务暂时繁忙，请稍后再试。可先查看历史回答，避免连续重复发送。'

export function aiRequestError(problem: unknown, fallback: string): string {
  if (problem instanceof ApiError && problem.status === 504) return AI_TIMEOUT_MESSAGE
  if (problem instanceof ApiError) {
    if (problem.aiLimitSource === 'provider_rate_limit') return AI_PROVIDER_BUSY_MESSAGE
    if (problem.status === 429) {
      if (problem.aiLimitSource === 'user_daily') return '本日AI问答额度已用完，将在下一次北京时间08:00刷新。可先查看历史回答。'
      if (problem.aiLimitSource === 'global_daily') return '平台本日AI问答额度已用完，将在下一次北京时间08:00刷新。可先阅读课程或查看历史回答。'
      if (problem.aiLimitSource === 'concurrency') return 'AI助手正在处理其他问题，请稍等片刻再发送；无需重复点击。'
      return 'AI助手请求暂时受限，请稍后再试，或查看历史回答。'
    }
  }
  return problem instanceof Error ? problem.message : fallback
}
