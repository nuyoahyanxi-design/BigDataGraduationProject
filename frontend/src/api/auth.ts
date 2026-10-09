import { request } from './http'
import type { Credentials, TokenResponse, User } from '@/types/auth'
export const login = (credentials: Credentials) =>
  request<TokenResponse>({ method: 'POST', url: '/auth/login', data: credentials, skipAuth: true })
export const getCurrentUser = () => request<User>({ method: 'GET', url: '/users/me' })
