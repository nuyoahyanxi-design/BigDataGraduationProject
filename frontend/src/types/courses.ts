export interface Chapter {
  id: number; resource_id: number; title: string; position: number; content: string; knowledge_tags: string[]
  learning_objectives?: string[] | null; example_code?: string | null; exercises?: string[] | null
  video_name: string | null; video_url: string | null; video_cover: string | null
  video_duration_seconds: number | null; video_position: number; started?: boolean; completed: boolean
}
export interface Course {
  resource_id: number; title: string; content: string | null; status: string
  course_status: 'not_started' | 'in_progress' | 'completed'; chapters: Chapter[]
}
export type ChapterEventType = 'chapter_view' | 'video_play' | 'chapter_complete'
export interface ChapterReceipt {
  event_uuid: string; resource_id: number; chapter_id: number; event_type: ChapterEventType
  is_effective: number; chapter_completed: boolean; completed_chapters: number; total_chapters: number
  course_status: Course['course_status']
}
export function safeVideoAsset(url: string | null, folder = 'videos'): string | undefined {
  if (!url || url.includes('..')) return undefined
  if (folder === 'videos' && url === '/demo/video.mp4') return url
  const extensions = folder === 'videos' ? 'mp4|webm' : 'png|jpg|jpeg|webp'
  return new RegExp(`^/${folder}/[a-zA-Z0-9_/-]+\\.(${extensions})$`).test(url) ? url : undefined
}
export function chapterPercent(chapters: Chapter[]): number {
  const completed = chapters.filter(ch => ch.completed).length
  if (!completed || !chapters.length) return 0
  return completed === chapters.length ? 100 : Math.min(99, Math.max(1, Math.round(completed / chapters.length * 100)))
}

export function chapterStatus(chapters: Chapter[]): Course['course_status'] {
  const completed = chapters.filter(ch => ch.completed).length
  return chapters.length && completed === chapters.length ? 'completed' : chapters.some(ch=>ch.started || ch.completed) ? 'in_progress' : 'not_started'
}
export function courseButton(status: Course['course_status']): string {
  return status === 'completed' ? '重新学习' : status === 'in_progress' ? '继续学习' : '开始课程'
}
export function resumeChapter(chapters: Chapter[]): Chapter | undefined {
  const ordered = [...chapters].sort((a, b) => a.position - b.position)
  return ordered.find(ch => !ch.completed) ?? ordered.at(-1)
}
