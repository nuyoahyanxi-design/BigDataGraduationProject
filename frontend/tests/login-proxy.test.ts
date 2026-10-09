import { afterEach, expect, it, vi } from 'vitest'
import { http } from '../src/api/http'
import { login } from '../src/api/auth'
import viteConfig from '../vite.config'
const original = http.defaults.adapter
afterEach(() => { http.defaults.adapter = original; vi.unstubAllEnvs() })
it('登录通过Axios api前缀访问既有后端认证路径', async () => {
  http.defaults.adapter = async config => {
    expect(config.method).toBe('post')
    expect(http.getUri(config)).toBe('/api/auth/login')
    expect(config.skipAuth).toBe(true)
    expect(config.headers.has('Authorization')).toBe(false)
    return { config, status: 200, statusText: 'OK', headers: {}, data: { access_token: 'test-only', token_type: 'bearer', expires_in: 60 } }
  }
  await login({ username: 'test-only', password: 'test-only' })
})
async function config() {
  if (typeof viteConfig !== 'function') throw new Error('Expected Vite config factory')
  return viteConfig({ command: 'serve', mode: 'test' })
}
it('未提供代理变量时仍代理/api且不重写认证路径', async () => {
  vi.stubEnv('API_PROXY_TARGET', '')
  const result = await config()
  expect(result.server?.proxy?.['/api']).toMatchObject({ target: 'http://127.0.0.1:8000', changeOrigin: true })
  expect(result.server?.proxy?.['/api']).not.toHaveProperty('rewrite')
})
it('保留显式后端代理地址覆盖', async () => {
  vi.stubEnv('API_PROXY_TARGET', 'http://127.0.0.1:18765')
  expect((await config()).server?.proxy?.['/api']).toMatchObject({ target: 'http://127.0.0.1:18765' })
})
