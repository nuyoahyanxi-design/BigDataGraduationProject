import { request } from './http'
import type { CourseAIRecord, CourseAIQuestion, CourseAIHistory } from '@/types/course-assistant'
export const askCourseAI = (id: number, data: CourseAIQuestion) => request<CourseAIRecord>({method:'post', url:`/resources/${id}/ai/questions`,data,timeout:60000})
export const getCourseAIQuestion = (id: number, uuid: string) => request<CourseAIRecord>({method:'get',url:`/resources/${id}/ai/questions/${encodeURIComponent(uuid)}`})
export const getCourseAIHistory = (id: number, page=1) => request<CourseAIHistory>({method:'get',url:`/resources/${id}/ai/history`,params:{page,page_size:20}})
