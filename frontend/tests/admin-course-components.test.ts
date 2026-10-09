import { afterEach, expect, it, vi } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, defineComponent, h, nextTick, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { createPinia } from 'pinia'
import { AxiosError } from 'axios'
import { http } from '../src/api/http'
import AdminCoursesView from '../src/views/AdminCoursesView.vue'
import AdminCourseEditView from '../src/views/AdminCourseEditView.vue'
import AdminChapterListView from '../src/views/AdminChapterListView.vue'
import AdminChapterEditView from '../src/views/AdminChapterEditView.vue'
const { push,replace,route } = vi.hoisted(() => ({ push:vi.fn(),replace:vi.fn(),route:{name:'admin-courses',params:{} as Record<string,string>,query:{} as Record<string,string>} }))
vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => ({ push,replace }) }))
vi.mock('element-plus', () => {
  const button = defineComponent({ setup(_, { slots, attrs }) { return () => h('button', attrs, slots.default?.()) } })
  const plain = defineComponent({ setup(_, { slots, attrs }) { return () => h('div', attrs, slots.default?.()) } })
  return { ElButton: button, ElTag: plain, ElAlert: plain, ElEmpty:plain, ElForm:plain, ElFormItem:plain, ElInput:plain, ElInputNumber:plain, ElOption:plain, ElPagination:plain, ElSelect:plain }
})
type Node = { text: string; type: string; children: Node[]; parent?: Node; props: Record<string, any> }
const node = (type: string, text = ''): Node => ({ type, text, children: [], props: {} })
const renderer = createRenderer<Node, Node>({
  createElement: type => node(type), createText: text => node('text', text), createComment: text => node('comment', text),
  setText: (n,t) => { n.text=t }, setElementText: (n,t) => { n.text=t; n.children=[] },
  parentNode: n => n.parent ?? null, nextSibling: n => n.parent?.children[n.parent.children.indexOf(n)+1] ?? null,
  patchProp: (n,k,_,v) => { n.props[k]=v },
  insert(n,p,anchor) { if(n.parent) n.parent.children.splice(n.parent.children.indexOf(n),1); n.parent=p; const i=anchor?p.children.indexOf(anchor):-1; p.children.splice(i<0?p.children.length:i,0,n) },
  remove(n) { if(n.parent) n.parent.children.splice(n.parent.children.indexOf(n),1) },
})
const flatten = (n: Node): Node[] => [n, ...n.children.flatMap(flatten)]
const text = (n: Node): string => n.text + n.children.map(text).join('')
function clientView(view: any) {
  const filename=view.__name
  const { descriptor }=parse(readFileSync(new URL(`../src/views/${filename}.vue`,import.meta.url),'utf8'))
  const script=compileScript(descriptor,{id:filename})
  const compiled=compileTemplate({source:descriptor.template!.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}})
  const code=compiled.code.replace(/import \{([\s\S]*?)\} from "vue"/,(_,helpers:string)=>`const {${helpers.replace(/ as /g, ': ')}}=Vue`).replace('export function render','function render')
  return {...view, render:new Function('Vue',ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText+';return render')(Vue)}
}
const original=http.defaults.adapter
let app:ReturnType<typeof renderer.createApp>|undefined
afterEach(()=>{app?.unmount();http.defaults.adapter=original;push.mockClear();replace.mockClear()})
const settle=async()=>{await new Promise(r=>setTimeout(r,25));await nextTick()}
const chapter=()=>({id:7,resource_id:42,title:'RDD章节',position:1,content:'# 正文',knowledge_tags:['RDD'],learning_objectives:['目标'],exercises:['练习'],example_code:'print(1)',video_url:'/demo/video.mp4',video_name:null,video_cover:null,video_duration_seconds:null,video_position:1,completed:false})
function backend(options:{frozen?:boolean;empty?:boolean;missing?:boolean;failSave?:boolean}={}){
  let chapters:any[]=options.empty?[]:[chapter()]
  const row:any={id:42,title:'示例课程',summary:'介绍',resource_type:'document',status:'draft',category_code:'data-engineering',tags:['spark','rdd'],difficulty:1,chapter_count:chapters.length,updated_at:'2026-10-05T12:00:00',content:'原课程正文',content_url:null,source_name:'原来源',license_note:'原许可'}
  const calls:{method:string;url:string;data:any}[]=[]
  http.defaults.adapter=async config=>{
    const body=config.data?JSON.parse(config.data):{}
    calls.push({method:config.method!,url:config.url!,data:body})
    let data:any={}
    const failure=(status:number)=>new AxiosError('fixture error','ERR_BAD_REQUEST',config,undefined,{config,status,statusText:'Error',headers:{},data:{}})
    if(options.missing)throw failure(404)
    if(options.failSave && config.method==='put')throw failure(409)
    if(config.url?.endsWith('/course'))data={resource_id:42,title:row.title,status:row.status,course_status:'not_started',chapters:chapters.map(ch=>({...ch}))}
    else if(config.method==='get' && config.url==='/admin/courses')data={items:[{...row,chapter_count:chapters.length}],total:1,page:1,page_size:10}
    else if(config.method==='get')data={...row}
    else{
      if(config.method==='delete' && options.frozen)throw failure(409)
      if(config.url==='/resources'||config.url==='/resources/42'){Object.assign(row,body);data={...row}}
      else if(config.url?.endsWith('/status')){Object.assign(row,body);data={...row}}
      else if(config.method==='post'||config.method==='put'){data={id:7,resource_id:42,...body};chapters=[data]}
      else if(config.method==='delete')chapters=[]
    }
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  return {calls,row,chapters:()=>chapters,writes:()=>calls.filter(c=>c.method!=='get')}
}
async function mount(view:any,name:string,params:Record<string,string>={}){
  app?.unmount();route.name=name;route.params=params;route.query={}
  const root=node('root')
  app=renderer.createApp(clientView(view));app.use(createPinia());app.provide(ssrContextKey,{modules:new Set()})
  app.component('RouterLink',defineComponent({setup(_,ctx){return()=>h('a',ctx.attrs,ctx.slots.default?.())}}))
  app.mount(root);await settle()
  const click=async(label:string)=>{const button=flatten(root).find(n=>n.type==='button'&&text(n)===label);expect(button).toBeDefined();button!.props.onClick();await settle()}
  const fill=(label:string,value:any)=>{const field=flatten(root).find(n=>n.props['aria-label']===label && n.props['onUpdate:modelValue']);expect(field).toBeDefined();field!.props['onUpdate:modelValue'](value)}
  return{root,click,fill}
}
it('课程列表只有列表，编辑/章节/创建按钮导航且不读取或展开编辑表单',async()=>{
  const fixture=backend();const{root,click}=await mount(AdminCoursesView,'admin-courses')
  expect(text(root)).toContain('章节数量 1');expect(text(root)).toContain('更新时间')
  expect(flatten(root).some(n=>n.props['aria-label']==='课程标题')).toBe(false)
  expect(text(root)).not.toContain('Markdown正文')
  await click('编辑课程');expect(push).toHaveBeenCalledWith({name:'admin-course-edit',params:{id:42}})
  await click('管理章节');expect(push).toHaveBeenCalledWith({name:'admin-course-chapters',params:{id:42}})
  await click('创建课程');expect(push).toHaveBeenCalledWith({name:'admin-course-create'})
  expect(fixture.calls.every(c=>c.method==='get'&&c.url==='/admin/courses')).toBe(true)
})
it('课程编辑直达URL加载，保存保留类型/正文/元数据，发布隐藏与返回有效',async()=>{
  const fixture=backend();const{click,fill}=await mount(AdminCourseEditView,'admin-course-edit',{id:'42'})
  fill('课程标题','修订课程');await click('保存课程')
  expect(fixture.writes()[0]).toMatchObject({method:'put',url:'/resources/42',data:{title:'修订课程',resource_type:'document',content:'原课程正文',source_name:'原来源',license_note:'原许可'}})
  await click('发布课程');expect(fixture.row.status).toBe('published')
  await click('隐藏课程');expect(fixture.row.status).toBe('offline')
  await click('返回课程列表');expect(push).toHaveBeenCalledWith({name:'admin-courses'})
})
it('课程创建成功跳转编辑URL，保留创建接口',async()=>{
  const fixture=backend();const{fill,click}=await mount(AdminCourseEditView,'admin-course-create')
  fill('课程标题','新课程');fill('课程简介','简介');fill('课程标签',['spark']);fill('课程介绍','介绍');await click('保存课程')
  expect(fixture.writes()[0]).toMatchObject({method:'post',url:'/resources',data:{resource_type:'course'}})
  expect(replace).toHaveBeenCalledWith({name:'admin-course-edit',params:{id:42},query:{saved:'1'}})
})
it('章节列表展示排序和视频地址，新增/编辑跳转独立页面',async()=>{
  backend();const{root,click}=await mount(AdminChapterListView,'admin-course-chapters',{id:'42'})
  expect(text(root)).toContain('排序号 1');expect(text(root)).toContain('/demo/video.mp4')
  expect(flatten(root).some(n=>n.props['aria-label']==='章节Markdown正文')).toBe(false)
  await click('新增章节');expect(push).toHaveBeenCalledWith({name:'admin-chapter-create',params:{courseId:42}})
  await click('编辑章节');expect(push).toHaveBeenCalledWith({name:'admin-chapter-edit',params:{courseId:42,chapterId:7}})
  await click('返回课程列表');expect(push).toHaveBeenCalledWith({name:'admin-courses'})
})
it('章节删除须二次确认，成功后刷新列表',async()=>{
  const fixture=backend();const{click}=await mount(AdminChapterListView,'admin-course-chapters',{id:'42'})
  await click('删除章节');expect(fixture.writes()).toHaveLength(0)
  await click('确认删除章节');expect(fixture.writes()).toHaveLength(1);expect(fixture.chapters()).toHaveLength(0)
})
it('章节列表冻结删除失败保留章节和确认目标',async()=>{
  const fixture=backend({frozen:true});const{root,click}=await mount(AdminChapterListView,'admin-course-chapters',{id:'42'})
  await click('删除章节');await click('确认删除章节')
  expect(flatten(root).some(n=>n.props.title?.includes?.('已有学习记录'))).toBe(true)
  expect(fixture.chapters()).toHaveLength(1);expect(text(root)).toContain('确认删除“RDD章节”')
})
it('章节编辑直达URL，教学字段完整保存且返回章节列表',async()=>{
  const fixture=backend();const{fill,click,root}=await mount(AdminChapterEditView,'admin-chapter-edit',{courseId:'42',chapterId:'7'})
  expect(text(root)).toContain('示例课程');fill('章节Markdown正文','# 修订正文');fill('章节教学目标','目标1\n目标2');fill('章节练习','练习1');await click('保存章节')
  expect(fixture.writes()[0]).toMatchObject({method:'put',url:'/resources/42/chapters/7',data:{content:'# 修订正文',learning_objectives:['目标1','目标2'],exercises:['练习1'],video_url:'/demo/video.mp4',example_code:'print(1)',position:1}})
  await click('返回章节列表');expect(push).toHaveBeenCalledWith({name:'admin-course-chapters',params:{id:42}})
})
it('零章可创建第一章，创建成功转为编辑URL避免重复新增',async()=>{
  const fixture=backend({empty:true});const{root}=await mount(AdminChapterListView,'admin-course-chapters',{id:'42'})
  expect(text(root)).toContain('章节数量 0')
  const{fill,click}=await mount(AdminChapterEditView,'admin-chapter-create',{courseId:'42'})
  fill('章节标题','第一章');fill('章节Markdown正文','教学内容');await click('保存章节')
  expect(fixture.writes()[0]).toMatchObject({method:'post',url:'/resources/42/chapters',data:{position:1}})
  expect(replace).toHaveBeenCalledWith({name:'admin-chapter-edit',params:{courseId:42,chapterId:7},query:{saved:'1'}})
})
it('保存失败保留章节内容，错误提示可见且不导航',async()=>{
  backend({failSave:true});const{fill,click,root}=await mount(AdminChapterEditView,'admin-chapter-edit',{courseId:'42',chapterId:'7'})
  fill('章节Markdown正文','# 不丢失');await click('保存章节')
  expect(flatten(root).some(n=>n.props.modelValue==='# 不丢失')).toBe(true)
  expect(flatten(root).some(n=>n.props.title?.includes?.('操作被拒绝'))).toBe(true)
  expect(replace).not.toHaveBeenCalled()
})
it('缺失章节不能保存且不产生写入',async()=>{
  const fixture=backend();const{root}=await mount(AdminChapterEditView,'admin-chapter-edit',{courseId:'42',chapterId:'999'})
  expect(flatten(root).some(n=>n.props.title?.includes?.('章节不存在'))).toBe(true)
  expect(text(root)).not.toContain('保存章节');expect(fixture.writes()).toHaveLength(0)
})
it('课程不存在显示读取错误，保留明显返回入口',async()=>{
  backend({missing:true});const{root,click}=await mount(AdminCourseEditView,'admin-course-edit',{id:'999'})
  expect(flatten(root).some(n=>n.props.role==='alert')).toBe(true);expect(text(root)).not.toContain('保存课程')
  await click('返回课程列表');expect(push).toHaveBeenCalledWith({name:'admin-courses'})
})
it.each(['0','-1','oops','9007199254740992'])('非法编号%s不调用接口或显示表单',async id=>{
  const fixture=backend();const{root}=await mount(AdminChapterEditView,'admin-chapter-edit',{courseId:id,chapterId:'7'})
  expect(fixture.calls).toHaveLength(0);expect(text(root)).not.toContain('保存章节')
})
it('五门正式资源仍在课程列表渲染各五章',async()=>{
  const titles=['Spark RDD基础教程','PySpark数据处理实践','Hadoop HDFS入门','MySQL数据库基础','Python机器学习基础']
  http.defaults.adapter=async config=>({config,status:200,statusText:'OK',headers:{},data:{items:titles.map((title,i)=>({id:1068+i,title,summary:'正式教学简介',resource_type:'document',status:'published',chapter_count:5,updated_at:'2026-10-05T12:00:00'})),total:5,page:1,page_size:10}})
  const{root}=await mount(AdminCoursesView,'admin-courses')
  for(const title of titles)expect(text(root)).toContain(title)
  expect(text(root).match(/章节数量 5/g)).toHaveLength(5)
  expect(text(root)).not.toContain('数据库验收资源');expect(text(root)).not.toContain('联调演示资源')
})
