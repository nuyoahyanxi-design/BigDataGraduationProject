<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElAlert, ElButton, ElCheckbox, ElEmpty, ElInput, ElOption, ElPagination, ElSelect } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { CourseAssistant } from '@/services/course-assistant'
import { aiStatus } from '@/types/assistant'
import AiAnswerContent from './AiAnswerContent.vue'
const props=defineProps<{courseId:number;courseTitle:string;chapterId?:number;learningBusy?:boolean}>()
const emit=defineEmits<{select:[chapterId:number]}>()
const auth=useAuthStore(),controller=new CourseAssistant(props.courseId,()=>auth.token),state=controller.state
const mobileOpen=ref(false),desktop=ref(false),open=computed(()=>desktop.value || mobileOpen.value)
const panel=ref<HTMLElement>(),chat=ref<HTMLElement>(),latestExchange=ref<HTMLElement>(),availableHeight=ref<number>()
const compact=computed(()=>availableHeight.value!==undefined && availableHeight.value<500)
function measurePanel(){
  if(!desktop.value || typeof window==='undefined' || !panel.value?.getBoundingClientRect || !Number.isFinite(window.innerHeight)){availableHeight.value=undefined;return}
  availableHeight.value=Math.max(0,window.innerHeight-Math.max(24,panel.value.getBoundingClientRect().top)-24)
}
async function locateLatest(){
  await nextTick()
  if(!desktop.value || !chat.value?.getBoundingClientRect || !latestExchange.value?.getBoundingClientRect)return
  const top=Math.max(0,chat.value.scrollTop+latestExchange.value.getBoundingClientRect().top-chat.value.getBoundingClientRect().top)
  chat.value.scrollTo?.({top,behavior:'smooth'})
}
let media:MediaQueryList|undefined
let layoutObserver:ResizeObserver|undefined
function resize(){desktop.value=media?.matches??false;nextTick(measurePanel)}
onMounted(()=>{if(typeof window!=='undefined' && typeof window.matchMedia==='function'){media=window.matchMedia('(min-width: 1400px)');resize();media.addEventListener('change',resize)}})
onMounted(()=>{if(typeof window!=='undefined'){window.addEventListener?.('scroll',measurePanel,{passive:true});window.addEventListener?.('resize',measurePanel)}})
onMounted(()=>{const page=panel.value?.closest?.('.course-page');if(page && typeof ResizeObserver!=='undefined'){layoutObserver=new ResizeObserver(measurePanel);layoutObserver.observe(page)}})
watch(()=>props.courseTitle,()=>nextTick(measurePanel))
watch(()=>props.chapterId,()=>nextTick(measurePanel))
watch(()=>[state.busy,state.answer],()=>{locateLatest()},{flush:'post'})
const references=computed(()=>state.answer && 'references' in state.answer?state.answer.references:[])
const referenceGroups=computed(()=>{
  const groups=new Map<string,typeof references.value>()
  for(const reference of references.value){const items=groups.get(reference.course_name)??[];items.push(reference);groups.set(reference.course_name,items)}
  return [...groups].map(([courseName,chapters])=>({courseName,chapters}))
})
function toggle(){mobileOpen.value=!mobileOpen.value}
watch(open,async value=>{if(value && !state.capabilities && !state.loading)await controller.load()})
function changeMode(value:'course'|'general'){controller.mode(value)}
onUnmounted(()=>{layoutObserver?.disconnect();media?.removeEventListener('change',resize);if(typeof window!=='undefined'){window.removeEventListener?.('scroll',measurePanel);window.removeEventListener?.('resize',measurePanel)}controller.dispose()})
</script>
<template>
  <section ref="panel" class="course-ai panel" :class="{'assistant-compact':compact}" :style="availableHeight===undefined?undefined:{'--assistant-panel-height':availableHeight+'px'}" aria-label="AI学习工作面板">
    <div class="assistant-heading"><h2>AI学习助手</h2><ElButton class="assistant-toggle" :aria-expanded="open" aria-controls="course-assistant-panel" @click="toggle">{{open?'收起助手':'展开助手'}}</ElButton></div>
    <div v-if="open" id="course-assistant-panel" class="assistant-body">
      <header class="assistant-context">
        <p class="current-course" :title="courseTitle">当前课程：{{courseTitle}}</p>
        <label>问答模式<ElSelect :model-value="state.mode" :disabled="state.busy" aria-label="课程AI模式" @update:model-value="changeMode"><ElOption label="课程助手" value="course" /><ElOption label="通用AI" value="general" /></ElSelect></label>
        <p class="mode-note">{{state.mode==='course'?'基于当前课程资料回答；未找到相关资料时明确使用通用知识。':'直接使用已有AI能力回答。'}}</p>
      </header>
      <div ref="chat" class="assistant-chat" role="region" aria-label="问答内容" tabindex="0">
        <p v-if="state.loading" role="status">正在检查AI功能…</p>
        <ElAlert v-else-if="!state.capabilities?.enabled" title="AI助手当前不可用，课程学习不受影响" type="info" :closable="false" />
        <template v-else>
          <ElAlert v-if="!state.capabilities.ready" title="模型暂未配置，仍可查看历史" type="info" :closable="false" />
          <article v-if="state.answer || state.busy" ref="latestExchange" class="ai-exchange">
            <div class="user-question"><h3>你的问题</h3><p>{{state.answer?.question ?? state.question}}</p></div>
            <p v-if="state.busy" role="status">正在生成回答，请稍候…</p>
            <div v-if="state.answer" class="ai-answer"><h3>AI回答</h3><p class="answer-meta">{{aiStatus(state.answer)}} · {{state.answer.source}}</p>
              <AiAnswerContent v-if="state.answer.answer" v-model:expanded="state.expanded" :text="state.answer.answer" :error-code="state.answer.error_code" />
              <details v-if="references.length" :key="state.answer.request_uuid" class="ai-references">
                <summary>参考来源（{{references.length}}章）</summary>
                <div v-for="group in referenceGroups" :key="group.courseName" class="reference-group"><p>参考课程：{{group.courseName}}</p>
                  <p v-for="reference in group.chapters" :key="reference.chapter_id"><ElButton link :disabled="learningBusy" @click="emit('select',reference.chapter_id)">{{reference.position}}. {{reference.chapter_name}}</ElButton></p>
                </div>
              </details>
              <ElButton v-if="state.answer.status==='pending'" @click="controller.refresh()">刷新状态</ElButton>
            </div>
          </article>
          <p v-else-if="!state.busy" class="chat-empty">可以就当前章节提问，或切换通用AI。回答可能有误，请核对课程原文。</p>
          <details class="assistant-history"><summary>最近问答记录（{{state.total}}）</summary>
            <p class="history-note">本课程最近30天</p><ElEmpty v-if="!state.records.length" description="暂无课程问答历史" />
            <div v-for="record in state.records" :key="record.request_uuid" class="history-row"><span :title="record.question">{{record.question}}</span><ElButton :disabled="state.busy" @click="controller.show(record)">查看记录</ElButton></div>
            <ElPagination v-if="state.total>20" v-model:current-page="state.page" :total="state.total" :page-size="20" layout="prev,pager,next" @current-change="controller.history()" />
            <p><RouterLink to="/assistant">打开独立AI助手与全部问答历史</RouterLink></p>
          </details>
        </template>
      </div>
      <footer class="assistant-composer">
        <ElAlert v-if="state.error" :title="state.error" type="error" :closable="false" role="alert" />
        <template v-if="state.capabilities?.enabled">
          <ElInput v-model="state.question" type="textarea" :rows="compact?2:3" :maxlength="2000" show-word-limit :disabled="state.busy" aria-label="课程AI学习问题" />
          <p class="sharing-note">本次问题{{state.mode==='course'?'及检索到的课程资料':''}}将发送至Agnes，请勿输入密码或敏感信息。</p>
          <ElCheckbox v-model="state.consent" :disabled="state.busy">我确认本次问题及所选资料可发送给外部模型</ElCheckbox>
          <div class="send-row"><span>最多2000字</span><ElButton type="primary" :loading="state.busy" :disabled="state.busy || !state.capabilities.ready" @click="controller.send(chapterId)">发送问题</ElButton></div>
        </template>
      </footer>
    </div>
  </section>
