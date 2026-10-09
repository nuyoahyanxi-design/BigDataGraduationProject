import { request } from './http'
import type { Page, ResourceSummary, ResourceDetail, ListQuery, Progress, Favorite, EventReceipt, EventPayload, LearningAction } from '@/types/resources'
export const listResources = (params: ListQuery) => request<Page<ResourceSummary>>({ url: '/resources', params })
export const getResource = (id: number) => request<ResourceDetail>({ url: `/resources/${id}` })
export const getProgress = (id: number) => request<Page<Progress>>({ url: '/users/me/progress', params: { resource_id: id, page: 1, page_size: 1 } })
export const getFavorites = (page = 1) => request<Page<Favorite>>({ url: '/users/me/favorites', params: { page, page_size: 100 } })
export async function isFavorited(id: number) {
  let page = 1
  while (true) {
    const result = await getFavorites(page)
    if (result.items.some((item) => item.resource_id === id)) return true
    if (result.items.length === 0 || page * result.page_size >= result.total) return false
    page += 1
  }
}
export async function getLearningState(id: number) {
  const [progress, favorite] = await Promise.all([getProgress(id), isFavorited(id)])
  const item = progress.items.find((item) => item.resource_id === id)
  if (!item) throw new Error('学习状态响应缺失，请重新查询')
  return { progress: item.status, favorite }
}
export const sendLearningEvent = (id: number, action: LearningAction, data: EventPayload) =>
  request<EventReceipt>({ url: `/resources/${id}/${action === 'unfavorite' ? 'favorite' : action}`, method: action === 'unfavorite' ? 'DELETE' : 'POST', data })
