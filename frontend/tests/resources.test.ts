import { afterEach, expect, it, vi } from 'vitest'
import { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { http, ApiError } from '../src/api/http'
import { listResources, isFavorited, sendLearningEvent } from '../src/api/resources'
import { ResourceLearning } from '../src/services/resource-learning'
import { safeContentUrl } from '../src/types/resources'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'
const originalAdapter = http.defaults.adapter
afterEach(() => { http.defaults.adapter = originalAdapter; vi.unstubAllGlobals() })
const response = (config: InternalAxiosRequestConfig, data: unknown) => ({ config, data, status: 200, statusText: 'OK', headers: {} })

it('列表参数准确传递分页、标题和分类', async () => {
  http.defaults.adapter = async (config) => {
    expect(config.params).toEqual({ page: 2, page_size: 12, q: 'Python', category_code: 'python-basics' })
    return response(config, { items: [], total: 0, page: 2, page_size: 12 })
  }
  await listResources({ page: 2, page_size: 12, q: 'Python', category_code: 'python-basics' })
})
it('收藏状态查询读取后续分页', async () => {
  const pages: number[] = []
  http.defaults.adapter = async (config) => {
    pages.push(config.params.page)
    return response(config, { items: [{ resource_id: config.params.page === 2 ? 42 : 1 }], total: 101, page: config.params.page, page_size: 100 })
  }
  expect(await isFavorited(42)).toBe(true); expect(pages).toEqual([1, 2])
})
it('取消收藏使用 DELETE JSON body', async () => {
  http.defaults.adapter = async (config) => {
    expect(config.method).toBe('delete'); expect(config.url).toBe('/resources/42/favorite')
    expect(JSON.parse(config.data).event_uuid).toBe('test-only-event')
    return response(config, {})
  }
  await sendLearningEvent(42, 'unfavorite', { event_uuid: 'test-only-event', session_id: 'test-only-session' })
})
it('超时保留UUID重试并阻止不同操作，接受后刷新状态', async () => {
  let attempt = 0; const uuids: string[] = []
  http.defaults.adapter = async (config) => {
    if (config.url?.endsWith('/start')) {
      uuids.push(JSON.parse(config.data).event_uuid)
      if (++attempt === 1) throw new AxiosError('timeout', 'ECONNABORTED', config)
      return response(config, { is_effective: 1 })
    }
    if (config.url?.endsWith('/progress')) return response(config, { items: [{ resource_id: 42, status: 'in_progress' }] })
    return response(config, { items: [], total: 0, page: 1, page_size: 100 })
  }
  const learning = new ResourceLearning(42); learning.state.stateReady = true
  await learning.perform('start'); expect(learning.state.pending?.action).toBe('start')
  await learning.perform('favorite'); expect(attempt).toBe(1)
  await learning.perform('start'); expect(uuids[0] === uuids[1]).toBe(true)
  expect(learning.state.progress).toBe('in_progress'); expect(learning.state.pending).toBeNull()
})
it('事件成功但状态查询失败不重复提交且按钮状态待确认', async () => {
  let writes = 0
  http.defaults.adapter = async (config) => {
    if (config.url?.endsWith('/start')) { writes++; return response(config, { is_effective: 1 }) }
    throw new AxiosError('network', 'ERR_NETWORK', config)
  }
  const learning = new ResourceLearning(42); learning.state.stateReady = true
  await learning.perform('start'); await learning.perform('start')
  expect(writes).toBe(1); expect(learning.state.pending).toBeNull()
  expect(learning.state.notice.length > 0).toBe(true); expect(learning.state.stateReady).toBe(false)
})
it('双击写操作只产生一个请求', async () => {
  let resolve!: () => void; let writes = 0
  const waiting = new Promise<void>((done) => { resolve = done })
  http.defaults.adapter = async (config) => {
    if (config.url?.endsWith('/favorite')) { writes++; await waiting; return response(config, { is_effective: 1 }) }
    if (config.url?.endsWith('/progress')) return response(config, { items: [{ resource_id: 42, status: 'not_started' }] })
    return response(config, { items: [{ resource_id: 42 }], total: 1, page: 1, page_size: 100 })
  }
  const learning = new ResourceLearning(42); learning.state.stateReady = true
  const first = learning.perform('favorite'); const second = learning.perform('favorite')
  resolve(); await Promise.all([first, second]); expect(writes).toBe(1); expect(learning.state.favorite).toBe(true)
})
it('浏览失败重试保留UUID及带时区客户端时间', async () => {
  const uuids: string[] = []; let attempt = 0
  http.defaults.adapter = async (config) => {
    const data = JSON.parse(config.data); uuids.push(data.event_uuid)
    expect(data.client_occurred_at.endsWith('Z')).toBe(true)
    if (++attempt === 1) throw new AxiosError('network', 'ERR_NETWORK', config)
    return response(config, {})
  }
  const learning = new ResourceLearning(42)
  await learning.recordView(); await learning.recordView(); await learning.recordView()
  expect(uuids.length).toBe(2)
  expect(uuids[0] === uuids[1]).toBe(true); expect(learning.state.viewPending).toBeNull()
})
it('未登录资源页受路由保护', async () => {
  memoryStorage(); const auth = newSession()
  expect(await createAuthGuard(auth)({ name: 'resources', meta: { requiresAuth: true } })).toEqual({ name: 'login' })
})
it('危险外部地址被拒绝，HTTP(S)可用', () => {
  expect(safeContentUrl('javascript:alert(1)')).toBeUndefined()
  expect(safeContentUrl('https://example.com/learning')).toBe('https://example.com/learning')
})
