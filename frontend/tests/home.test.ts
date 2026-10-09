import { afterEach, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { createPinia } from 'pinia'
import { renderToString } from 'vue/server-renderer'
import { useAuthStore } from '../src/stores/auth'
import { http } from '../src/api/http'
import HomeView from '../src/views/HomeView.vue'
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }), useRoute: () => ({ query: {} }) }))
const original = http.defaults.adapter
afterEach(() => { http.defaults.adapter = original })
async function renderResponse(data: unknown) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.token = 'test-only-token'
  auth.expiresAt = Date.now() + 60000
  http.defaults.adapter = async config => ({ config, status: 200, statusText: 'OK', headers: {}, data })
  await auth.restore()
  return renderToString(createSSRApp({ render: () => h(HomeView) }).use(pinia))
}
it.each([
  ['null用户', null],
  ['空对象', {}],
  ['缺少兴趣字段', { username: 'student', role: 'learner' }],
  ['null标签', { username: 'student', role: 'learner', interest_tags: null }],
  ['空数组', { username: 'student', role: 'learner', interest_tags: [] }],
])('当前用户接口返回%s时首页不白屏', async (_name, data) => {
  const html = await renderResponse(data)
  expect(html).toContain('个人账户')
  expect(html).toContain('浏览学习资源')
  expect(html).toContain('查看个性化推荐')
  if (data !== null) expect(html).toContain('暂无兴趣标签')
})
it('正常兴趣标签与管理员入口保持原展示', async () => {
  const html = await renderResponse({ username: 'admin', role: 'admin', interest_tags: ['python', 'spark'] })
  expect(html).toContain('python')
  expect(html).toContain('spark')
  expect(html).toContain('管理员')
  expect(html).toContain('进入管理员后台')
  expect(html).not.toContain('暂无兴趣标签')
})
