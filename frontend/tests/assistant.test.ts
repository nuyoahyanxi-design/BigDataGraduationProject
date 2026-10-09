import { afterEach, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { http } from '../src/api/http'
import { askAI, getAICapabilities, getAIHistory, getAIQuestion } from '../src/api/assistant'
import { aiStatus, validateAIQuestion, type AIRecord } from '../src/types/assistant'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'
import { AxiosError } from 'axios'
import { ApiError } from '../src/api/http'
import { aiRequestError, AI_TIMEOUT_MESSAGE } from '../src/services/ai-feedback'
const original = http.defaults.adapter
it('AI的HTTP504转为友好提示，仍保留原错误状态且不重试', async () => {
  let calls = 0
  http.defaults.adapter = async config => {
    calls++
    throw new AxiosError('upstream timeout', 'ERR_BAD_RESPONSE', config, undefined,
      { config, status: 504, statusText: 'Gateway Timeout', headers: {}, data: { error_code: 'provider_timeout' } })
  }
  let caught: unknown
  try { await askAI({ request_uuid: 'timeout-test', question: 'Spark?', mode: 'general', resource_id: null, consent_version: 'agnes-external-v1' }) }
  catch (problem) { caught = problem }
  expect(caught).toBeInstanceOf(ApiError)
  expect((caught as ApiError).status).toBe(504)
  expect(aiRequestError(caught, '请求失败')).toBe(AI_TIMEOUT_MESSAGE)
  expect(aiRequestError(caught, '请求失败')).not.toContain('HTTP')
  expect(calls).toBe(1)
})
it('超时历史提供友好状态，不改变provider_timeout记录', () => {
  const record = { status: 'unknown', error_code: 'provider_timeout' } as AIRecord
  expect(aiStatus(record)).toBe(AI_TIMEOUT_MESSAGE)
  expect(aiStatus(record)).toContain('消耗')
  expect(aiStatus(record)).not.toContain('provider_timeout')
  expect(record.error_code).toBe('provider_timeout')
  expect(record.status).toBe('unknown')
})
it('AI非超时错误与正常回答仍使用原提示', () => {
  expect(aiRequestError(new ApiError('登录已失效，请重新登录', 401), '失败')).toContain('重新登录')
  expect(aiRequestError(new ApiError('没有访问权限', 403), '失败')).toBe('没有访问权限')
  expect(aiRequestError(null, '历史暂不可用')).toBe('历史暂不可用')
  expect(aiStatus({ status: 'succeeded', error_code: null } as AIRecord)).toBe('回答完成')
})
afterEach(() => { http.defaults.adapter = original })
it('AI页面匿名仍跳转登录', async () => {
  memoryStorage(); const auth = newSession()
  expect(await createAuthGuard(auth)({ name: 'assistant', meta: { requiresAuth: true } })).toEqual({ name: 'login' })
})
it('问题与外发确认及资源编号校验', () => {
  expect(validateAIQuestion(' ', true, 'general', undefined)).not.toBe('')
  expect(validateAIQuestion('a'.repeat(2001), true, 'general', undefined)).not.toBe('')
  expect(validateAIQuestion('Spark?', false, 'general', undefined)).toContain('确认')
  expect(validateAIQuestion('Spark?', true, 'resource', undefined)).toContain('编号')
  expect(validateAIQuestion('Spark?', true, 'resource', 406)).toBe('')
})
it('AI请求超时独立且不提供任意用户字段', async () => {
  const requests: { url?: string; timeout?: number; params?: unknown; data?: string }[] = []
  http.defaults.adapter = async config => { requests.push(config); return { config, status: 200, statusText: 'OK', headers: {}, data: {} } }
  await getAICapabilities()
  await askAI({ request_uuid: 'test-uuid', question: 'Spark?', mode: 'general', resource_id: null, consent_version: 'agnes-external-v1' })
  await getAIHistory(2); await getAIQuestion('test-uuid')
  expect(requests[1]?.timeout).toBe(60000)
  expect(JSON.parse(requests[1]!.data!)).not.toHaveProperty('user_id')
  expect(requests[2]?.params).toEqual({ page: 2, page_size: 20 })
  expect(requests[3]?.url).toBe('/ai/questions/test-uuid')
})
it('未知完成状态提示潜在重复消耗', () => {
  expect(aiStatus({ status: 'unknown' } as AIRecord)).toContain('消耗')
  expect(aiStatus({ status: 'succeeded', error_code: 'resource_unavailable' } as AIRecord)).toContain('隐藏')
})
it('回答只用文本插值，页面不持久化问题和自动重试POST', () => {
  const source = readFileSync('src/views/AiAssistantView.vue', 'utf8')
  const content = readFileSync('src/components/AiAnswerContent.vue', 'utf8')
  expect(content).toContain('{{ visibleText }}')
  expect(content).not.toContain('v-html')
  expect(source).not.toContain('v-html')
  expect(source).not.toContain('localStorage')
  expect(source).toContain('getAIQuestion(uuid)')
})
