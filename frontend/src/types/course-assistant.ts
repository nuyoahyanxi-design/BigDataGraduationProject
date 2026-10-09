import type { AIRecord } from './assistant'
export interface CourseReference { course_name: string; chapter_name: string; chapter_id: number; position: number }
export interface CourseAIRecord extends AIRecord {
  course_id: number; course_title: string | null; references: CourseReference[]; retrieval_version: string
}
export interface CourseAIQuestion { request_uuid: string; question: string; chapter_id: number | null; consent_version: string }
export interface CourseAIHistory { items: CourseAIRecord[]; total: number; page: number; page_size: number }
