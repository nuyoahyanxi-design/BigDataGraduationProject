import { createRouter, createWebHistory } from 'vue-router'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'
import { createAuthGuard } from './auth-guard'
export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: to => /^admin-(course|chapter)/.test(String(to.name)) ? {left:0,top:0} : false,
  routes: [
    { path: '/admin/courses/new', name: 'admin-course-create', component: () => import('@/views/AdminCourseEditView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/admin/courses/:id/edit', name: 'admin-course-edit', component: () => import('@/views/AdminCourseEditView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/admin/courses/:id/chapters', name: 'admin-course-chapters', component: () => import('@/views/AdminChapterListView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/admin/courses/:courseId/chapters/new', name: 'admin-chapter-create', component: () => import('@/views/AdminChapterEditView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/admin/courses/:courseId/chapters/:chapterId/edit', name: 'admin-chapter-edit', component: () => import('@/views/AdminChapterEditView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },

    { path: '/admin/courses', name: 'admin-courses', component: () => import('@/views/AdminCoursesView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/resources/:id/learn', name: 'course-learning', component: () => import('@/views/CourseLearningView.vue'), meta: { requiresAuth: true } },
    { path: '/assistant', name: 'assistant', component: () => import('@/views/AiAssistantView.vue'), meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { requiresAuth: true, roles: ['admin'], forbiddenRoute: 'forbidden' } },
    { path: '/403', name: 'forbidden', component: () => import('@/views/ForbiddenView.vue'), meta: { requiresAuth: true } },
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/resources', name: 'resources', component: () => import('@/views/ResourcesView.vue'), meta: { requiresAuth: true } },
    { path: '/recommendations', name: 'recommendations', component: () => import('@/views/RecommendationsView.vue'), meta: { requiresAuth: true } },
    { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
    { path: '/resources/:id', name: 'resource-detail', component: () => import('@/views/ResourceDetailView.vue'), meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
router.beforeEach(createAuthGuard(useAuthStore(pinia)))

