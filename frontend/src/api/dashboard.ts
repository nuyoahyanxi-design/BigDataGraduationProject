import { request } from './http'
import type { DashboardResponse } from '@/types/dashboard'
export const getDashboard = () => request<DashboardResponse>({ url: '/dashboard/overview' })
