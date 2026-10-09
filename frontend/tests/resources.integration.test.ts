import { randomBytes } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { afterAll, beforeAll, expect, it, vi } from 'vitest'
import { http, request } from '../src/api/http'
import { ResourceLearning } from '../src/services/resource-learning'
import { getResource, listResources, sendLearningEvent } from '../src/api/resources'
import { getCourse } from '../src/api/courses'
import type { Page, EventReceipt, ResourceSummary } from '../src/types/resources'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'

const target = process.env.AUTH_API_TARGET
const run = target ? it : it.skip
const username = 'fr_' + randomBytes(16).toString('hex')
const password = randomBytes(24).toString('base64url')
const originalBase = http.defaults.baseURL
let created = false; let resource: ResourceSummary; let learning: ResourceLearning
beforeAll(async () => {
  if (!target) return
  memoryStorage(); http.defaults.baseURL = target
  const auth = newSession()
  try {
    await request({ method: 'POST', url: '/auth/register', skipAuth: true, data: { username, password } }); created = true
    await auth.signIn({ username, password })
    expect(await createAuthGuard(auth)({ name: 'resources', meta: { requiresAuth: true } })).toBe(true)
    const result = await listResources({ page: 1, page_size: 100 })
    if (!result.items.length) throw new Error('No published resources available')
    // These tests exercise legacy unchaptered-resource semantics. Chapter completion
    // is covered by the course tests and cannot be bypassed through /complete.
    let legacyResource: ResourceSummary | undefined
    for (const item of result.items) {
      if (!(await getCourse(item.id)).chapters.length) { legacyResource = item; break }
    }
    if (!legacyResource) throw new Error('No published unchaptered resource for legacy tests')
    resource = legacyResource; learning = new ResourceLearning(resource.id)
  } catch { throw new Error('Resource integration fixture setup failed; credentials redacted') }
})
afterAll(() => {
  http.defaults.baseURL = originalBase; vi.unstubAllGlobals()
  if (created) {
    try { execFileSync(process.env.AUTH_TEST_PYTHON!, ['tests/cleanup-resource-user.py', username], { env: process.env, stdio: 'pipe' }) }
    catch { throw new Error('Temporary resource learner cleanup failed; credentials redacted') }
  }
})
run('登录后读取已发布资源及分页', async () => {
  const first = await listResources({ page: 1, page_size: 1 })
  expect(first.items.length).toBe(1); expect(first.items.every((item) => item.status === 'published')).toBe(true)
  if (first.total > 1) {
    const second = await listResources({ page: 2, page_size: 1 })
    expect(second.page).toBe(2); expect(second.items[0].id !== first.items[0].id).toBe(true)
  }
})
run('标题搜索和分类筛选返回匹配资源', async () => {
  const result = await listResources({ page: 1, page_size: 100, q: resource.title, category_code: resource.category_code })
  expect(result.items.some((item) => item.id === resource.id)).toBe(true)
  expect(result.items.every((item) => item.title.includes(resource.title) && item.category_code === resource.category_code)).toBe(true)
  const empty = await listResources({ page: 1, page_size: 12, q: 'no_match_' + randomBytes(12).toString('hex') })
  expect(empty.total).toBe(0)
})
run('详情完整信息与初始个人状态可查询', async () => {
  const detail = await getResource(resource.id)
  expect(detail.title).toBe(resource.title); expect('content' in detail && 'content_url' in detail).toBe(true)
  await learning.load(); expect(learning.state.error).toBe(''); expect(learning.state.stateReady).toBe(true)
  expect(learning.state.progress).toBe('not_started'); expect(learning.state.favorite).toBe(false)
})
run('浏览产生真实事件并使用会话UUID', async () => {
  await learning.recordView(); expect(learning.state.viewError).toBe('')
  const result = await request<Page<EventReceipt>>({ url: '/users/me/events', params: { resource_id: resource.id } })
  expect(result.total).toBe(1); expect(result.items[0].event_type).toBe('RESOURCE_VIEW')
  expect(result.items[0].session_id).toBe(learning.sessionId)
})
run('开始与完成学习使状态变化且幂等重放不增加事件', async () => {
  await learning.perform('start'); expect(learning.state.progress).toBe('in_progress')
  const receipt = learning.state.lastReceipt!
  const replay = await sendLearningEvent(resource.id, 'start', { event_uuid: receipt.event_uuid, session_id: learning.sessionId })
  expect(replay.id).toBe(receipt.id)
  await learning.perform('complete'); expect(learning.state.progress).toBe('completed')
  expect(learning.state.actionError).toBe('')
})
run('收藏与取消收藏切换状态且五类事件完整', async () => {
  await learning.perform('favorite'); expect(learning.state.favorite).toBe(true)
  await learning.perform('unfavorite'); expect(learning.state.favorite).toBe(false)
  const result = await request<Page<EventReceipt>>({ url: '/users/me/events', params: { resource_id: resource.id } })
  expect(result.total).toBe(5)
  expect(result.items.map((item) => item.event_type).sort()).toEqual(['RESOURCE_VIEW', 'LEARNING_START', 'LEARNING_COMPLETE', 'FAVORITE_ADD', 'FAVORITE_REMOVE'].sort())
  expect(result.items.every((item) => item.is_effective === 1)).toBe(true)
})
