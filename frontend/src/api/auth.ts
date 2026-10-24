import { request } from './http'
import type { Credentials, TokenResponse, User } from '@/types/auth'
export const login = (credentials: Credentials) =>
  request<TokenResponse>({ method: 'POST', url: '/auth/login', data: credentials, skipAuth: true })
export const getCurrentUser = () => request<User>({ method: 'GET', url: '/users/me' })

export const getCaptcha = () => request<import('@/types/auth').Captcha>({ method:'GET',url:'/auth/captcha',skipAuth:true })
export const registerAccount = (data: Credentials) => request<import('@/types/auth').RecoveryResult>({method:'POST',url:'/auth/register',data,skipAuth:true})
export const resetPassword = (data: Credentials & {recovery_code:string}) => request<import('@/types/auth').RecoveryResult>({method:'POST',url:'/auth/reset-password',data,skipAuth:true})
export const generateRecoveryCode = (password:string) => request<import('@/types/auth').RecoveryResult>({method:'POST',url:'/auth/recovery-code',data:{password}})
