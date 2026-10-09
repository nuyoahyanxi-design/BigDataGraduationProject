import { afterEach, expect, it } from 'vitest'
import { http } from '../src/api/http'
import { CourseAssistant } from '../src/services/course-assistant'
import { askCourseAI, getCourseAIQuestion } from '../src/api/course-assistant'
import { AxiosError } from 'axios'
const original=http.defaults.adapter
afterEach(()=>{http.defaults.adapter=original})
const caps={enabled:true,ready:true,consent_version:'agnes-external-v1',max_question_chars:2000,notice:'确认外发'}
const record={request_uuid:'fixture',question:'问题',mode:'resource',resource_id:1071,resource_version:1,answer:'答案',status:'succeeded',
  source:'课程资料增强回答',model:'test',error_code:null,created_at:'2026-10-05',finished_at:'2026-10-05',course_id:1071,course_title:'MySQL',
  references:[{course_name:'MySQL',chapter_name:'SELECT查询',chapter_id:3,position:3}],retrieval_version:'text-course-v1'}
function setup(){
  const calls:{url:string;method:string;data:any}[]=[]
  http.defaults.adapter=async config=>{
    calls.push({url:config.url!,method:config.method!,data:config.data?JSON.parse(config.data):null})
    const data=config.url?.endsWith('capabilities')?caps:config.url?.endsWith('history')?{items:[record],total:1,page:1,page_size:20}:record
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  return calls
}
it('默认课程模式并冻结当前课程和章节，只调用已有相对/api链路',async()=>{
  const calls=setup(),controller=new CourseAssistant(1071,()=> 'session')
  await controller.load();expect(controller.state.mode).toBe('course')
  controller.state.question='SELECT条件';controller.state.consent=true
  await controller.send(3)
  expect(calls.find(c=>c.method==='post')).toMatchObject({url:'/resources/1071/ai/questions',data:{question:'SELECT条件',chapter_id:3,consent_version:'agnes-external-v1'}})
  expect(controller.state.answer && 'references' in controller.state.answer?controller.state.answer.references:[]).toEqual(record.references)
})
it('通用模式继续使用原askAI，不发送课程或章节内容',async()=>{
  const calls=setup(),controller=new CourseAssistant(1071,()=> 'session');await controller.load()
  controller.state.consent=true;controller.mode('general');expect(controller.state.consent).toBe(false)
  controller.state.question='通用知识';controller.state.consent=true;await controller.send(3)
  expect(calls.find(c=>c.method==='post')).toMatchObject({url:'/ai/questions',data:{mode:'general',resource_id:null}})
  expect(calls.find(c=>c.method==='post')?.data).not.toHaveProperty('chapter_id')
})
it('未确认外发不发送，空问题不发送',async()=>{
  const calls=setup(),controller=new CourseAssistant(1,()=> 'session');await controller.load()
  controller.state.question='Spark';await controller.send();expect(controller.state.error).toContain('确认')
  controller.state.consent=true;controller.state.question=' ';await controller.send()
  expect(calls.filter(c=>c.method==='post')).toHaveLength(0)
})
it('组件离开或登录变化时不接收迟到的回答',async()=>{
  let resolve!:(value:any)=>void,token='first'
  http.defaults.adapter=async config=>new Promise(r=>{resolve=(data)=>r({config,status:200,statusText:'OK',headers:{},data})})
  const controller=new CourseAssistant(1,()=>token);controller.state.capabilities=caps;controller.state.question='问';controller.state.consent=true
  const pending=controller.send();await new Promise(r=>setTimeout(r,0));token='changed';controller.dispose();resolve(record);await pending
  expect(controller.state.answer).toBeUndefined();expect(controller.state.records).toEqual([])
})
it('未知资料引用为空，保持服务端说明不自行猜章节',async()=>{
  http.defaults.adapter=async config=>({config,status:200,statusText:'OK',headers:{},data:{...record,references:[],answer:'当前课程资料中未找到相关内容，以下回答基于通用知识。'}})
  expect((await askCourseAI(1071,{request_uuid:'x',question:'不存在知识',chapter_id:null,consent_version:'agnes-external-v1'})).references).toEqual([])
})
it('记录状态查询使用课程内路由与编码UUID',async()=>{
  const calls=setup();await getCourseAIQuestion(1071,'a/b')
  expect(calls[0].url).toBe('/resources/1071/ai/questions/a%2Fb')
})
it('外发未批准时友好说明，通用回答不被课程历史404覆盖',async()=>{
  http.defaults.adapter=async config=>{
    if(config.url==='/ai/questions')return {config,status:200,statusText:'OK',headers:{},data:{...record,mode:'general'}}
    throw new AxiosError('fixture','ERR_BAD_REQUEST',config,undefined,{config,status:404,statusText:'Not Found',headers:{},data:{}})
  }
  const controller=new CourseAssistant(1071,()=> 'session');controller.state.capabilities=caps
  controller.state.question='问题';controller.state.consent=true;await controller.send()
  expect(controller.state.error).toContain('尚未批准资料外发');expect(controller.state.error).not.toContain('HTTP')
  controller.mode('general');controller.state.consent=true;await controller.send()
  expect(controller.state.answer?.answer).toBe('答案');expect(controller.state.error).toBe('')
})
