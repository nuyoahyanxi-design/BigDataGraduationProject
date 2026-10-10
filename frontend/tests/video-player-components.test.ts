import { expect, it } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, nextTick, ref, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import LearningVideo from '../src/components/LearningVideo.vue'

type Node = { text:string; type:string; children:Node[]; parent?:Node; props:Record<string,any> }
const node=(type:string,text=''):Node=>({type,text,children:[],props:{}})
const renderer=createRenderer<Node,Node>({
  createElement:type=>node(type),createText:text=>node('text',text),createComment:text=>node('comment',text),
  setText:(n,t)=>{n.text=t},setElementText:(n,t)=>{n.text=t;n.children=[]},
  parentNode:n=>n.parent??null,nextSibling:n=>n.parent?.children[n.parent.children.indexOf(n)+1]??null,
  patchProp:(n,k,_,v)=>{n.props[k]=v},
  insert(n,p,anchor){if(n.parent)n.parent.children.splice(n.parent.children.indexOf(n),1);n.parent=p;const i=anchor?p.children.indexOf(anchor):-1;p.children.splice(i<0?p.children.length:i,0,n)},
  remove(n){if(n.parent)n.parent.children.splice(n.parent.children.indexOf(n),1)},
})
const flatten=(n:Node):Node[]=>[n,...n.children.flatMap(flatten)]
const text=(n:Node):string=>n.text+n.children.map(text).join('')
it('实际播放器结束仅提示，切换视频清除结束及元数据，播放才发play',async()=>{
  const {descriptor}=parse(readFileSync(new URL('../src/components/LearningVideo.vue',import.meta.url),'utf8'))
  const script=compileScript(descriptor,{id:'video-test'})
  const compiled=compileTemplate({source:descriptor.template!.content,filename:'LearningVideo.vue',id:'video-test',compilerOptions:{bindingMetadata:script.bindings}})
  const code=compiled.code.replace(/import \{([\s\S]*?)\} from "vue"/,(_,helpers:string)=>`const {${helpers.replace(/ as /g,': ')}}=Vue`).replace('export function render','function render')
  const render=new Function('Vue',ts.transpileModule(code,{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText+';return render')(Vue)
  const url=ref('/videos/course_1069/chapter_006.mp4'),calls:number[]=[]
  const root=node('root'),app=renderer.createApp({render:()=>Vue.h({...LearningVideo,render},{url:url.value,name:'章节视频',cover:null,duration:null,onPlay:(seconds:number)=>calls.push(seconds)})})
  app.provide(ssrContextKey, {modules:new Set()});app.mount(root)
  try {
    let video=flatten(root).find(n=>n.type==='video')!
    video.props.onLoadedmetadata({target:{duration:245}});await nextTick()
    expect(text(root)).toContain('视频时长：4:05')
    video.props.onEnded();await nextTick()
    expect(text(root)).toContain('视频播放完成，请阅读章节内容后确认完成本章节。')
    expect(calls).toEqual([])
    video.props.onPlay({target:{currentTime:12.5}});await nextTick()
    expect(calls).toEqual([12.5])
    expect(text(root)).not.toContain('视频播放完成')
    url.value='/videos/course_1069/chapter_007.mp4';await nextTick()
    video=flatten(root).find(n=>n.type==='video')!
    expect(video.props.src).toBe(url.value)
    expect(text(root)).toContain('视频时长：待视频加载')
    expect(text(root)).toContain('当前播放时间：0 秒')
    expect(calls).toHaveLength(1)
  } finally {app.unmount()}
})
