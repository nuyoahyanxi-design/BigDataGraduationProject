import { expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import AiAnswerContent from '../src/components/AiAnswerContent.vue'

async function render(text: string, errorCode: string | null, expanded: boolean) {
  return renderToString(createSSRApp({ render: () => h(AiAnswerContent, { text, errorCode, expanded }) }))
}
it('普通回答完整显示，无展开按钮', async () => {
  const html = await render('普通回答', null, false)
  expect(html).toContain('普通回答')
  expect(html).not.toContain('aria-expanded')
})
it('截断记录折叠和展开显示对应正文及按钮状态', async () => {
  const text = 'a'.repeat(2000) + '正文末尾'
  const collapsed = await render(text, 'answer_truncated', false)
  expect(collapsed).toContain('回答内容较长，点击展开完整内容')
  expect(collapsed).toContain('aria-expanded="false"')
  expect(collapsed).not.toContain('正文末尾')
  const expanded = await render(text, 'answer_truncated', true)
  expect(expanded).toContain('正文末尾')
  expect(expanded).toContain('aria-expanded="true"')
  expect(expanded).toContain('收起')
  expect(expanded).not.toContain('回答内容较长，点击展开完整内容')
})
it('长但未截断回答可展开，不显示截断警告', async () => {
  const html = await render('a'.repeat(2000), null, false)
  expect(html).toContain('aria-expanded="false"')
  expect(html).not.toContain('截断标记')
})
it('Token停止与正文裁剪区分，文本仍安全转义', async () => {
  const html = await render('<script>text</script>', 'provider_output_limited', false)
  expect(html).toContain('模型达到输出上限')
  expect(html).toContain('&lt;script&gt;')
  expect(html).not.toContain('回答内容较长')
})
