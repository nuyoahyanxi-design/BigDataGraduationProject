<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElAlert, ElButton } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getCourse, recordChapter } from '@/api/courses'
import { ResourceLearning, resourceError } from '@/services/resource-learning'
import { chapterPercent, chapterStatus, resumeChapter, type Course, type Chapter, type ChapterEventType } from '@/types/courses'
import ChapterNavigation from '@/components/ChapterNavigation.vue'
import LearningVideo from '@/components/LearningVideo.vue'
import LearningMarkdown from '@/components/LearningMarkdown.vue'
import ChapterTeachingContent from '@/components/ChapterTeachingContent.vue'
import CourseAiAssistant from '@/components/CourseAiAssistant.vue'
const route=useRoute(), router=useRouter(), auth=useAuthStore()
const course=ref<Course>(), selected=ref<Chapter>(), loading=ref(false), busy=ref(false), error=ref(''), notice=ref('')
const pending=ref<{ id:number; chapter:number; event_uuid:string; event_type:ChapterEventType; playback_seconds?:number }>()
const percent=computed(() => chapterPercent(course.value?.chapters ?? []))
let generation=0
let legacyController: ResourceLearning | undefined
onUnmounted(() => { generation++ })
async function action(chapter: Chapter, type: ChapterEventType, seconds?:number) {
  if (busy.value || !course.value || pending.value) return
  pending.value={id:course.value.resource_id,chapter:chapter.id,event_uuid:crypto.randomUUID(),event_type:type,
    ...(seconds === undefined ? {} : {playback_seconds:Math.round(seconds*1000)/1000})}
  await retry()
}
async function retry() {
  const operation=pending.value
  if (!operation || busy.value) return
  const seq=generation,token=auth.token
  busy.value=true;error.value=''
  try {
    const result=await recordChapter(operation.id,operation.chapter,{event_uuid:operation.event_uuid,event_type:operation.event_type,
      ...(operation.playback_seconds === undefined ? {} : {playback_seconds:operation.playback_seconds})})
    if(seq!==generation || token!==auth.token)return
    const chapter=course.value?.chapters.find(ch=>ch.id===operation.chapter)
    if(chapter)chapter.completed=result.chapter_completed
    if(course.value)course.value.course_status=chapterStatus(course.value.chapters)
    pending.value=undefined
    notice.value=course.value?.course_status==='completed'?'课程已完成，可继续复习章节内容。':'学习行为已记录'
  } catch(problem) { if(seq===generation && token===auth.token)error.value=resourceError(problem)+'；可重试原操作，不要重复提交新请求。' }
  finally { if(seq===generation && token===auth.token)busy.value=false }
}
async function selectChapter(chapter:Chapter) {
  if(busy.value || pending.value)return
  selected.value=chapter;notice.value=''
  await action(chapter,'chapter_view')
}
async function load() {
  const seq=++generation,token=auth.token,id=Number(route.params.id)
  course.value=undefined;selected.value=undefined;pending.value=undefined;busy.value=false;error.value='';notice.value=''
  legacyController=undefined
  if(!Number.isSafeInteger(id)||id<1){error.value='资源编号无效';return}
  loading.value=true
  try {
    const result=await getCourse(id)
    if(seq!==generation || token!==auth.token)return
    if(result.chapters.length)result.course_status=chapterStatus(result.chapters)
    course.value=result
    if(result.status==='published' && result.chapters.length)await selectChapter(resumeChapter(result.chapters)!)
  } catch(problem){if(seq===generation && token===auth.token)error.value=resourceError(problem)}
  finally{if(seq===generation && token===auth.token)loading.value=false}
}
async function legacy(action:'start'|'complete') {
  if(!course.value||busy.value)return
  const seq=generation,token=auth.token
  legacyController ??= new ResourceLearning(course.value.resource_id)
  const controller=legacyController
  busy.value=true;error.value=''
  try {
    await controller.load();await controller.perform(action)
    if(seq!==generation || token!==auth.token)return
    if(controller.state.actionError)error.value=controller.state.actionError
    else if(course.value){course.value.course_status=controller.state.progress;notice.value=controller.state.notice}
  }finally{if(seq===generation && token===auth.token)busy.value=false}
}
watch(()=>route.params.id,load,{immediate:true})
</script>
<template>
  <section class="course-page"><div class="course-toolbar"><ElButton @click="router.push({name:'resource-detail',params:{id:route.params.id}})">返回资源详情</ElButton></div>
    <p v-if="loading" role="status">正在加载课程…</p><ElAlert v-if="error" :title="error" type="error" :closable="false" />
    <ElButton v-if="pending" :disabled="busy" @click="retry">重试原操作</ElButton>
    <ElButton v-else-if="error && !course" @click="load">重新加载</ElButton>
    <template v-if="course"><header class="course-heading"><p class="course-eyebrow">课程学习</p><h1>{{course.title}}</h1><p class="course-status">课程状态：{{course.course_status==='completed'?'已完成':course.course_status==='in_progress'?'学习中':'未开始'}}<template v-if="course.chapters.length"> · 章节完成 {{percent}}%</template></p></header>
      <ElAlert v-if="notice" :title="notice" type="success" :closable="false" />
      <p class="course-note">视频播放结束后，请阅读章节内容并手动确认完成本章节；章节完成不验证学习能力或实际观看时长。</p>
      <div class="learning-workspace"><div class="learning-materials">
      <div v-if="course.chapters.length" class="course-layout">
        <aside class="course-sidebar"><ChapterNavigation :course-title="course.title" :chapters="course.chapters" :selected="selected?.id" :disabled="busy || !!pending" @select="selectChapter" /></aside>
        <article v-if="selected" class="panel course-content"><header class="chapter-heading"><p>第 {{selected.position}} 章</p><h2>{{selected.title}}</h2></header>
          <LearningVideo :key="selected.id" :url="selected.video_url" :cover="selected.video_cover" :name="selected.video_name || selected.title + '教学视频'" :duration="selected.video_duration_seconds"
            :disabled="busy || !!pending" @play="seconds=>selected && action(selected,'video_play',seconds)" />
          <ChapterTeachingContent :chapter="selected" />
          <div class="chapter-actions"><ElButton type="primary" :disabled="busy || !!pending || selected.completed || course.status!=='published'" @click="action(selected,'chapter_complete')">{{selected.completed?'本章节已完成':'完成本章节'}}</ElButton></div>
        </article>
      </div>
      <article v-else class="panel"><p>本资源暂无独立章节，请阅读现有内容。</p><LearningMarkdown :content="course.content || '暂无正文，请返回资源详情查看原资源地址。'" />
        <ElButton v-if="course.course_status==='not_started'" :disabled="busy || course.status!=='published'" @click="legacy('start')">开始阅读</ElButton>
        <ElButton v-if="course.course_status==='in_progress'" :disabled="busy || course.status!=='published'" @click="legacy('complete')">确认阅读完成</ElButton>
      </article>
      </div><aside class="course-ai-rail" aria-label="课程AI辅助学习"><CourseAiAssistant :key="course.resource_id" :course-id="course.resource_id" :course-title="course.title" :chapter-id="selected?.id" :learning-busy="busy || !!pending" @select="id=>{const ch=course?.chapters.find(item=>item.id===id);if(ch)selectChapter(ch)}" /></aside></div>
    </template>
  </section>
