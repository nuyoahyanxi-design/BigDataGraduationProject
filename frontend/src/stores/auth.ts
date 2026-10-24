import { defineStore } from 'pinia'
import { login, getCurrentUser } from '@/api/auth'
import { ApiError } from '@/api/http'
import type { Credentials, User } from '@/types/auth'
export const SESSION_KEY = 'spark-learning.auth.v1'
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '', user: null as User | null, expiresAt: 0, restored: false,
    notice: '', storageWarning: '', remember: false,
  }),
  getters: {
    role: (state) => state.user?.role ?? null,
    authenticated: (state) => Boolean(state.token && state.user && state.expiresAt > Date.now()),
  },
  actions: {
    clear(message = '') {
      this.token = ''; this.user = null; this.expiresAt = 0
      this.restored = true; this.notice = message; this.storageWarning = ''
      try { sessionStorage.removeItem(SESSION_KEY) } catch { /* memory session still cleared */ }
      try { localStorage.removeItem(SESSION_KEY) } catch { /* optional persistent session */ }
      this.remember = false
    },
    expire() {
      if (this.token && this.expiresAt <= Date.now()) {
        this.clear('登录已过期，请重新登录')
        return true
      }
      return false
    },
    invalidate(requestToken: string) {
      if (requestToken === this.token) this.clear('登录已失效，请重新登录')
    },
    persist() {
      try {
        if (this.remember) {
          localStorage.setItem(SESSION_KEY, JSON.stringify({ token: this.token, expiresAt: this.expiresAt }))
          sessionStorage.removeItem(SESSION_KEY)
        } else {
          sessionStorage.setItem(SESSION_KEY, JSON.stringify({ token: this.token, expiresAt: this.expiresAt }))
          try { localStorage.removeItem(SESSION_KEY) } catch { /* optional persistent session */ }
        }
        this.storageWarning = ''
      } catch { this.storageWarning = '浏览器无法保存会话，刷新后需要重新登录' }
    },
    async restore() {
      if (this.restored && this.user) { this.expire(); return }
      if (!this.token) {
        try {
          let raw = sessionStorage.getItem(SESSION_KEY)
          if (!raw) {
            try { raw = localStorage.getItem(SESSION_KEY); this.remember = Boolean(raw) } catch { /* session storage still works */ }
          }
          if (raw) {
            const value: unknown = JSON.parse(raw)
            if (value && typeof value === 'object' && 'token' in value && 'expiresAt' in value
              && typeof value.token === 'string' && value.token.length > 0
              && typeof value.expiresAt === 'number' && Number.isFinite(value.expiresAt)) {
              this.token = value.token; this.expiresAt = value.expiresAt
            } else this.clear()
          }
        } catch { this.clear() }
      }
      this.restored = true
      if (!this.token || this.expire()) return
      const pendingToken = this.token
      try {
        const user = await getCurrentUser()
        if (pendingToken === this.token && !this.expire()) { this.user = user; this.notice = '' }
      } catch (error) {
        if (pendingToken !== this.token) return
        if (error instanceof ApiError && error.status === 401) this.clear('登录已失效，请重新登录')
        else {
          this.user = null
          this.notice = '暂时无法确认登录状态，请重试或重新登录'
          throw error
        }
      }
    },
    async signIn(credentials: Credentials) {
      this.clear()
      const result = await login(credentials)
      this.remember = Boolean(credentials.remember_me)
      this.token = result.access_token
      this.expiresAt = Date.now() + result.expires_in * 1000
      try {
        const user = await getCurrentUser()
        if (!this.token || this.expire()) throw new ApiError('登录已失效，请重新登录', 401)
        this.user = user; this.persist()
      } catch (error) { this.clear(); throw error }
    },
  },
})
