import type { RouteLocationNormalized } from 'vue-router'
import type { useAuthStore } from '@/stores/auth'

export function createAuthGuard(auth: ReturnType<typeof useAuthStore>) {
  return async (to: Pick<RouteLocationNormalized, 'meta' | 'name'>) => {
    try { await auth.restore() } catch { /* login page exposes retry notice */ }
    if (to.meta.requiresAuth && !auth.authenticated) return { name: 'login' }
    if (Array.isArray(to.meta.roles) && !to.meta.roles.includes(auth.role)) return to.meta.forbiddenRoute ? { name: String(to.meta.forbiddenRoute) } : { name: 'home', query: { notice: 'dashboard-forbidden' } }
    if (to.name === 'login' && auth.authenticated) return { name: 'home' }
    return true
  }
}
