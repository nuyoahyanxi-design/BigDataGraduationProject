// Browser component harness only. Not imported by the production entry/build.
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../src/App.vue'
import ResourcesView from '../src/views/ResourcesView.vue'
import ResourceDetailView from '../src/views/ResourceDetailView.vue'
import HomeView from '../src/views/HomeView.vue'
import LoginView from '../src/views/LoginView.vue'
import { pinia } from '../src/stores'
import { useAuthStore } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { http } from '../src/api/http'
import type { ResourceDetail, ProgressStatus } from '../src/types/resources'
import 'element-plus/dist/index.css'
import '../src/styles/base.css'

const auth = useAuthStore(pinia)
auth.token = 'invalid-component-test-placeholder'
auth.expiresAt = Date.now() + 3600000
auth.restored = true
auth.user = { id: 1, username: 'component_test_learner', nickname: null, role: 'learner', status: 'active', interest_tags: ['spark'], created_at: '', updated_at: '' }
const resources: ResourceDetail[] = Array.from({ length: 13 }, (_, i) => ({
  id: 100 + i, title: i < 2 ? `Spark 数据处理练习 ${i + 1}` : `Python 基础学习 ${i - 1}`,
  summary: '用于验证页面交互的模拟资源，不代表真实数据库数据。', tags: i < 2 ? ['spark', 'big-data'] : ['python'], difficulty: i % 3 + 1,
  resource_type: 'document', category_code: i < 2 ? 'data-engineering' : 'python-basics', source_name: '组件测试', license_note: '仅测试',
  status: 'published', version_no: 1, created_by: 1, published_at: '2026-10-05T00:00:00', created_at: '2026-10-05T00:00:00', updated_at: '2026-10-05T00:00:00',
  content: '模拟学习正文\n请依次验证开始学习、完成学习、收藏与取消收藏。', content_url: null,
}))
const progress = new Map<number, ProgressStatus>(), favorites = new Set<number>()
const receipts = new Map<string, unknown>()
http.defaults.adapter = async (config) => {
  const url = config.url ?? '', params = config.params ?? {}
  let data: unknown
  if (url === '/resources') {
    const items = resources.filter((item) => (!params.q || item.title.includes(params.q)) && (!params.category_code || item.category_code === params.category_code))
    data = { items: items.slice((params.page - 1) * params.page_size, params.page * params.page_size), total: items.length, page: params.page, page_size: params.page_size }
  } else if (url === '/users/me/progress') {
    data = { items: [{ resource_id: params.resource_id, status: progress.get(params.resource_id) ?? 'not_started', first_started_at: null, completed_at: null, updated_at: null }], total: 1, page: 1, page_size: 1 }
  } else if (url === '/users/me/favorites') {
    const items = [...favorites].map((resource_id) => ({ resource_id, created_at: '2026-10-05T00:00:00' }))
    data = { items, total: items.length, page: 1, page_size: 100 }
  } else {
    const match = url.match(/^\/resources\/(\d+)(?:\/(view|start|complete|favorite))?$/)
    if (!match) throw new Error('Unexpected harness request')
    const id = Number(match[1]), action = match[2]
    if (!action) data = resources.find((item) => item.id === id)
    else {
      const payload = JSON.parse(config.data)
      if (receipts.has(payload.event_uuid)) data = receipts.get(payload.event_uuid)
      else {
        if (action === 'start') progress.set(id, 'in_progress')
        if (action === 'complete') progress.set(id, 'completed')
        if (action === 'favorite') { if (config.method === 'delete') favorites.delete(id); else favorites.add(id) }
        data = { id: receipts.size + 1, event_uuid: payload.event_uuid, is_effective: 1 }
        receipts.set(payload.event_uuid, data)
      }
    }
  }
  return { config, data, status: 200, statusText: 'OK', headers: {} }
}
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', name: 'home', component: HomeView, meta: { requiresAuth: true } },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/resources', name: 'resources', component: ResourcesView, meta: { requiresAuth: true } },
  { path: '/resources/:id', name: 'resource-detail', component: ResourceDetailView, meta: { requiresAuth: true } },
] })
router.beforeEach(createAuthGuard(auth))
await router.push('/resources')
createApp(App).use(pinia).use(router).mount('#app')
