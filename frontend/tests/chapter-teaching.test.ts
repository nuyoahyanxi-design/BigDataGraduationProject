import { expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ChapterTeachingContent from '../src/components/ChapterTeachingContent.vue'
import LearningVideo from '../src/components/LearningVideo.vue'
import { safeVideoAsset, type Chapter } from '../src/types/courses'
const chapter = { id: 1, title: 'RDD核心概念', content: '# 惰性求值\n行动触发计算', knowledge_tags: ['Spark', 'RDD'],
  learning_objectives: ['理解血缘'], example_code: 'print("RDD")', exercises: ['区分转换和行动'] } as Chapter
const render = (value: Chapter) => renderToString(createSSRApp({ render: () => h(ChapterTeachingContent, { chapter: value }) }))
it('教学目标、知识点、正文、代码和练习保持顺序并展示内容', async () => {
  const html = await render(chapter)
  const positions = ['教学目标', '知识点', '知识讲解', '代码示例', '章节练习'].map(text => html.indexOf(`aria-label="${text}"`))
  expect(positions.every((position, index) => position >= 0 && (!index || position > positions[index - 1]!))).toBe(true)
  for (const text of ['理解血缘', 'Spark', '惰性求值', '区分转换和行动']) expect(html).toContain(text)
  expect(html).toContain('print(&quot;RDD&quot;)')
})
it.each([undefined, null])('旧章节新字段为%s时保留正文且不白屏', async value => {
  const html = await render({ ...chapter, learning_objectives: value, example_code: value, exercises: value })
  expect(html).toContain('惰性求值')
  expect(html).toContain('暂未补充教学目标')
  expect(html).toContain('暂无独立代码示例')
  expect(html).toContain('整理学习笔记')
})
it('正文、代码、目标及练习内HTML均转义，不执行注入', async () => {
  const unsafe = '<script>alert(1)</script>'
  const html = await render({ ...chapter, content: unsafe, example_code: unsafe, learning_objectives: [unsafe], exercises: [unsafe] })
  expect(html).not.toContain('<script>')
  expect(html).toContain('&lt;script&gt;')
})
it('只允许新增精确视频占位地址，同时保持旧资源及安全限制', async () => {
  expect(safeVideoAsset('/demo/video.mp4')).toBe('/demo/video.mp4')
  expect(safeVideoAsset('/videos/demo.mp4')).toBe('/videos/demo.mp4')
  for (const bad of ['/demo/other.mp4', '/demo/../video.mp4', 'https://example.com/video.mp4', 'javascript:alert(1)']) expect(safeVideoAsset(bad)).toBeUndefined()
  const html = await renderToString(createSSRApp({ render: () => h(LearningVideo, { url: '/demo/video.mp4', cover: null, name: null, duration: null }) }))
  expect(html).toContain('src="/demo/video.mp4"')
  expect(html).toContain('controls')
})
