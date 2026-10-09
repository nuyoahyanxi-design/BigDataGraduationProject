import { createPinia } from 'pinia'
import { vi } from 'vitest'
import { useAuthStore } from '../src/stores/auth'
import { configureAuthTransport } from '../src/api/http'

export function memoryStorage() {
  const values = new Map<string, string>()
  const storage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value) },
    removeItem: (key: string) => { values.delete(key) },
  }
  vi.stubGlobal('sessionStorage', storage)
  return storage
}
export function newSession() {
  const auth = useAuthStore(createPinia())
  configureAuthTransport({ getToken: () => { auth.expire(); return auth.token }, onUnauthorized: (token) => auth.invalidate(token) })
  return auth
}
