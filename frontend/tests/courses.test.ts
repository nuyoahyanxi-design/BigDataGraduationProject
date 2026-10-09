import { afterEach, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { http } from '../src/api/http'
import { getCourse, recordChapter } from '../src/api/courses'
import { chapterPercent, safeVideoAsset, type Chapter } from '../src/types/courses'
import { learningBlocks } from '../src/services/markdown-learning'
import { newPlayback, updatePlayback } from '../src/services/video-learning'
import LearningVideo from '../src/components/LearningVideo.vue'
import LearningMarkdown from '../src/components/LearningMarkdown.vue'
import ChapterNavigation from '../src/components/ChapterNavigation.vue'
const original=http.defaults.adapter
afterEach(()=>{http.defaults.adapter=original})
it('课程查询和章节事件使用当前用户接口与固定事件UUID',async()=>{
  const requests: {url?:string;data?:string}[]=[]
  http.defaults.adapter=async config=>{requests.push(config);return {config,status:200,statusText:'OK',headers:{},data:{}}}
  await getCourse(1068)
  await recordChapter(1068,1,{event_uuid:'same-uuid',event_type:'video_play',playback_seconds:12.5})
  expect(requests[0]?.url).toBe('/resources/1068/course')
  expect(requests[1]?.url).toBe('/resources/1068/chapters/1/events')
  expect(JSON.parse(requests[1]!.data!)).toEqual({event_uuid:'same-uuid',event_type:'video_play',playback_seconds:12.5})
  expect(JSON.parse(requests[1]!.data!)).not.toHaveProperty('user_id')
})
it('完成率来自章节而非旧课程状态',()=>{
  expect(chapterPercent([])).toBe(0)
  expect(chapterPercent([{completed:true},{completed:false}] as Chapter[])).toBe(50)
  expect(chapterPercent([{completed:true},{completed:true}] as Chapter[])).toBe(100)
})
it('视频仅允许本地静态地址，拒绝脚本和路径穿越',()=>{
  expect(safeVideoAsset('/videos/demo.mp4')).toBe('/videos/demo.mp4')
  for(const bad of ['javascript:alert(1)','https://example.com/a.mp4','/videos/../a.mp4','/videos/a.png','//example.com/a.mp4'])expect(safeVideoAsset(bad)).toBeUndefined()
  expect(safeVideoAsset('/images/cover.png','images')).toBe('/images/cover.png')
})
it('播放时间、结束和异常状态可处理，重播清除完成标记',()=>{
  const state=newPlayback()
  updatePlayback(state,'play',1.5);updatePlayback(state,'timeupdate',9.25)
  expect(state.seconds).toBe(9.25)
  updatePlayback(state,'ended');expect(state.ended).toBe(true)
  updatePlayback(state,'play',0);expect(state.ended).toBe(false)
  updatePlayback(state,'timeupdate',NaN);expect(state.seconds).toBe(0)
  updatePlayback(state,'error');expect(state.failed).toBe(true)
})
it('HTML5播放器提供原生播放暂停控制，无视频显示阅读回退',async()=>{
  const render=(url:string|null)=>renderToString(createSSRApp({render:()=>h(LearningVideo,{url,cover:null,name:'RDD',duration:null})}))
  const html=await render('/videos/demo.mp4')
  expect(html).toContain('controls');expect(html).toContain('preload="metadata"');expect(html).toContain('/videos/demo.mp4')
  const empty=await render(null)
  expect(empty).toContain('教学视频暂未提供或无法加载');expect(empty).not.toContain('<video')
})
it('Markdown标题代码可展示，HTML不能执行',async()=>{
  const content='# RDD\n<script>alert(1)</script>\n```python\nprint(1)\n```'
  expect(learningBlocks(content).map(b=>b.kind)).toEqual(['heading','text','code'])
  const html=await renderToString(createSSRApp({render:()=>h(LearningMarkdown,{content})}))
  expect(html).toContain('&lt;script&gt;');expect(html).not.toContain('<script>');expect(html).toMatch(/<code[^>]*>print\(1\)<\/code>/)
})
it('章节目录展示完成标记与当前章节，忙碌时禁止切换',async()=>{
  const chapters=[{id:1,title:'第一章',position:1,completed:true},{id:2,title:'第二章',position:2,completed:false}] as Chapter[]
  const html=await renderToString(createSSRApp({render:()=>h(ChapterNavigation,{chapters,selected:2,disabled:true})}))
  expect(html).toContain('✓ 1. 第一章');expect(html).toContain('○ 2. 第二章');expect(html).toContain('aria-current="step"');expect(html).toContain('disabled')
})
