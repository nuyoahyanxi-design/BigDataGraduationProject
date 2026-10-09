import { request } from './http'
import type { RecommendationAlgorithm, RecommendationsResponse } from '@/types/recommendations'
export const getRecommendations = (algorithm: RecommendationAlgorithm = 'content_v1') =>
  request<RecommendationsResponse>({ url: '/recommendations/me', params: { algorithm } })
