import type { ResourceSummary } from './resources'
export interface AdminCourseSummary extends ResourceSummary { chapter_count:number }
import type { Chapter } from './courses'
import { safeVideoAsset } from './courses'
export interface ChapterWrite {
  title:string; position:number; content:string; knowledge_tags:string[]; learning_objectives:string[]
  example_code:string|null; exercises:string[]; video_url:string|null; video_name:string|null
  video_cover:string|null; video_duration_seconds:number|null; video_position:number
}
export interface ChapterForm extends Omit<ChapterWrite,'knowledge_tags'|'learning_objectives'|'exercises'> {
  knowledge_tags:string; learning_objectives:string; exercises:string
}
export function chapterForm(chapter?:Chapter,position=1):ChapterForm {
  return {title:chapter?.title??'',position:chapter?.position??position,content:chapter?.content??'',
    knowledge_tags:chapter?.knowledge_tags.join(', ')??'',learning_objectives:chapter?.learning_objectives?.join('\n')??'',
    example_code:chapter?.example_code??null,exercises:chapter?.exercises?.join('\n')??'',
    video_url:chapter?.video_url??null,video_name:chapter?.video_name??null,video_cover:chapter?.video_cover??null,
    video_duration_seconds:chapter?.video_duration_seconds??null,video_position:chapter?.video_position??1}
}
const lines=(text:string)=>text.split(/\r?\n/).map(t=>t.trim()).filter(Boolean)
export function chapterPayload(form:ChapterForm):ChapterWrite {
  return {title:form.title.trim(),position:form.position,content:form.content.trim(),
    knowledge_tags:form.knowledge_tags.split(/[,，\n]/).map(t=>t.trim()).filter(Boolean),
    learning_objectives:lines(form.learning_objectives),example_code:form.example_code?.trim()||null,
    exercises:lines(form.exercises),video_url:form.video_url?.trim()||null,video_name:form.video_name?.trim()||null,
    video_cover:form.video_cover?.trim()||null,video_duration_seconds:form.video_duration_seconds,video_position:form.video_position}
}
export function validateChapter(form:ChapterForm):string {
  const p=chapterPayload(form)
  if(!p.title || p.title.length>200)return '章节标题必填，最多200字'
  if(!Number.isInteger(p.position)||p.position<1||p.position>1000)return '排序须为1到1000的整数，且不能重复'
  if(!p.content || p.content.length>100000)return 'Markdown正文必填，最多100000字'
  if(p.knowledge_tags.length>20 || new Set(p.knowledge_tags).size!==p.knowledge_tags.length || p.knowledge_tags.some(t=>t.length>50))return '知识点标签须不重复，最多20个，每个最多50字'
  if([p.learning_objectives,p.exercises].some(items=>items.length>8 || items.some(t=>t.length>1000)))return '教学目标和练习各最多8项，每项最多1000字'
  if(p.example_code && p.example_code.length>10000)return '示例代码最多10000字'
  if(p.video_url && !safeVideoAsset(p.video_url))return '视频仅支持本地/videos/下的MP4/WebM或/demo/video.mp4占位'
  return ''
}
