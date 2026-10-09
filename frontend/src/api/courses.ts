import { request } from './http'
import type { Course, ChapterEventType, ChapterReceipt } from '@/types/courses'
export const getCourse = (id: number) => request<Course>({ method: 'get', url: `/resources/${id}/course` })
export const recordChapter = (id: number, chapterId: number, data: { event_uuid: string; event_type: ChapterEventType; playback_seconds?: number }) =>
  request<ChapterReceipt>({ method: 'post', url: `/resources/${id}/chapters/${chapterId}/events`, data })
