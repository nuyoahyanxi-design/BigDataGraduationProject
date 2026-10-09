import { request } from './http'
import type { Page } from '@/types/resources'
import type { ChapterWrite, AdminCourseSummary } from '@/types/admin-courses'
export const listAdminCourses = (page=1,q='',status='all') => request<Page<AdminCourseSummary>>({url:'/admin/courses',params:{page,page_size:10,status,...(q.trim()?{q:q.trim()}:{})}})
export const createChapter = (id:number,data:ChapterWrite) => request<ChapterWrite & {id:number;resource_id:number}>({url:`/resources/${id}/chapters`,method:'POST',data})
export const updateChapter = (id:number,chapter:number,data:ChapterWrite) => request<ChapterWrite & {id:number;resource_id:number}>({url:`/resources/${id}/chapters/${chapter}`,method:'PUT',data})
export const deleteChapter = (id:number,chapter:number) => request<void>({url:`/resources/${id}/chapters/${chapter}`,method:'DELETE'})
