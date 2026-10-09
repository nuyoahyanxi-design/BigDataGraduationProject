import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { http, request } from '../src/api/http'
import { SESSION_KEY } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'

const originalAdapter = http.defaults.adapter
const user = { id: 1, username: 'fixture', nickname: null, role: 'learner', status: 'active', interest_tags: ['python'], created_at: '', updated_at: '' }
beforeEach(() => { memoryStorage() })
afterEach(() => { http.defaults.adapter = originalAdapter; vi.unstubAllGlobals() })
function success(config: InternalAxiosRequestConfig, data: unknown) { return { data, status: 200, statusText: 'OK', headers: {}, config } }

it('未登录首页拦截到登录页', async () => {
  expect(await createAuthGuard(newSession())({ name: 'home', meta: { requiresAuth: true } })).toEqual({ name: 'login' })
})
it('损坏缓存清理并拒绝进入首页', async () => {
  sessionStorage.setItem(SESSION_KEY, '{broken')
  const auth = newSession(); await auth.restore()
  expect(auth.authenticated).toBe(false)
  expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
})
it('已过期缓存不发送请求', async () => {
  const adapter = vi.fn(); http.defaults.adapter = adapter
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'test-only-invalid', expiresAt: Date.now() - 1 }))
  const auth = newSession(); await auth.restore()
  expect(adapter).not.toHaveBeenCalled(); expect(auth.token).toBe('')
})
it('刷新重新取当前用户且自动携带认证头', async () => {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'test-only-invalid', expiresAt: Date.now() + 60000 }))
  http.defaults.adapter = async (config) => {
    expect(Boolean(config.headers.get('Authorization'))).toBe(true)
    return success(config, user)
  }
  const auth = newSession(); await auth.restore()
  expect(auth.user?.username).toBe('fixture'); expect(auth.role).toBe('learner')
  expect(await createAuthGuard(auth)({ name: 'login', meta: {} })).toEqual({ name: 'home' })
})
it('401 清空当前会话与缓存', async () => {
  const auth = newSession(); auth.token = 'test-only-invalid'; auth.expiresAt = Date.now() + 60000; auth.persist()
  http.defaults.adapter = async (config) => { throw new AxiosError('unauthorized', 'ERR_BAD_REQUEST', config, undefined, { ...success(config, {}), status: 401 }) }
  let status: number | undefined
  try { await request({ url: '/users/me' }) } catch (error) { status = (error as { status: number }).status }
  expect(status).toBe(401); expect(auth.token).toBe(''); expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
})
it('旧会话的失败不会清理新会话', () => {
  const auth = newSession(); auth.token = 'new-test-only-invalid'; auth.expiresAt = Date.now() + 60000
  auth.invalidate('old-test-only-invalid'); expect(Boolean(auth.token)).toBe(true)
})
it('网络失败保留缓存，之后可重试恢复', async () => {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'test-only-invalid', expiresAt: Date.now() + 60000 }))
  http.defaults.adapter = async (config) => { throw new AxiosError('network', 'ERR_NETWORK', config) }
  const auth = newSession()
  await auth.restore().catch(() => undefined)
  expect(Boolean(auth.token)).toBe(true); expect(auth.authenticated).toBe(false)
  http.defaults.adapter = async (config) => success(config, user)
  await auth.restore(); expect(auth.authenticated).toBe(true)
})
it('存储不可用时保留内存会话并给出提示', () => {
  vi.stubGlobal('sessionStorage', { setItem: () => { throw new Error('blocked') }, removeItem: () => {} })
  const auth = newSession(); auth.token = 'test-only-invalid'; auth.expiresAt = Date.now() + 60000
  auth.persist(); expect(auth.storageWarning.length > 0).toBe(true); expect(Boolean(auth.token)).toBe(true)
})
it('角色来自当前用户，退出同时清空身份与会话', async () => {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'test-only-invalid', expiresAt: Date.now() + 60000 }))
  http.defaults.adapter = async (config) => success(config, { ...user, role: 'admin' })
  const auth = newSession(); await auth.restore(); expect(auth.role).toBe('admin')
  auth.clear(); expect(auth.role).toBeNull(); expect(auth.user).toBeNull()
  expect(sessionStorage.getItem(SESSION_KEY)).toBeNull()
})
it('登录请求不携带旧 Token', async () => {
  const auth = newSession(); auth.token = 'test-only-invalid'; auth.expiresAt = Date.now() + 60000
  http.defaults.adapter = async (config) => {
    expect(Boolean(config.headers.get('Authorization'))).toBe(false)
    return success(config, {})
  }
  await request({ url: '/auth/login', method: 'POST', skipAuth: true })
})
it('持久化只保存 Token 和截止时间，不保存用户隐私字段', () => {
  const auth = newSession(); auth.token = 'test-only-invalid'; auth.expiresAt = Date.now() + 60000
  auth.persist()
  const cached = JSON.parse(sessionStorage.getItem(SESSION_KEY)!)
  expect(Object.keys(cached).sort()).toEqual(['expiresAt', 'token'])
})
