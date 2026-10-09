import type { ResourceDetail } from './resources'
export interface AdminUser { id:number; username:string; role:'admin'|'learner'; status:'active'|'disabled'|'deleted'; created_at:string }
export interface BatchInfo { stage:string; batch_id:string|null; status:string; generated_at:string|null; as_of_utc:string|null; data_count:number|null; count_label:string; source:string; message:string|null }
export interface BatchList { items:BatchInfo[]; scope:string }
export type ResourceWrite=Pick<ResourceDetail,'title'|'resource_type'|'category_code'|'tags'|'difficulty'|'summary'|'content'|'content_url'|'source_name'|'license_note'>
export const controlledTags=['python','java','sql','mysql','spark','big-data','data-analysis','machine-learning','web-development','algorithms','rdd','pyspark','hadoop','hdfs','ml','大数据','数据库']
export const statusNames={draft:'草稿',published:'已发布',offline:'已下架',deleted:'已删除'}
export function newResource():ResourceWrite { return {title:'',resource_type:'document',category_code:'data-engineering',tags:[],difficulty:1,summary:'',content:null,content_url:null,source_name:null,license_note:null} }
export function resourcePayload(value:ResourceWrite):ResourceWrite {
  const nullable=(text:string|null)=>text?.trim() || null
  return {title:value.title.trim(),resource_type:value.resource_type,category_code:value.category_code,tags:[...value.tags],difficulty:value.difficulty,summary:value.summary.trim(),
    content:nullable(value.content),content_url:nullable(value.content_url),source_name:nullable(value.source_name),license_note:nullable(value.license_note)}
}
export function validateResource(value:ResourceWrite) {
  if(!value.title.trim() || value.title.length>200) return '标题必填，最多200字'
  if(!value.summary.trim() || value.summary.length>1000) return '简介必填，最多1000字'
  if(value.tags.length>10 || new Set(value.tags).size!==value.tags.length || value.tags.some(t=>!controlledTags.includes(t))) return '请选择不重复的受控标签'
  if(value.content_url && !/^https?:\/\//i.test(value.content_url)) return '外链必须使用HTTP或HTTPS'
  return ''
}
export function utcTime(value:string|null) {
  if(!value) return '未记录'
  const iso=value.replace(' ','T'); const stamp=/(?:Z|[+-]\d{2}:\d{2})$/i.test(iso)?iso:iso+'Z'
  return new Date(stamp).toLocaleString('zh-CN',{timeZone:'UTC',hour12:false})+' UTC'
}

