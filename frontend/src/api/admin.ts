import { request } from './http'
import type { Page, ResourceSummary, ResourceDetail } from '@/types/resources'
import type { AdminUser, BatchList, ResourceWrite } from '@/types/admin'
export const listAdminUsers=(page=1)=>request<Page<AdminUser>>({url:'/admin/users',params:{page,page_size:20}})
export const getAdminBatches=()=>request<BatchList>({url:'/admin/batches'})
export const listAdminResources=(page=1,q='',status='all')=>request<Page<ResourceSummary>>({url:'/resources',params:{page,page_size:10,status,...(q.trim()?{q:q.trim()}: {})}})
export const createResource=(data:ResourceWrite)=>request<ResourceDetail>({url:'/resources',method:'POST',data})
export const updateResource=(id:number,data:ResourceWrite)=>request<ResourceDetail>({url:`/resources/${id}`,method:'PUT',data})
export const changeResourceStatus=(id:number,status:'published'|'offline')=>request<ResourceDetail>({url:`/resources/${id}/status`,method:'PATCH',data:{status}})
