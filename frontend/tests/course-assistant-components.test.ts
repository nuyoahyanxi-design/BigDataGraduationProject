import { afterEach, expect, it, vi } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, defineComponent, h, nextTick, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { createPinia } from 'pinia'
import { http } from '../src/api/http'
import CourseAiAssistant from '../src/components/CourseAiAssistant.vue'
vi.mock('element-plus',()=>{
  const plain=defineComponent({setup(_, {slots,attrs}){return()=>h('div',attrs,slots.default?.())}})
  const button=defineComponent({setup(_, {slots,attrs}){return()=>h('button',attrs,slots.default?.())}})
  return {ElButton:button,ElAlert:plain,ElCheckbox:plain,ElEmpty:plain,ElInput:plain,ElOption:plain,ElPagination:plain,ElSelect:plain}
})
vi.mock('../src/components/AiAnswerContent.vue',()=>({default:defineComponent({props:['text'],setup(props){return()=>h('p',props.text)}})}))
type Node={text:string;type:string;children:Node[];parent?:Node;props:Record<string,any>;scrollTop:number;scrollTo:ReturnType<typeof vi.fn>;getBoundingClientRect:()=>{top:number};closest:()=>Node|undefined}
let layoutTarget:Node|undefined
const node=(type:string,text=''):Node=>({type,text,children:[],props:{},scrollTop:0,scrollTo:vi.fn(),getBoundingClientRect:()=>({top:type==='section'?180:type==='article'?160:100}),closest:()=>layoutTarget})
const renderer=createRenderer<Node,Node>({
  createElement:t=>node(t),createText:t=>node('text',t),createComment:t=>node('comment',t),
  setText:(n,t)=>{n.text=t},setElementText:(n,t)=>{n.text=t;n.children=[]},
  parentNode:n=>n.parent??null,nextSibling:n=>n.parent?.children[n.parent.children.indexOf(n)+1]??null,
  patchProp:(n,k,_,v)=>{n.props[k]=v},
  insert(n,p,a){if(n.parent)n.parent.children.splice(n.parent.children.indexOf(n),1);n.parent=p;const i=a?p.children.indexOf(a):-1;p.children.splice(i<0?p.children.length:i,0,n)},
  remove(n){if(n.parent)n.parent.children.splice(n.parent.children.indexOf(n),1)},
})
const flatten=(n:Node):Node[]=>[n,...n.children.flatMap(flatten)]
const text=(n:Node):string=>n.text+n.children.map(text).join('')
const settle=async()=>{await new Promise(r=>setTimeout(r,25));await nextTick()}
const original=http.defaults.adapter;let app:ReturnType<typeof renderer.createApp>|undefined
afterEach(()=>{app?.unmount();layoutTarget=undefined;http.defaults.adapter=original;vi.unstubAllGlobals()})
function clientComponent(){
  const {descriptor}=parse(readFileSync(new URL('../src/components/CourseAiAssistant.vue',import.meta.url),'utf8'))
  const script=compileScript(descriptor,{id:'course-ai'})
  const compiled=compileTemplate({source:descriptor.template!.content,filename:'CourseAiAssistant.vue',id:'course-ai',compilerOptions:{bindingMetadata:script.bindings}})
  const code=compiled.code.replace(/import \{([\s\S]*?)\} from "vue"/,(_,helpers:string)=>`const {${helpers.replace(/ as /g,': ')}}=Vue`).replace('export function render','function render')
  return {...CourseAiAssistant,render:new Function('Vue',ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText+';return render')(Vue)}
}
async function mount(empty=false,history=false){
  const calls:any[]=[]
  http.defaults.adapter=async config=>{
    calls.push(config)
    let data:any
    if(config.url?.endsWith('capabilities'))data={enabled:true,ready:true,consent_version:'agnes-external-v1'}
    else if(config.url?.endsWith('history'))data={items:history?[{request_uuid:'history-1',question:'历史SELECT问题',answer:'历史回答',status:'succeeded',mode:'resource',source:'课程资料增强回答',references:[]}]:[],total:history?1:0,page:1,page_size:20}
    else data={request_uuid:'test',question:'SELECT问题',answer:empty?'当前课程资料中未找到相关内容，以下回答基于通用知识。':'模型文字提及虚构的第999章',status:'succeeded',mode:'resource',source:'课程资料增强回答',
      course_id:1071,references:empty?[]:[{course_name:'MySQL数据库基础',chapter_name:'SELECT查询、条件筛选与排序',chapter_id:3,position:3}]}
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  const selected:number[]=[],root=node('root')
  app=renderer.createApp(clientComponent(),{courseId:1071,courseTitle:'MySQL数据库基础',chapterId:3,onSelect:(id:number)=>selected.push(id)})
  app.use(createPinia());app.provide(ssrContextKey,{modules:new Set()});app.component('RouterLink',defineComponent({setup(_, {slots}){return()=>h('a',slots.default?.())}}));app.mount(root);await settle()
  return {root,calls,selected}
}
async function click(root:Node,label:string){const button=flatten(root).find(n=>n.type==='button' && text(n)===label);expect(button).toBeDefined();await button!.props.onClick();await settle()}
async function send(root:Node){flatten(root).find(n=>n.props['aria-label']==='课程AI学习问题')!.props['onUpdate:modelValue']('SELECT问题');flatten(root).find(n=>text(n)==='我确认本次问题及所选资料可发送给外部模型' && n.props['onUpdate:modelValue'])!.props['onUpdate:modelValue'](true);await click(root,'发送问题')}
it('折叠面板不自动请求AI，打开默认课程模式，引用只展示服务端真实章节',async()=>{
  const {root,calls,selected}=await mount();expect(calls).toEqual([])
  await click(root,'展开助手');expect(flatten(root).find(n=>n.props['aria-label']==='课程AI模式')!.props['model-value']).toBe('course')
  await send(root)
  const buttons=flatten(root).filter(n=>n.type==='button').map(text)
  expect(buttons).toContain('3. SELECT查询、条件筛选与排序');expect(buttons.some(t=>t.includes('999'))).toBe(false)
  await click(root,'3. SELECT查询、条件筛选与排序');expect(selected).toEqual([3])
})
it('无匹配只显示通用知识说明，不展示伪造章节来源',async()=>{
  const {root}=await mount(true);await click(root,'展开助手');await send(root)
  expect(text(root)).toContain('当前课程资料中未找到相关内容，以下回答基于通用知识。')
  expect(text(root)).not.toContain('本次提供给模型的课程资料')
})
it('前端切换通用AI使用原接口，保留原助手入口',async()=>{
  const {root,calls}=await mount();await click(root,'展开助手')
  flatten(root).find(n=>n.props['aria-label']==='课程AI模式')!.props['onUpdate:modelValue']('general');await settle();await send(root)
  expect(calls.find(c=>c.method==='post').url).toBe('/ai/questions')
  expect(text(root)).toContain('打开独立AI助手与全部问答历史')
})
it('小屏展开和收起不会重建助手或再次自动发送',async()=>{
  const {root,calls}=await mount();await click(root,'展开助手');await click(root,'收起助手')
  expect(text(root)).not.toContain('课程AI学习问题')
  const initial=calls.length;await click(root,'展开助手');expect(calls.length).toBe(initial)
  expect(calls.filter(c=>c.method==='post')).toEqual([])
})
it('桌面自动展开，缩小窗口恢复折叠，放大保留同一问答状态',async()=>{
  let change!:()=>void
  const media={matches:true,addEventListener:vi.fn((name,fn)=>{change=fn}),removeEventListener:vi.fn()}
  vi.stubGlobal('window',{matchMedia:vi.fn(()=>media)})
  const {root,calls}=await mount();expect(text(root)).toContain('基于当前课程资料回答')
  await send(root);const posts=calls.filter(c=>c.method==='post').length
  media.matches=false;change();await settle();expect(text(root)).toContain('展开助手')
  media.matches=true;change();await settle();expect(text(root)).toContain('SELECT查询、条件筛选与排序')
  expect(calls.filter(c=>c.method==='post')).toHaveLength(posts)
})
it('课程页只有一个助手，位于材料外侧；桌面高度及滚动只作用于助手',()=>{
  const view=readFileSync(new URL('../src/views/CourseLearningView.vue',import.meta.url),'utf8')
  const {descriptor}=parse(view)
  expect(descriptor.template!.content.match(/<CourseAiAssistant\b/g)).toHaveLength(1)
  expect(descriptor.template!.content).toMatch(/<aside class="course-ai-rail"[\s\S]*?<CourseAiAssistant/)
  expect(descriptor.styles[0]!.content).toContain('grid-template-columns:minmax(0,1fr) clamp(450px,32vw,520px)')
  const panel=readFileSync(new URL('../src/components/CourseAiAssistant.vue',import.meta.url),'utf8')
  expect(panel).toContain('height:min(900px,var(--assistant-panel-height,calc(100dvh - 48px)))')
  expect(panel).toContain('overflow-y:auto;overscroll-behavior:contain')
})

it('工作面板固定上下区与滚动聊天区分离，输入与错误不嵌入回答滚动区',async()=>{
  const {root,calls}=await mount();await click(root,'展开助手')
  const nodes=flatten(root)
  const chat=nodes.find(n=>n.props.class==='assistant-chat')!
  const composer=nodes.find(n=>n.props.class==='assistant-composer')!
  expect(chat.parent).toBe(composer.parent)
  expect(flatten(chat).some(n=>n.props['aria-label']==='课程AI学习问题')).toBe(false)
  expect(flatten(composer).some(n=>n.props['aria-label']==='课程AI学习问题')).toBe(true)
  expect(text(composer)).toContain('最多2000字')
  flatten(composer).find(n=>n.props['aria-label']==='课程AI学习问题')!.props['onUpdate:modelValue']('SELECT问题')
  await click(root,'发送问题')
  expect(calls.filter(c=>c.method==='post')).toHaveLength(0)
  expect(flatten(composer).some(n=>n.props.role==='alert')).toBe(true)
})

it('引用默认折叠，课程名称去重，引用链接仍只来自服务端',async()=>{
  const {root,selected}=await mount();await click(root,'展开助手');await send(root)
  const refs=flatten(root).find(n=>n.type==='details' && n.props.class==='ai-references')!
  expect(refs.props.open).not.toBe(true)
  expect(text(refs)).toContain('参考来源（1章）')
  expect(text(refs).match(/参考课程：MySQL数据库基础/g)).toHaveLength(1)
  expect(text(refs)).not.toContain('999')
  await click(root,'3. SELECT查询、条件筛选与排序');expect(selected).toEqual([3])
  expect(text(root)).toContain('你的问题SELECT问题')
})

it('历史默认折叠，显示总数并可查看已有记录，输入区仍保留',async()=>{
  const {root,calls}=await mount(false,true);await click(root,'展开助手')
  const history=flatten(root).find(n=>n.type==='details' && n.props.class==='assistant-history')!
  expect(history.props.open).not.toBe(true)
  expect(text(history)).toContain('最近问答记录（1）')
  await click(root,'查看记录')
  expect(text(root)).toContain('历史回答')
  expect(text(root)).toContain('你的问题历史SELECT问题')
  expect(flatten(root).some(n=>n.props['aria-label']==='课程AI学习问题')).toBe(true)
  expect(calls.filter(c=>c.method==='post')).toHaveLength(0)
})

it('桌面面板扣除初始顶部偏移，提交后只滚动聊天容器到新回答',async()=>{
  const events:Record<string,()=>void>={}
  vi.stubGlobal('window',{innerHeight:800,matchMedia:()=>({matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()}),
    addEventListener:(name:string,callback:()=>void)=>{events[name]=callback},removeEventListener:vi.fn(),scrollTo:vi.fn()})
  const {root}=await mount()
  const panel=flatten(root).find(n=>n.type==='section')!
  expect(panel.props.style['--assistant-panel-height']).toBe('596px')
  const chat=flatten(root).find(n=>n.props.class==='assistant-chat')!
  chat.scrollTop=500
  await send(root)
  expect(chat.scrollTo).toHaveBeenCalledWith({top:560,behavior:'smooth'})
  expect(window.scrollTo).not.toHaveBeenCalled()
  panel.getBoundingClientRect=()=>({top:24});events.scroll();await settle()
  expect(panel.props.style['--assistant-panel-height']).toBe('752px')
  const source=readFileSync(new URL('../src/components/CourseAiAssistant.vue',import.meta.url),'utf8')
  expect(source).not.toContain('max-height:42dvh')
  expect(source).toContain('.assistant-composer{overflow:visible}')
})

it('小屏收到新回答不自动滚动课程页面或折叠面板',async()=>{
  const {root}=await mount();await click(root,'展开助手');await send(root)
  expect(flatten(root).find(n=>n.props.class==='assistant-chat')!.scrollTo).not.toHaveBeenCalled()
  expect(text(root)).toContain('收起助手')
})

it('章节区域尺寸变化后重新计算可用高度，卸载时释放观察器',async()=>{
  let resized!:()=>void
  const observed=vi.fn(),disconnected=vi.fn()
  layoutTarget=node('course-page')
  vi.stubGlobal('ResizeObserver',class {observe=observed;disconnect=disconnected;constructor(callback:()=>void){resized=callback}})
  vi.stubGlobal('window',{innerHeight:800,matchMedia:()=>({matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()})})
  const {root}=await mount();expect(observed).toHaveBeenCalledWith(layoutTarget)
  const panel=flatten(root).find(n=>n.type==='section')!
  panel.getBoundingClientRect=()=>({top:260});resized();await settle()
  expect(panel.props.style['--assistant-panel-height']).toBe('516px')
  app?.unmount();app=undefined;expect(disconnected).toHaveBeenCalledOnce()
})

