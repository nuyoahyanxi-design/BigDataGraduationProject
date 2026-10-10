// Isolated acceptance harness; not imported by the production application.
import { createApp, h, nextTick, ref } from 'vue'
import LearningVideo from '../src/components/LearningVideo.vue'

const chapter = ref(6), plays = ref(0), confirmations = ref(0)
const lessons = ref<{id:number;video_url:string|null}[]>([])
fetch('/test-course').then(response=>response.json()).then(course=>{lessons.value=course.chapters})
createApp({
  setup() {
    function media() { return document.querySelector('video')! }
    return () => h('main', [
      h('h1', '隔离视频导入验收'),
      h('p', '用户提供测试素材；播放与完成计数仅为模拟，不连接正式数据库，不代表AI课程内容。'),
      h('button', { onClick: () => { chapter.value = chapter.value === 6 ? 7 : 6 } }, '切换测试章节'),
      h('p', `当前测试章节：${chapter.value}`),
      h(LearningVideo, { key: chapter.value, url: lessons.value.find(row=>row.id===chapter.value)?.video_url ?? null,
        name: '用户提供的12.mp4（测试素材）', cover: null, duration: null, onPlay: () => { plays.value++ } }),
      h('button', { onClick: async () => { await nextTick(); await media().play() } }, '播放测试视频'),
      h('button', { onClick: () => media().pause() }, '暂停测试视频'),
      h('button', { onClick: async () => { media().currentTime = Math.max(0, media().duration - 0.5); await media().play() } }, '测试结束提示'),
      h('button', { onClick: () => { confirmations.value++ } }, '手动确认测试章节完成'),
      h('p', `模拟播放事件：${plays.value}；模拟完成事件：${confirmations.value}`),
    ])
  },
}).mount('#app')
