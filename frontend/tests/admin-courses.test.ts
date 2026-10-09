import { afterEach, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'
import { http } from '../src/api/http'
import { listAdminCourses,createChapter,updateChapter,deleteChapter } from '../src/api/admin-courses'
import { AdminCourses } from '../src/services/admin-courses'
import { newResource, validateResource } from '../src/types/admin'
import { chapterForm,chapterPayload,validateChapter } from '../src/types/admin-courses'
import { createAuthGuard } from '../src/router/auth-guard'
import { memoryStorage,newSession } from './helpers'
const original=http.defaults.adapter
afterEach(()=>{http.defaults.adapter=original;vi.unstubAllGlobals()})
const form=()=>({...chapterForm(),title:'RDD',content:'# 教学',knowledge_tags:'Spark, RDD',learning_objectives:'理解RDD\n解释Lineage',exercises:'创建RDD',video_url:'/demo/video.mp4',example_code:'print(1)'})
it('课程列表与章节CRUD固定接口参数',async()=>{
  const calls: any[]=[]
  http.defaults.adapter=async config=>{calls.push({url:config.url,method:config.method,params:config.params,data:config.data?JSON.parse(config.data):undefined});return {config,status:200,statusText:'OK',headers:{},data:{}}}
  await listAdminCourses(2,' Spark ','offline')
  await createChapter(42,chapterPayload(form()));await updateChapter(42,7,chapterPayload(form()));await deleteChapter(42,7)
  expect(calls[0]).toMatchObject({url:'/admin/courses',params:{page:2,status:'offline',q:'Spark'}})
  expect(calls[1]).toMatchObject({url:'/resources/42/chapters',method:'post',data:{learning_objectives:['理解RDD','解释Lineage'],video_url:'/demo/video.mp4'}})
  expect(calls[2]).toMatchObject({url:'/resources/42/chapters/7',method:'put'})
  expect(calls[3]).toMatchObject({url:'/resources/42/chapters/7',method:'delete'})
})
it('章节序列化只提交允许字段，并保留原视频元数据',()=>{
  const value={...form(),id:7,resource_id:406,completed:true,video_name:'教程',video_cover:'/covers/demo.png',video_duration_seconds:60,video_position:2}
  const payload=chapterPayload(value)
  expect(payload).not.toHaveProperty('id');expect(payload).not.toHaveProperty('completed');expect(payload).not.toHaveProperty('resource_id')
  expect(payload).toMatchObject({knowledge_tags:['Spark','RDD'],video_duration_seconds:60,video_position:2})
  expect(validateChapter(value)).toBe('')
})
it.each([
  {title:' '},{position:0},{position:1.5},{content:''},{knowledge_tags:'RDD,RDD'},
  {video_url:'https://example.com/video.mp4'},{video_url:'/videos/../bad.mp4'},
  {learning_objectives:Array(9).fill('目标').join('\n')},{example_code:'x'.repeat(10001)},
])('无效章节输入阻止提交 %j',changes=>expect(validateChapter({...form(),...changes})).not.toBe(''))
for(const role of ['anonymous','learner','admin'] as const)it(`课程管理员入口权限 ${role}`,async()=>{
  memoryStorage();const auth=newSession()
  if(role!=='anonymous'){auth.token='test-only';auth.expiresAt=Date.now()+60000;auth.restored=true;auth.user={id:1,username:'fixture',nickname:null,role,status:'active',interest_tags:[],created_at:'',updated_at:''}}
  const result=await createAuthGuard(auth)({name:'admin-courses',meta:{requiresAuth:true,roles:['admin'],forbiddenRoute:'forbidden'}})
  expect(result).toEqual(role==='anonymous'?{name:'login'}:role==='learner'?{name:'forbidden'}:true)
})
it('课程及章节完整维护流程，包括二次确认删除',async()=>{
  const row:any={id:42,title:'旧课程',summary:'简介',status:'draft',resource_type:'course',category_code:'data-engineering',tags:['spark'],difficulty:1,content:'介绍',content_url:null,source_name:null,license_note:null}
  let chapters:any[]=[];const writes:string[]=[]
  http.defaults.adapter=async config=>{
    let data:any={};const body=config.data?JSON.parse(config.data):{}
    if(config.method==='get' && config.url==='/admin/courses')data={items:[{...row}],total:1,page:1,page_size:10}
    else if(config.method==='get' && config.url==='/resources/42')data={...row}
    else if(config.url?.endsWith('/course'))data={resource_id:42,title:row.title,status:row.status,chapters:[...chapters]}
    else{
      writes.push(config.method+' '+config.url)
      if(config.url==='/resources'){Object.assign(row,body);data={...row}}
      else if(config.url==='/resources/42'){Object.assign(row,body);data={...row}}
      else if(config.url?.endsWith('/status')){row.status=body.status;data={...row}}
      else if(config.method==='post'){data={id:7,resource_id:42,...body};chapters=[data]}
      else if(config.method==='put'){data={id:7,resource_id:42,...body};chapters=[data]}
      else if(config.method==='delete')chapters=[]
    }
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  const admin=new AdminCourses();await admin.load()
  admin.addCourse();Object.assign(admin.state.courseForm,{title:'新课程',summary:'简介',tags:['spark'],content:'介绍',resource_type:'document'})
  await admin.saveCourse();expect(row.resource_type).toBe('course')
  await admin.editCourse(42);admin.state.courseForm.title='更新课程';await admin.saveCourse();expect(row.title).toBe('更新课程')
  await admin.status(admin.state.list!.items[0]!);expect(row.status).toBe('published')
  await admin.select(42);admin.editChapter();Object.assign(admin.state.chapterForm,form());await admin.saveChapter()
  expect(admin.state.course!.chapters).toHaveLength(1)
  admin.editChapter(admin.state.course!.chapters[0]);admin.state.chapterForm.content='# 修订';await admin.saveChapter()
  expect(chapters[0].content).toBe('# 修订')
  const count=writes.length;admin.askDelete(admin.state.course!.chapters[0]!);expect(writes).toHaveLength(count)
  await admin.confirmDelete();expect(admin.state.course!.chapters).toHaveLength(0)
  await admin.status(admin.state.list!.items[0]!);expect(row.status).toBe('offline')
})
it('服务器拒绝删除时保留确认目标，显示保护提示',async()=>{
  http.defaults.adapter=async config=>{throw new AxiosError('conflict','ERR_BAD_REQUEST',config,undefined,{config,status:409,statusText:'Conflict',headers:{},data:{detail:'frozen'}})}
  const admin=new AdminCourses();admin.state.course={resource_id:42,title:'课程',status:'published',course_status:'not_started',content:'',chapters:[]}
  admin.askDelete({id:7,title:'章节'} as any);await admin.confirmDelete()
  expect(admin.state.deleteTarget?.id).toBe(7);expect(admin.state.busy).toBe(false);expect(admin.state.error).toContain('已有学习记录')
})
it('保存失败保留表单且可重试，双击只写一次',async()=>{
  const admin=new AdminCourses();admin.state.course={resource_id:42,title:'课程',status:'draft',course_status:'not_started',content:'',chapters:[]}
  admin.editChapter();Object.assign(admin.state.chapterForm,form())
  let writes=0;let finish!:()=>void;const blocked=new Promise<void>(resolve=>{finish=resolve})
  http.defaults.adapter=async config=>{writes++;await blocked;throw new AxiosError('network','ERR_NETWORK',config)}
  const a=admin.saveChapter(),b=admin.saveChapter();finish();await Promise.all([a,b])
  expect(writes).toBe(1);expect(admin.state.chapterEditor).toBe(true);expect(admin.state.chapterForm.content).toBe('# 教学');expect(admin.state.busy).toBe(false)
})
it('排序冲突响应保留编辑输入',async()=>{
  const admin=new AdminCourses();admin.state.course={resource_id:42,title:'课程',status:'draft',course_status:'not_started',content:'',chapters:[]}
  admin.editChapter();Object.assign(admin.state.chapterForm,form())
  http.defaults.adapter=async config=>{throw new AxiosError('conflict','ERR_BAD_REQUEST',config,undefined,{config,status:409,statusText:'Conflict',headers:{},data:{}})}
  await admin.saveChapter();expect(admin.state.chapterEditor).toBe(true);expect(admin.state.error).toContain('排序可能重复')
})
it('编辑已有document教学资源时保留原类型',async()=>{
  const writes:any[]=[]
  http.defaults.adapter=async config=>{
    let data:any={items:[],total:0,page:1,page_size:10}
    if(config.url==='/resources/1071'&&config.method==='get')data={title:'MySQL数据库基础',summary:'简介',resource_type:'document',category_code:'databases',difficulty:1,tags:['mysql'],content:'介绍',content_url:null,source_name:null,license_note:null}
    if(config.method==='put'){writes.push(JSON.parse(config.data));data={id:1071,...writes[0]}}
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  const admin=new AdminCourses();await admin.editCourse(1071)
  admin.state.courseForm.title='MySQL数据库基础（修订）';await admin.saveCourse()
  expect(writes[0].resource_type).toBe('document')
})

it.each([
  ['spark','rdd','大数据'],['python','pyspark','spark'],['hadoop','hdfs','大数据'],['mysql','数据库'],['python','ml'],
])('正式课程现有标签可保留并编辑 %j', (...tags) => {
  expect(validateResource({...newResource(),title:'正式课程',summary:'简介',tags})).toBe('')
})
