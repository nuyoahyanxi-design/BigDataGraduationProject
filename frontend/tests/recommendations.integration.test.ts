import { randomBytes } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { afterAll, beforeAll, expect, it, vi } from 'vitest'
import { http, request } from '../src/api/http'
import { getRecommendations } from '../src/api/recommendations'
import { memoryStorage, newSession } from './helpers'

const run = process.env.AUTH_API_TARGET ? it : it.skip
const username = 'fa_' + randomBytes(16).toString('hex')
const password = randomBytes(24).toString('base64url')
const originalBase = http.defaults.baseURL
let created = false
beforeAll(async () => {
  if (!process.env.AUTH_API_TARGET) return
  memoryStorage(); http.defaults.baseURL = process.env.AUTH_API_TARGET
  const auth = newSession()
  try {
    await request({ method: 'POST', url: '/auth/register', skipAuth: true, data: { username, password, interest_tags: ['machine-learning'] } }); created = true
    await auth.signIn({ username, password })
  } catch { throw new Error('Recommendation fixture setup failed; credentials redacted') }
})
afterAll(() => {
  http.defaults.baseURL = originalBase; vi.unstubAllGlobals()
  if (created) {
    try { execFileSync(process.env.AUTH_TEST_PYTHON!, ['tests/cleanup-auth-user.py', username], { env: process.env, stdio: 'pipe' }) }
    catch { throw new Error('Recommendation learner cleanup failed; credentials redacted') }
  }
})
run('真实新用户返回批次、显式兴趣与友好空结果', async () => {
  const result = await getRecommendations()
  expect(result.items).toEqual([]); expect(result.profile).toBeNull()
  expect(result.explicit_interest_tags).toEqual(['machine-learning'])
  expect(result.algorithm).toBe('content_v1'); expect(Boolean(result.batch_id)).toBe(true)
  expect(result.message?.includes('暂无')).toBe(true)
})
run('真实接口支持热门算法选择', async () => {
  const result = await getRecommendations('popular_v1')
  expect(result.algorithm).toBe('popular_v1'); expect(result.items).toEqual([])
})
