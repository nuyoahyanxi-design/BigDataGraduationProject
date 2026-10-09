import { afterEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { getRecommendations } from '../src/api/recommendations'
import { formatScore } from '../src/types/recommendations'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage, newSession } from './helpers'

const originalAdapter = http.defaults.adapter
afterEach(() => { http.defaults.adapter = originalAdapter; vi.unstubAllGlobals() })
it('默认内容推荐请求不接受目标用户ID', async () => {
  http.defaults.adapter = async (config) => {
    expect(config.url).toBe('/recommendations/me')
    expect(config.params).toEqual({ algorithm: 'content_v1' })
    return { config, status: 200, statusText: 'OK', headers: {}, data: { items: [] } }
  }
  expect((await getRecommendations()).items).toEqual([])
})
it('热门方法通过明确参数选择', async () => {
  http.defaults.adapter = async (config) => {
    expect(config.params).toEqual({ algorithm: 'popular_v1' })
    return { config, status: 200, statusText: 'OK', headers: {}, data: { items: [] } }
  }
  await getRecommendations('popular_v1')
})
it('分数格式化保留精度并处理零分', () => {
  expect(formatScore('0.123456789123')).toBe('0.123456789123')
  expect(formatScore('0.000000000001')).toBe('0.000000000001')
  expect(formatScore('0.000000000000')).toBe('0')
  expect(formatScore('10.000000000000')).toBe('10')
})
it('未登录不能访问推荐页面', async () => {
  memoryStorage()
  expect(await createAuthGuard(newSession())({ name: 'recommendations', meta: { requiresAuth: true } })).toEqual({ name: 'login' })
})
