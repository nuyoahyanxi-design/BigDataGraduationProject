import { request } from './http'
import type { DashboardResponse } from '@/types/dashboard'
export const getDashboard = () => request<DashboardResponse>({ url: '/dashboard/overview' })

export const getPublicEducationDashboard = () => request<import('@/types/public-education').PublicEducationResponse>({ url: '/dashboard/public-education' })
