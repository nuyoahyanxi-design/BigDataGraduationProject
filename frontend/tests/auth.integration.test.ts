import { randomBytes } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { afterAll, beforeAll, expect, it, vi } from 'vitest'
import { http, request } from '../src/api/http'
import { useAuthStore, SESSION_KEY } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'

const target = process.env.AUTH_API_TARGET
const run = target ? it : it.skip
const username = 'fa_' + randomBytes(16).toString('hex')
const password = randomBytes(24).toString('base64url')
let created = false
const originalBase = http.defaults.baseURL
let auth: ReturnType<typeof useAuthStore>
beforeAll(async () => {
  if (!target) return
  memoryStorage(); http.defaults.baseURL = target; auth = newSession()
  try {
    await request({ method: 'POST', url: '/auth/register', skipAuth: true, data: { username, password, interest_tags: ['python', 'spark'] } })
    created = true
  } catch { throw new Error('Temporary learner creation failed; credentials redacted') }
})
afterAll(() => {
  http.defaults.baseURL = originalBase; vi.unstubAllGlobals()
  if (created) {
    const python = process.env.AUTH_TEST_PYTHON
    if (!python) throw new Error('Missing cleanup Python')
    try { execFileSync(python, ['tests/cleanup-auth-user.py', username], { env: process.env, stdio: 'pipe' }) }
    catch { throw new Error('Temporary learner cleanup failed; inspect fixture cleanup without credentials') }
  }
})
run('真实 API 正确登录、Token 保存及当前用户展示数据', async () => {
  try { await auth.signIn({ username, password }) } catch { throw new Error('Real API sign-in failed; credentials redacted') }
  expect(auth.authenticated).toBe(true)
  expect(Boolean(sessionStorage.getItem(SESSION_KEY))).toBe(true)
  expect(auth.user?.username === username).toBe(true)
  expect(auth.role).toBe('learner')
  expect(auth.user?.interest_tags).toEqual(['python', 'spark'])
})
run('新 Pinia 实例模拟刷新并经后端恢复', async () => {
  auth = newSession()
  await auth.restore().catch(() => { throw new Error('Real API restore failed') })
  expect(auth.authenticated).toBe(true)
  expect(await createAuthGuard(auth)({ name: 'home', meta: { requiresAuth: true } })).toBe(true)
})
run('错误密码返回公共提示，不保存会话', async () => {
  let message = ''; let status: number | undefined
  try { await auth.signIn({ username, password: randomBytes(24).toString('base64url') }) }
  catch (error) { message = (error as Error).message; status = (error as { status: number }).status }
  expect(status).toBe(401); expect(message).toBe('用户名或密码错误')
  expect(auth.authenticated).toBe(false); expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
})
run('无效 Token 被真实后端拒绝后退出并触发路由拦截', async () => {
  auth.token = 'intentionally-invalid-test-value'; auth.expiresAt = Date.now() + 60000; auth.persist()
  await auth.restore()
  expect(auth.token).toBe(''); expect(auth.user).toBeNull()
  expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
  expect(await createAuthGuard(auth)({ name: 'home', meta: { requiresAuth: true } })).toEqual({ name: 'login' })
})