</template>
<style scoped>
.course-page{max-width:1600px;margin:0 auto;min-width:0}
.learning-workspace{display:grid;grid-template-columns:minmax(0,1fr);gap:24px;align-items:start}.learning-materials,.course-ai-rail{min-width:0}
.course-toolbar{margin-bottom:20px}.course-heading{margin-bottom:20px}
.course-eyebrow{color:#246bd3;font-size:13px;margin:0 0 8px;letter-spacing:2px}
.course-heading h1{font-size:28px;line-height:1.4;margin:0 0 12px;color:#172b4d;overflow-wrap:break-word}
.course-status{color:#596b83;font-size:14px;margin:0}
.course-note{color:#7b889a;font-size:13px;line-height:1.7;margin:16px 0 24px}
.course-layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:24px;align-items:start}
.course-sidebar{box-sizing:border-box;width:260px;min-width:0;padding:22px 16px;background:#fff;border:1px solid #e4e8ee;border-radius:12px;position:sticky;top:24px;max-height:calc(100dvh - 48px);overflow-y:auto}
.course-content{box-sizing:border-box;min-width:0;padding:28px}
.chapter-heading{border-bottom:1px solid #edf0f5;padding-bottom:20px;margin-bottom:24px}
.chapter-heading p{font-size:12px;color:#7b889a;margin:0 0 8px}.chapter-heading h2{font-size:24px;color:#172b4d;line-height:1.5;margin:0;overflow-wrap:break-word}
.chapter-actions{border-top:1px solid #edf0f5;padding-top:24px;margin-top:32px;display:flex;justify-content:flex-end}
.chapter-actions .el-button{min-height:42px;padding:12px 28px}
@media(min-width:1400px){.learning-workspace{grid-template-columns:minmax(0,1fr) clamp(450px,32vw,520px)}.course-ai-rail{position:sticky;top:24px}.course-layout{grid-template-columns:220px minmax(0,1fr)}.course-sidebar{width:220px}.course-content{padding:22px}}
@media(max-width:900px){.course-layout{grid-template-columns:minmax(0,1fr)}.course-sidebar{width:100%;position:static;max-height:none}.course-content{padding:24px}}
@media(max-width:600px){.course-heading h1{font-size:24px}.course-content{padding:18px}.chapter-heading h2{font-size:21px}.chapter-actions .el-button{width:100%}}
</style>
