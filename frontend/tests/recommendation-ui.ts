// Isolated browser harness. Not imported by the production entry/build.
import { createApp } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '../src/App.vue'
import RecommendationsView from '../src/views/RecommendationsView.vue'
import ResourceDetailView from '../src/views/ResourceDetailView.vue'
import ResourcesView from '../src/views/ResourcesView.vue'
import HomeView from '../src/views/HomeView.vue'
import LoginView from '../src/views/LoginView.vue'
import { pinia } from '../src/stores'
import { useAuthStore } from '../src/stores/auth'
import { createAuthGuard } from '../src/router/auth-guard'
import { http } from '../src/api/http'
import 'element-plus/dist/index.css'
import '../src/styles/base.css'

const auth = useAuthStore(pinia)
auth.token = 'invalid-component-test-placeholder'; auth.expiresAt = Date.now() + 3600000; auth.restored = true
auth.user = { id: 1, username: 'component_test_learner', nickname: null, role: 'learner', status: 'active', interest_tags: ['python', 'spark'], created_at: '', updated_at: '' }
const time = '2026-10-05T00:00:00Z'
const profile = { batch_id: 'component_profile_fixture', generated_at: time, as_of_utc: time,
  interest_weights: { python: 0.7, spark: 0.3 }, evidence: 'observed', active_days: 3,
  event_counts: { resource_view: 5, learning_start: 2, learning_complete: 1, favorite_add: 2, favorite_remove: 1 },
  started_resources: 2, completed_resources: 1, completion_rate: 0.5 }
const resource = { id: 100, title: 'Spark 学习行为分析（模拟资源）', summary: '推荐展示组件验证使用的模拟简介。', tags: ['spark', 'python'], difficulty: 2,
  resource_type: 'document', category_code: 'data-engineering', source_name: '组件测试', license_note: '仅测试', status: 'published',
  version_no: 1, created_by: 1, published_at: time, created_at: time, updated_at: time,
  content: '模拟资源详情正文。', content_url: null }
const empty = new URLSearchParams(location.search).has('empty')
http.defaults.adapter = async (config) => {
  let data: unknown
  if (config.url === '/recommendations/me') {
    const algorithm = config.params.algorithm
    data = { batch_id: 'component_recommendation_fixture', generated_at: time, as_of_utc: time, algorithm,
      explicit_interest_tags: ['python', 'spark'], profile: empty ? null : profile,
      items: empty ? [] : [{ resource_id: 100, resource, algorithm, score: algorithm === 'content_v1' ? '0.928476690885' : '12.000000000000', rank: 1,
        reason: algorithm === 'content_v1' ? '与你的行为兴趣画像匹配：python、spark' : '按历史浏览、开始、完成和收藏行为热度推荐' }],
      message: empty ? '暂无可展示的推荐，可先浏览学习资源并等待下一批生成' : null }
  } else if (config.url === '/resources/100') data = resource
  else if (config.url === '/users/me/progress') data = { items: [{ resource_id: 100, status: 'not_started' }], total: 1, page: 1, page_size: 1 }
  else if (config.url === '/users/me/favorites') data = { items: [], total: 0, page: 1, page_size: 100 }
  else if (config.url === '/resources/100/view') data = { is_effective: 1 }
  else if (config.url === '/resources') data = { items: [resource], total: 1, page: 1, page_size: 12 }
  else throw new Error('Unexpected harness request')
  return { config, data, status: 200, statusText: 'OK', headers: {} }
}
const router = createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', name: 'home', component: HomeView, meta: { requiresAuth: true } },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/resources', name: 'resources', component: ResourcesView, meta: { requiresAuth: true } },
  { path: '/resources/:id', name: 'resource-detail', component: ResourceDetailView, meta: { requiresAuth: true } },
  { path: '/recommendations', name: 'recommendations', component: RecommendationsView, meta: { requiresAuth: true } },
] })
router.beforeEach(createAuthGuard(auth)); await router.push('/recommendations')
createApp(App).use(pinia).use(router).mount('#app')
