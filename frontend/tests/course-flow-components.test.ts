import { afterEach, expect, it, vi } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, defineComponent, h, nextTick, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { createPinia } from 'pinia'
import { http } from '../src/api/http'
import ResourceDetailView from '../src/views/ResourceDetailView.vue'
import CourseLearningView from '../src/views/CourseLearningView.vue'
const { push } = vi.hoisted(() => ({ push: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { id: '1071' } }), useRouter: () => ({ push }) }))
vi.mock('element-plus', () => {
  const button = defineComponent({ setup(_, { slots, attrs }) { return () => h('button', attrs, slots.default?.()) } })
  const plain = defineComponent({ setup(_, { slots, attrs }) { return () => h('div', attrs, slots.default?.()) } })
  return { ElButton: button, ElTag: plain, ElAlert: plain, ElCheckbox:plain, ElEmpty:plain, ElInput:plain, ElOption:plain, ElPagination:plain, ElSelect:plain }
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
function clientView(view: typeof ResourceDetailView) {
  const filename=view===ResourceDetailView?'ResourceDetailView':'CourseLearningView'
  const { descriptor }=parse(readFileSync(new URL(`../src/views/${filename}.vue`,import.meta.url),'utf8'))
  const script=compileScript(descriptor,{id:filename})
  const compiled=compileTemplate({source:descriptor.template!.content,filename,id:filename,compilerOptions:{bindingMetadata:script.bindings}})
  const code=compiled.code.replace(/import \{([\s\S]*?)\} from "vue"/,(_,helpers:string)=>`const {${helpers.replace(/ as /g, ': ')}}=Vue`).replace('export function render','function render')
  return {...view, render:new Function('Vue',ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText+';return render')(Vue)}
}
const original = http.defaults.adapter
let app: ReturnType<typeof renderer.createApp> | undefined
afterEach(() => { app?.unmount(); http.defaults.adapter=original; push.mockClear() })
async function mount(completed: number, view = ResourceDetailView) {
  const writes: string[]=[]
  http.defaults.adapter=async config => {
    let data: unknown
    if(config.url?.endsWith('/course')) data={ resource_id:1071,title:'课程',status:'published',course_status:'completed',chapters:Array.from({length:5},(_,i)=>({id:i+1,position:i+1,title:'章节'+(i+1),content:'正文',knowledge_tags:[],completed:i<completed,video_url:'/demo/video.mp4',video_cover:null,video_name:null,video_duration_seconds:null})) }
    else if(config.url?.endsWith('/progress')) data={items:[{resource_id:1071,status:'completed'}]}
    else if(config.url?.endsWith('/favorites')) data={items:[],total:0,page:1,page_size:100}
    else if(config.method==='post') { writes.push(config.url!); data={chapter_completed:completed===5,course_status:'completed'} }
    else data={id:1071,title:'课程',summary:'简介',status:'published',tags:[],resource_type:'course',category_code:'databases',difficulty:'beginner'}
    return {config,status:200,statusText:'OK',headers:{},data}
  }
  const root=node('root')
  app=renderer.createApp(clientView(view)); app.use(createPinia()); app.provide(ssrContextKey, {modules:new Set()}); app.mount(root)
  await new Promise(resolve => setTimeout(resolve, 20)); await nextTick()
  return {root,writes}
}
it.each([[0,'开始课程','未开始',0],[2,'继续学习','学习中',40],[5,'重新学习','已完成',100]] as const)('真实详情组件根据%d章完成展示状态和按钮', async (n,label,status,percent) => {
  const {root,writes}=await mount(n)
  expect(text(root)).toContain(status)
  expect(text(root)).toContain(`章节完成 ${percent}%`)
  const button=flatten(root).find(n=>n.type==='button' && text(n)===label)!
  expect(button).toBeDefined(); expect(button.props.disabled).toBe(false)
  button.props.onClick()
  expect(push).toHaveBeenCalledWith({name:'course-learning',params:{id:1071}})
  expect(writes).toEqual(['/resources/1071/view']) // navigation does not start/complete the course
})
it.each([[2,3],[5,5]])('课程组件%d章已完成时定位章节%d', async (n,selected) => {
  const {root,writes}=await mount(n,CourseLearningView)
  expect(text(root)).toContain(`第 ${selected} 章`)
  expect(writes).toEqual([`/resources/1071/chapters/${selected}/events`])
})


