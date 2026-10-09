import { request } from './http'
import type { AICapabilities, AIQuestion, AIRecord, AIHistory } from '@/types/assistant'
export const getAICapabilities = () => request<AICapabilities>({ method: 'get', url: '/ai/capabilities' })
export const askAI = (data: AIQuestion) => request<AIRecord>({ method: 'post', url: '/ai/questions', data, timeout: 60000 })
export const getAIQuestion = (uuid: string) => request<AIRecord>({ method: 'get', url: `/ai/questions/${encodeURIComponent(uuid)}` })
export const getAIHistory = (page = 1) => request<AIHistory>({ method: 'get', url: '/ai/history', params: { page, page_size: 20 } })
