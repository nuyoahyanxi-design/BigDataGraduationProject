import { expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ChapterNavigation from '../src/components/ChapterNavigation.vue'
import type { Chapter } from '../src/types/courses'
const chapters = [
  {id:1,position:1,title:'什么是RDD？',completed:true},
  {id:2,position:2,title:'Transformation转换算子与学习行为数据处理',completed:false},
  {id:3,position:3,title:'Action操作',completed:false},
] as Chapter[]
const render = (disabled=false) => renderToString(createSSRApp({render:()=>h(ChapterNavigation,{chapters,selected:2,disabled,courseTitle:'Spark RDD基础教程'})}))
it('目录展示课程名称和所有完整标题，长标题不在模板中截断',async()=>{
  const html=await render()
  expect(html).toContain('Spark RDD基础教程')
  for(const chapter of chapters)expect(html).toContain(`${chapter.position}. ${chapter.title}`)
  expect((html.match(/<button\b/g) ?? []).length).toBe(3)
  expect(html).toContain('class="chapter-navigation"')
})
it('保留当前章节语义和完成标记，正常情况下可切换',async()=>{
  const html=await render()
  expect((html.match(/aria-current="step"/g) ?? []).length).toBe(1)
  expect(html).toContain('✓ 1. 什么是RDD？')
  expect(html).not.toContain(' disabled')
})
it('忙碌时所有章节按钮仍禁用，未改变防重复操作语义',async()=>{
  const html=await render(true)
  expect((html.match(/ disabled/g) ?? []).length).toBe(3)
})
