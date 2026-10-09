import { expect, it } from 'vitest'
import { chapterPercent, chapterStatus, courseButton, resumeChapter, type Chapter } from '../src/types/courses'
const chapters = (completed: number, total = 5) => Array.from({ length: total }, (_, i) => ({ id: i+1, position: i+1, completed: i < completed } as Chapter))
it.each([
  [0, 'not_started', '开始课程', 0],
  [1, 'in_progress', '继续学习', 20],
  [2, 'in_progress', '继续学习', 40],
  [5, 'completed', '重新学习', 100],
] as const)('完成%d章：状态、按钮和百分比一致', (n, status, label, percent) => {
  const list = chapters(n)
  expect(chapterStatus(list)).toBe(status)
  expect(courseButton(chapterStatus(list))).toBe(label)
  expect(chapterPercent(list)).toBe(percent)
})
it('未完成课程进入首个未完成章，全部完成进入最后章', () => {
  expect(resumeChapter(chapters(0))?.id).toBe(1)
  expect(resumeChapter(chapters(2).reverse())?.id).toBe(3)
  expect(resumeChapter(chapters(5))?.id).toBe(5)
  expect(resumeChapter([])).toBeUndefined()
})
it('展示百分比仅全章完成时为100，部分完成保持1到99', () => {
  expect(chapterPercent(chapters(999, 1000))).toBe(99)
  expect(chapterPercent(chapters(1, 1000))).toBe(1)
  expect(chapterPercent([])).toBe(0)
})
it('重新学习仅定位章节，不清除完成记录', () => {
  const list = chapters(5)
  const before = JSON.stringify(list)
  resumeChapter(list)
  expect(JSON.stringify(list)).toBe(before)
  expect(list.every(ch => ch.completed)).toBe(true)
})
