import { afterEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { getRecommendations } from '../src/api/recommendations'
import { formatRecommendationScore, formatScore } from '../src/types/recommendations'
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
it('综合得分以百分比显示，热门热度保留原始量纲', () => {
  expect(formatRecommendationScore('0.750000000000', 'content_v1')).toBe('综合推荐得分：75%')
  expect(formatRecommendationScore('0.928476690885', 'content_v1')).toBe('综合推荐得分：92.8%')
  expect(formatRecommendationScore('0', 'content_v1')).toBe('综合推荐得分：0%')
  expect(formatRecommendationScore('1', 'content_v1')).toBe('综合推荐得分：100%')
  expect(formatRecommendationScore('12.000000000000', 'popular_v1')).toBe('热度得分：12')
  expect(formatRecommendationScore('12', 'content_v1')).toBe('原始推荐得分：12')
})
