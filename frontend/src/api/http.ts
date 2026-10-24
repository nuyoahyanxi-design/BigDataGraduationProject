import axios, { type AxiosRequestConfig } from 'axios'
declare module 'axios' {
  interface AxiosRequestConfig { skipAuth?: boolean; sessionToken?: string }
}
export class ApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly aiLimitSource?: string) { super(message); this.name = 'ApiError' }
}
interface AuthTransport { getToken: () => string; onUnauthorized: (token: string) => void }
let authTransport: AuthTransport | undefined
export function configureAuthTransport(transport: AuthTransport) { authTransport = transport }
const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 10000)
export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL?.trim() || '/api',
  timeout: Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 10000,
})
http.interceptors.request.use((config) => {
  const token = config.skipAuth ? '' : authTransport?.getToken()
  config.sessionToken = token || ''
  if (token) config.headers.set('Authorization', `Bearer ${token}`)
  else config.headers.delete('Authorization')
  return config
})
http.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      const token = error.config?.sessionToken
      if (status === 401 && token) authTransport?.onUnauthorized(token)
      const message = status === 401
        ? error.config?.skipAuth ? '用户名或密码错误' : '登录已失效，请重新登录'
        : status === 400 && error.config?.url?.includes('/auth/') ? (error.config.url.includes('reset-password') ? '验证码或恢复信息无效，请检查后重试' : '验证码错误或已过期，请刷新后重试')
        : status === 409 && error.config?.url?.includes('/auth/register') ? '该用户名已被使用，请更换用户名'
        : status === 429 ? '操作过于频繁，请稍后再试'
        : status === 422 ? '输入格式不符合要求'
        : status === 403 ? '没有访问权限'
        : status ? `服务请求失败（HTTP ${status}），请稍后重试`
        : error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '无法连接服务，请检查网络后重试'
      const source = error.response?.headers?.['x-ai-limit-source']
      const aiLimitSource = typeof source === 'string' && ['user_daily', 'global_daily', 'concurrency', 'provider_rate_limit'].includes(source) ? source : undefined
      return Promise.reject(new ApiError(message, status, aiLimitSource))
    }
    return Promise.reject(new ApiError('请求处理失败'))
  },
)
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await http.request<T>(config)
  return response.data
}