</template>
<style scoped>
.course-ai{margin:0;min-width:0;padding:20px}.assistant-heading{display:flex;align-items:center;justify-content:space-between;gap:16px}.assistant-heading h2{font-size:20px;margin:0}.assistant-body{margin-top:16px}.assistant-context{padding-bottom:12px;border-bottom:1px solid #e5e7eb}.course-ai p{line-height:1.65;color:#64748b}.current-course{margin:0 0 12px;overflow-wrap:anywhere;font-weight:600;color:#334155!important}.assistant-context label{display:flex;align-items:center;gap:12px}.assistant-context .el-select{flex:1;min-width:0}.mode-note,.sharing-note,.answer-meta,.history-note{font-size:12px;margin:8px 0}.assistant-chat{padding:16px 0;overflow-wrap:anywhere}.ai-exchange h3{font-size:14px;margin:0 0 8px;color:#334155}.user-question{background:#f0f5fb;border-radius:10px;padding:12px 14px;margin-bottom:18px}.user-question p{margin:0;white-space:pre-wrap;color:#334155}.ai-answer{min-width:0}.ai-references,.assistant-history{border:1px solid #e5e7eb;border-radius:8px;padding:10px 12px;margin-top:18px}.course-ai summary{cursor:pointer;font-size:13px;font-weight:600;color:#475569;line-height:1.7}.reference-group p{margin:8px 0}.ai-references .el-button{white-space:normal;text-align:left;height:auto;line-height:1.6;max-width:100%}.history-row{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid #edf0f5;padding:10px 0}.history-row span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-width:0;flex:1}.assistant-composer{border-top:1px solid #e5e7eb;padding:14px 0 0;text-align:left;flex-shrink:0}.assistant-composer :deep(textarea){resize:none}.assistant-composer .el-alert{margin-bottom:12px}.assistant-composer :deep(.el-checkbox){height:auto;align-items:flex-start;white-space:normal}.assistant-composer :deep(.el-checkbox__label){white-space:normal;line-height:1.6}.send-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px}.send-row span{font-size:12px;color:#94a3b8}
@media(min-width:1400px){.course-ai{box-sizing:border-box;height:min(900px,var(--assistant-panel-height,calc(100dvh - 48px)));display:flex;flex-direction:column;overflow:hidden}.assistant-heading{flex-shrink:0}.assistant-toggle{display:none}.assistant-body{min-height:0;flex:1;display:grid;grid-template-rows:auto minmax(0,1fr) auto;overflow:hidden}.assistant-chat{min-height:0;overflow-y:auto;overscroll-behavior:contain;padding-right:8px}.assistant-composer{overflow:visible}.assistant-context{flex-shrink:0}}
.assistant-compact{padding:12px}.assistant-compact .assistant-body{margin-top:8px}.assistant-compact .current-course{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:6px}.assistant-compact .mode-note{display:none}.assistant-compact .assistant-context{padding-bottom:8px}.assistant-compact .assistant-composer{padding-top:8px}.assistant-compact .sharing-note{margin:6px 0;line-height:1.4}.assistant-compact .send-row{margin-top:8px}
@media(max-width:600px){.course-ai{padding:18px}.assistant-heading{flex-wrap:wrap}.assistant-context label{align-items:stretch;flex-direction:column}.history-row{align-items:stretch;flex-direction:column}}
</style>

